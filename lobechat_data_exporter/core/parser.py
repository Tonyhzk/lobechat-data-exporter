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
        for msg in messages:
            if msg.get("topicId"):
                messages_by_topic[msg["topicId"]].append(msg)
        
        # 排序消息
        for topic_id in messages_by_topic:
            messages_by_topic[topic_id].sort(
                key=lambda m: m.get("createdAt") or m.get("updatedAt") or m.get("id", "")
            )
        
        # 构建层级结构
        groups = self.build_agent_groups(
            agents, sessions, topics, messages_by_topic, agents_to_sessions
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
    
    def build_agent_groups(self, agents, sessions, topics, messages_by_topic, agents_to_sessions):
        """构建助手分组结构"""
        grouped_by_agent = defaultdict(list)
        assigned_topic_ids = set()
        
        # 通过agentsToSessions关联
        for relation in agents_to_sessions:
            agent_id = relation.get("agentId")
            session_id = relation.get("sessionId")
            
            if not agent_id or not session_id:
                continue
            
            session = sessions.get(session_id)
            
            # 找到该会话的所有主题
            session_topics = []
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
                key=lambda t: t["topic"].get("createdAt") or t["topic"].get("updatedAt") or t["topicId"]
            )
            
            session_label = self.derive_session_label(session, session_topics)
            
            grouped_by_agent[agent_id].append({
                "sessionId": session_id,
                "sessionLabel": session_label,
                "session": session,
                "topics": session_topics
            })
        
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
            candidates = [
                agent.get("title"),
                agent.get("slug"),
                agent.get("description")
            ]
            for candidate in candidates:
                if candidate and candidate.strip():
                    return candidate.strip()
            return agent.get("id", "assistant")
        
        if session:
            candidates = [session.get("title"), session.get("slug")]
            for candidate in candidates:
                if candidate and candidate.strip():
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
