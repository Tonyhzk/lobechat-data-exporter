from collections import defaultdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from .db_connector import PostgreSQLConnector, DBConfig


class DatabaseParser:
    """数据库数据解析器 - 将数据库数据转换为与JSON解析器兼容的格式"""
    
    # 助手名称映射表 - 将随机生成的slug替换为友好名称
    AGENT_NAME_MAPPING = {
        "buffalo-under-own-plane": "随便聊聊",
    }
    
    def __init__(self, connector: PostgreSQLConnector, log_callback: Optional[callable] = None):
        """
        初始化数据库解析器
        
        Args:
            connector: 数据库连接器
            log_callback: 日志回调函数
        """
        self.connector = connector
        self.log_callback = log_callback
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
    
    def _convert_datetime(self, dt) -> Optional[str]:
        """将datetime对象转换为ISO格式字符串"""
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat()
        return str(dt)
    
    def _convert_row(self, row: Dict) -> Dict:
        """转换数据库行数据，处理日期时间和特殊字段"""
        result = {}
        for key, value in row.items():
            # 转换下划线命名为驼峰命名（与JSON格式保持一致）
            camel_key = self._snake_to_camel(key)
            
            if isinstance(value, datetime):
                result[camel_key] = self._convert_datetime(value)
            elif value is None:
                result[camel_key] = None
            else:
                result[camel_key] = value
        return result
    
    def _snake_to_camel(self, snake_str: str) -> str:
        """将下划线命名转换为驼峰命名"""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    def parse(self, user_id: str = None) -> Dict:
        """
        从数据库解析数据
        
        Args:
            user_id: 用户ID，如果指定则只解析该用户的数据
        
        Returns:
            与JSON解析器兼容的数据结构
        """
        self.log("开始从数据库读取数据...", "INFO")
        
        # 获取原始数据
        raw_agents = self.connector.get_all_agents(user_id)
        raw_sessions = self.connector.get_all_sessions(user_id)
        raw_topics = self.connector.get_all_topics(user_id)
        raw_messages = self.connector.get_all_messages(user_id)
        raw_agents_to_sessions = self.connector.get_agents_to_sessions(user_id)
        raw_ai_models = self.connector.get_all_ai_models(user_id)
        raw_ai_providers = self.connector.get_all_ai_providers(user_id)
        
        self.log(f"读取到: {len(raw_agents)}个助手, {len(raw_sessions)}个会话, "
                 f"{len(raw_topics)}个主题, {len(raw_messages)}条消息", "INFO")
        
        # 转换数据格式
        agents_list = [self._convert_row(a) for a in raw_agents]
        sessions_list = [self._convert_row(s) for s in raw_sessions]
        topics_list = [self._convert_row(t) for t in raw_topics]
        messages_list = [self._convert_row(m) for m in raw_messages]
        agents_to_sessions_list = [self._convert_row(a) for a in raw_agents_to_sessions]
        ai_models_list = [self._convert_row(m) for m in raw_ai_models]
        ai_providers_list = [self._convert_row(p) for p in raw_ai_providers]
        
        # 构建字典索引
        agents = {agent["id"]: agent for agent in agents_list}
        sessions = {session["id"]: session for session in sessions_list}
        topics = {topic["id"]: topic for topic in topics_list}
        
        # 按主题分组消息
        messages_by_topic = defaultdict(list)
        default_messages_by_session = defaultdict(list)
        
        for msg in messages_list:
            if msg.get("topicId"):
                messages_by_topic[msg["topicId"]].append(msg)
            elif msg.get("sessionId"):
                default_messages_by_session[msg["sessionId"]].append(msg)
        
        # 排序消息
        for topic_id in messages_by_topic:
            messages_by_topic[topic_id].sort(
                key=lambda m: m.get("createdAt") or m.get("updatedAt") or m.get("id", "")
            )
        
        for session_id in default_messages_by_session:
            default_messages_by_session[session_id].sort(
                key=lambda m: m.get("createdAt") or m.get("updatedAt") or m.get("id", "")
            )
        
        # 构建层级结构
        groups = self._build_agent_groups(
            agents, sessions, topics, messages_by_topic, agents_to_sessions_list,
            default_messages_by_session
        )
        
        # 构建原始数据结构（与JSON导出格式兼容）
        raw_data = {
            "mode": "db",  # 标记数据来源
            "schemaHash": None,
            "data": {
                "userSettings": [],
                "aiProviders": ai_providers_list,
                "aiModels": ai_models_list,
                "agents": agents_list,
                "sessions": sessions_list,
                "sessionGroups": [],
                "topics": topics_list,
                "messages": messages_list,
                "messageBlocks": [],
                "messagePlugins": [],
                "messageTranslates": [],
                "threads": [],
                "agentsToSessions": agents_to_sessions_list,
                "userInstalledPlugins": []
            }
        }
        
        # 统计信息
        stats = {
            "agentCount": len(groups),
            "sessionCount": len(sessions),
            "topicCount": len(topics),
            "messageCount": len(messages_list)
        }
        
        self.log(f"✅ 数据解析完成 - 助手:{stats['agentCount']}, "
                 f"会话:{stats['sessionCount']}, 主题:{stats['topicCount']}, "
                 f"消息:{stats['messageCount']}", "SUCCESS")
        
        return {
            "sourceFileName": f"数据库 ({self.connector.config.host})",
            "raw": raw_data,
            "agents": agents,
            "sessions": sessions,
            "topics": topics,
            "messagesByTopic": dict(messages_by_topic),
            "groups": groups,
            "stats": stats
        }
    
    def _build_agent_groups(self, agents, sessions, topics, messages_by_topic, 
                            agents_to_sessions, default_messages_by_session=None):
        """构建助手分组结构"""
        grouped_by_agent = defaultdict(list)
        assigned_topic_ids = set()
        
        if default_messages_by_session is None:
            default_messages_by_session = {}
        
        # 通过agentsToSessions关联
        for relation in agents_to_sessions:
            agent_id = relation.get("agentId")
            session_id = relation.get("sessionId")
            
            if not agent_id or not session_id:
                continue
            
            session = sessions.get(session_id)
            
            # 找到该会话的所有主题
            session_topics = []
            
            # 首先检查是否有默认对话数据
            if session_id in default_messages_by_session:
                default_msgs = default_messages_by_session[session_id]
                if default_msgs:
                    first_msg = default_msgs[0] if default_msgs else None
                    default_topic_label = "默认对话"
                    if first_msg and first_msg.get("content"):
                        content = first_msg["content"]
                        if isinstance(content, str) and content.strip():
                            line = content.strip().split('\n')[0]
                            if len(line) > 30:
                                default_topic_label = f"默认对话: {line[:30]}…"
                            else:
                                default_topic_label = f"默认对话: {line}"
                    
                    session_topics.append({
                        "topicId": f"default_{session_id}",
                        "topic": {
                            "id": f"default_{session_id}",
                            "title": default_topic_label,
                            "sessionId": session_id,
                            "createdAt": first_msg.get("createdAt") if first_msg else None,
                            "_isDefaultTopic": True
                        },
                        "topicLabel": default_topic_label,
                        "messages": default_msgs
                    })
            
            # 添加正常的主题
            for topic_id, topic in topics.items():
                if topic.get("sessionId") == session_id:
                    session_topics.append({
                        "topicId": topic_id,
                        "topic": topic,
                        "topicLabel": topic.get("title") or f"Topic_{topic_id[-6:]}",
                        "messages": messages_by_topic.get(topic_id, [])
                    })
                    assigned_topic_ids.add(topic_id)
            
            # 排序主题
            session_topics.sort(
                key=lambda t: (
                    0 if t["topic"].get("_isDefaultTopic") else 1,
                    t["topic"].get("createdAt") or t["topic"].get("updatedAt") or t["topicId"]
                )
            )
            
            session_label = self._derive_session_label(session, session_topics)
            
            grouped_by_agent[agent_id].append({
                "sessionId": session_id,
                "sessionLabel": session_label,
                "session": session,
                "topics": session_topics
            })
        
        # 处理孤立主题
        orphan_topics = []
        for topic_id, topic in topics.items():
            if topic_id not in assigned_topic_ids and topic.get("sessionId") is None:
                orphan_topics.append({
                    "topicId": topic_id,
                    "topic": topic,
                    "topicLabel": topic.get("title") or f"Topic_{topic_id[-6:]}",
                    "messages": messages_by_topic.get(topic_id, [])
                })
        
        if orphan_topics:
            orphan_topics.sort(
                key=lambda t: t["topic"].get("createdAt") or t["topic"].get("updatedAt") or t["topicId"]
            )
            
            default_agent_id = None
            for agent_id in agents.keys():
                agent = agents[agent_id]
                if not agent.get("title"):
                    default_agent_id = agent_id
                    break
            
            if not default_agent_id and agents:
                default_agent_id = list(agents.keys())[0]
            
            if default_agent_id:
                virtual_session_label = self._derive_session_label(None, orphan_topics)
                
                if default_agent_id not in grouped_by_agent:
                    grouped_by_agent[default_agent_id] = []
                
                grouped_by_agent[default_agent_id].append({
                    "sessionId": "virtual_session_orphan_topics",
                    "sessionLabel": virtual_session_label or "随便聊聊",
                    "session": None,
                    "topics": orphan_topics
                })
        
        # 构建最终分组
        groups = []
        for agent_id, session_groups in grouped_by_agent.items():
            agent = agents.get(agent_id)
            agent_label = self._derive_agent_label(agent, None)
            
            session_groups.sort(
                key=lambda s: s["session"].get("createdAt") if s["session"] else s["sessionId"]
            )
            
            groups.append({
                "agentId": agent_id,
                "agentLabel": agent_label,
                "agent": agent,
                "sessions": session_groups
            })
        
        return groups
    
    def _derive_agent_label(self, agent: Optional[Dict], session: Optional[Dict]) -> str:
        """推导助手标签"""
        if agent:
            slug = agent.get("slug")
            if slug and slug in self.AGENT_NAME_MAPPING:
                return self.AGENT_NAME_MAPPING[slug]
            
            candidates = [
                agent.get("title"),
                slug,
                agent.get("description")
            ]
            for candidate in candidates:
                if candidate and str(candidate).strip():
                    if str(candidate).strip() in self.AGENT_NAME_MAPPING:
                        return self.AGENT_NAME_MAPPING[str(candidate).strip()]
                    return str(candidate).strip()
            return agent.get("id", "assistant")
        
        if session:
            candidates = [session.get("title"), session.get("slug")]
            for candidate in candidates:
                if candidate and str(candidate).strip():
                    if str(candidate).strip() in self.AGENT_NAME_MAPPING:
                        return self.AGENT_NAME_MAPPING[str(candidate).strip()]
                    return str(candidate).strip()
        
        return "未命名助手"
    
    def _derive_session_label(self, session: Optional[Dict], topics: List[Dict]) -> str:
        """推导会话标签"""
        if not session:
            return "session"
        
        topic_title = None
        snippet = None
        
        for topic_group in topics:
            if not topic_title and topic_group["topic"] and topic_group["topic"].get("title"):
                topic_title = topic_group["topic"]["title"]
            
            if not snippet and topic_group["messages"]:
                snippet = self._best_message_snippet(topic_group["messages"])
            
            if topic_title and snippet:
                break
        
        candidates = [
            topic_title,
            snippet,
            session.get("title"),
            session.get("slug"),
            session.get("description")
        ]
        
        for candidate in candidates:
            if candidate and str(candidate).strip():
                return str(candidate).strip()
        
        return session.get("id", "session")
    
    def _best_message_snippet(self, messages: List[Dict]) -> Optional[str]:
        """从消息中提取最佳摘要"""
        sorted_messages = sorted(
            messages,
            key=lambda m: m.get("createdAt") or m.get("updatedAt") or m.get("id", "")
        )
        
        for msg in sorted_messages:
            if msg.get("role") in ["user", "assistant"]:
                content = msg.get("content")
                if isinstance(content, str) and content.strip():
                    line = content.strip().split('\n')[0]
                    if len(line) > 48:
                        return f"{line[:48].strip()}…"
                    return line
        
        return None
    
    def get_all_users(self) -> List[Dict]:
        """获取所有用户列表"""
        try:
            users = self.connector.get_all_users()
            return [self._convert_row(u) for u in users]
        except Exception as e:
            self.log(f"获取用户列表失败: {e}", "ERROR")
            return []