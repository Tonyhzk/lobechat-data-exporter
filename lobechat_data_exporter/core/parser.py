"""
LobeChat 数据解析器
负责解析 JSON 数据并构建层级结构
"""

import os
from collections import defaultdict
from typing import Dict, List, Any, Optional
from ..config import ENABLE_DEBUG


class LobeChatParser:
    """LobeChat 数据解析器"""
    
    # 助手名称映射表 - 将随机生成的slug替换为友好名称
    AGENT_NAME_MAPPING = {
        "buffalo-under-own-plane": "随便聊聊",
        # 可以在这里添加更多映射
    }
    
    def __init__(self, log_callback: Optional[callable] = None):
        """
        初始化解析器
        
        Args:
            log_callback: 日志回调函数
        """
        self.log_callback = log_callback
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
    
    def parse(self, raw_data: Dict, source_file: str) -> Dict:
        """
        解析 LobeChat 数据
        
        Args:
            raw_data: 原始 JSON 数据
            source_file: 源文件路径
        
        Returns:
            解析后的数据结构
        """
        if ENABLE_DEBUG:
            self.log("DEBUG: 开始解析数据结构...", "DEBUG")
        
        # 提取data字段
        data = raw_data.get("data", {})
        
        if not data:
            raise ValueError("JSON结构不正确：缺少data字段")
        
        # 提取各个数据集
        agents = {agent["id"]: agent for agent in data.get("agents", [])}
        sessions = {session["id"]: session for session in data.get("sessions", [])}
        topics = {topic["id"]: topic for topic in data.get("topics", [])}
        messages = data.get("messages", [])
        agents_to_sessions = data.get("agentsToSessions", [])
        
        # 按主题分组消息
        messages_by_topic = defaultdict(list)
        # 收集默认对话消息（topicId为null但sessionId不为null的消息）
        default_messages_by_session = defaultdict(list)
        
        for msg in messages:
            if msg.get("topicId"):
                messages_by_topic[msg["topicId"]].append(msg)
            elif msg.get("sessionId"):
                # 这是默认对话数据 - topicId为null但有sessionId
                default_messages_by_session[msg["sessionId"]].append(msg)
        
        # 排序消息
        for topic_id in messages_by_topic:
            messages_by_topic[topic_id].sort(
                key=lambda m: m.get("createdAt") or m.get("updatedAt") or m.get("id", "")
            )
        
        # 排序默认对话消息
        for session_id in default_messages_by_session:
            default_messages_by_session[session_id].sort(
                key=lambda m: m.get("createdAt") or m.get("updatedAt") or m.get("id", "")
            )
        
        # 构建层级结构
        groups = self.build_agent_groups(
            agents, sessions, topics, messages_by_topic, agents_to_sessions,
            default_messages_by_session
        )
        
        # 统计信息
        stats = {
            "agentCount": len(groups),
            "sessionCount": len(sessions),
            "topicCount": len(topics),
            "messageCount": len(messages)
        }
        
        if ENABLE_DEBUG:
            self.log(
                f"DEBUG: 解析完成 - 助手:{stats['agentCount']}, "
                f"会话:{stats['sessionCount']}, 主题:{stats['topicCount']}, "
                f"消息:{stats['messageCount']}", 
                "DEBUG"
            )
        
        return {
            "sourceFileName": os.path.basename(source_file),
            "raw": raw_data,
            "agents": agents,
            "sessions": sessions,
            "topics": topics,
            "messagesByTopic": dict(messages_by_topic),
            "groups": groups,
            "stats": stats
        }
    
    def build_agent_groups(self, agents, sessions, topics, messages_by_topic, agents_to_sessions,
                           default_messages_by_session=None):
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
            
            # 首先检查是否有默认对话数据（topicId为null的消息）
            if session_id in default_messages_by_session:
                default_msgs = default_messages_by_session[session_id]
                if default_msgs:
                    # 创建虚拟话题来包含默认对话
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
                            "_isDefaultTopic": True  # 标记为默认对话
                        },
                        "topicLabel": default_topic_label,
                        "messages": default_msgs
                    })
                    
                    if ENABLE_DEBUG:
                        self.log(f"DEBUG: 会话 {session_id} 有 {len(default_msgs)} 条默认对话消息", "DEBUG")
            
            # 然后添加正常的主题
            for topic_id, topic in topics.items():
                if topic.get("sessionId") == session_id:
                    session_topics.append({
                        "topicId": topic_id,
                        "topic": topic,
                        "topicLabel": topic.get("title") or f"Topic_{topic_id[-6:]}",
                        "messages": messages_by_topic.get(topic_id, [])
                    })
                    assigned_topic_ids.add(topic_id)
            
            # 排序主题（默认对话在前面）
            session_topics.sort(
                key=lambda t: (
                    0 if t["topic"].get("_isDefaultTopic") else 1,  # 默认对话优先
                    t["topic"].get("createdAt") or t["topic"].get("updatedAt") or t["topicId"]
                )
            )
            
            session_label = self.derive_session_label(session, session_topics)
            
            grouped_by_agent[agent_id].append({
                "sessionId": session_id,
                "sessionLabel": session_label,
                "session": session,
                "topics": session_topics
            })
        
        # 处理没有 sessionId 的孤立主题（如"随便聊聊"）
        orphan_topics = []
        for topic_id, topic in topics.items():
            if topic_id not in assigned_topic_ids and topic.get("sessionId") is None:
                orphan_topics.append({
                    "topicId": topic_id,
                    "topic": topic,
                    "topicLabel": topic.get("title") or f"Topic_{topic_id[-6:]}",
                    "messages": messages_by_topic.get(topic_id, [])
                })
        
        # 如果有孤立主题，将它们添加到默认助手的虚拟会话中
        if orphan_topics:
            # 排序孤立主题
            orphan_topics.sort(
                key=lambda t: t["topic"].get("createdAt") or t["topic"].get("updatedAt") or t["topicId"]
            )
            
            # 查找默认助手（通常是第一个助手或没有title的助手）
            default_agent_id = None
            for agent_id in agents.keys():
                agent = agents[agent_id]
                if not agent.get("title"):  # 没有title的是默认助手
                    default_agent_id = agent_id
                    break
            
            # 如果没找到默认助手，使用第一个助手
            if not default_agent_id and agents:
                default_agent_id = list(agents.keys())[0]
            
            # 如果找到了助手，添加虚拟会话
            if default_agent_id:
                virtual_session_label = self.derive_session_label(None, orphan_topics)
                
                # 如果该助手还没有任何会话，初始化列表
                if default_agent_id not in grouped_by_agent:
                    grouped_by_agent[default_agent_id] = []
                
                # 添加虚拟会话（使用特殊的sessionId标识）
                grouped_by_agent[default_agent_id].append({
                    "sessionId": "virtual_session_orphan_topics",
                    "sessionLabel": virtual_session_label or "随便聊聊",
                    "session": None,
                    "topics": orphan_topics
                })
                
                if ENABLE_DEBUG:
                    self.log(f"DEBUG: 找到 {len(orphan_topics)} 个孤立主题，已添加到助手 {default_agent_id}", "DEBUG")
        
        # 构建最终分组
        groups = []
        for agent_id, session_groups in grouped_by_agent.items():
            agent = agents.get(agent_id)
            agent_label = self.derive_agent_label(agent, None)
            
            # 排序会话
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
    
    def derive_agent_label(self, agent: Optional[Dict], session: Optional[Dict]) -> str:
        """推导助手标签"""
        if agent:
            # 检查slug是否在名称映射表中
            slug = agent.get("slug")
            if slug and slug in self.AGENT_NAME_MAPPING:
                return self.AGENT_NAME_MAPPING[slug]
            
            candidates = [
                agent.get("title"),
                slug,
                agent.get("description")
            ]
            for candidate in candidates:
                if candidate and candidate.strip():
                    # 再次检查候选名称是否需要映射
                    if candidate.strip() in self.AGENT_NAME_MAPPING:
                        return self.AGENT_NAME_MAPPING[candidate.strip()]
                    return candidate.strip()
            return agent.get("id", "assistant")
        
        if session:
            candidates = [session.get("title"), session.get("slug")]
            for candidate in candidates:
                if candidate and candidate.strip():
                    # 检查会话名称是否需要映射
                    if candidate.strip() in self.AGENT_NAME_MAPPING:
                        return self.AGENT_NAME_MAPPING[candidate.strip()]
                    return candidate.strip()
        
        return "未命名助手"
    
    def derive_session_label(self, session: Optional[Dict], topics: List[Dict]) -> str:
        """推导会话标签"""
        if not session:
            return "session"
        
        # 尝试从主题中获取信息
        topic_title = None
        snippet = None
        
        for topic_group in topics:
            if not topic_title and topic_group["topic"] and topic_group["topic"].get("title"):
                topic_title = topic_group["topic"]["title"]
            
            if not snippet and topic_group["messages"]:
                snippet = self.best_message_snippet(topic_group["messages"])
            
            if topic_title and snippet:
                break
        
        # 构建候选标签
        candidates = [
            topic_title,
            snippet,
            session.get("title"),
            session.get("slug"),
            session.get("description")
        ]
        
        for candidate in candidates:
            if candidate and candidate.strip():
                return candidate.strip()
        
        return session.get("id", "session")
    
    def best_message_snippet(self, messages: List[Dict]) -> Optional[str]:
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
