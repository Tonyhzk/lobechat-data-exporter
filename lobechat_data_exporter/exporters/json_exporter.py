"""
JSON 导出器
负责构建自定义 JSON 导出结构
"""

from typing import Dict, List, Set
from collections import defaultdict


class JSONExporter:
    """JSON 导出器 - 负责构建自定义JSON导出数据"""
    
    def __init__(self, parsed_data: Dict):
        """
        初始化导出器
        
        Args:
            parsed_data: 解析后的数据
        """
        self.parsed_data = parsed_data
    
    def build_custom_json(self, selected_modules: List[str]) -> Dict:
        """
        构建自定义JSON导出数据
        
        Args:
            selected_modules: 选中的模块列表
        
        Returns:
            自定义导出的JSON数据
        """
        raw_data = self.parsed_data["raw"]
        original_data = raw_data.get("data", {})
        
        new_data = {}
        
        for module_key in selected_modules:
            if module_key in original_data:
                new_data[module_key] = original_data[module_key]
        
        return {
            "mode": raw_data.get("mode", "postgres"),
            "schemaHash": raw_data.get("schemaHash", ""),
            "data": new_data
        }
    
    def get_selected_item_data(self, item_type: str, item_id: str) -> Dict:
        """
        获取选中项的完整数据（包含子级数据）
        
        Args:
            item_type: 项目类型（message/topic/session/agent）
            item_id: 项目ID
        
        Returns:
            包含完整数据的字典
        """
        if item_type == "message":
            return self._get_message_data(item_id)
        elif item_type == "topic":
            return self._get_topic_data(item_id)
        elif item_type == "session":
            return self._get_session_data(item_id)
        elif item_type == "agent":
            return self._get_agent_data(item_id)
        
        return None
    
    def _get_message_data(self, msg_id: str) -> Dict:
        """获取单条消息数据"""
        for topic_id, messages in self.parsed_data["messagesByTopic"].items():
            for msg in messages:
                if msg.get("id") == msg_id:
                    return {
                        "mode": "postgres",
                        "schemaHash": self.parsed_data["raw"].get("schemaHash", ""),
                        "data": {"messages": [msg]}
                    }
        return None
    
    def _get_topic_data(self, topic_id: str) -> Dict:
        """获取主题数据"""
        topic = self.parsed_data["topics"].get(topic_id)
        if not topic:
            return None
        
        messages = self.parsed_data["messagesByTopic"].get(topic_id, [])
        
        return {
            "mode": "postgres",
            "schemaHash": self.parsed_data["raw"].get("schemaHash", ""),
            "data": {
                "topics": [topic],
                "messages": messages
            }
        }
    
    def _get_session_data(self, session_id: str) -> Dict:
        """获取会话数据"""
        session = self.parsed_data["sessions"].get(session_id)
        if not session:
            return None
        
        session_topics = []
        session_messages = []
        
        for topic_id, topic in self.parsed_data["topics"].items():
            if topic.get("sessionId") == session_id:
                session_topics.append(topic)
                topic_messages = self.parsed_data["messagesByTopic"].get(topic_id, [])
                session_messages.extend(topic_messages)
        
        return {
            "mode": "postgres",
            "schemaHash": self.parsed_data["raw"].get("schemaHash", ""),
            "data": {
                "sessions": [session],
                "topics": session_topics,
                "messages": session_messages
            }
        }
    
    def _get_agent_data(self, agent_id: str) -> Dict:
        """获取助手数据"""
        agent = self.parsed_data["agents"].get(agent_id)
        if not agent:
            return None
        
        agent_sessions = []
        agent_topics = []
        agent_messages = []
        agents_to_sessions = []
        
        for group in self.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                for session_group in group["sessions"]:
                    session_id = session_group["sessionId"]
                    session = session_group.get("session")
                    
                    if session:
                        agent_sessions.append(session)
                    
                    agents_to_sessions.append({
                        "agentId": agent_id,
                        "sessionId": session_id
                    })
                    
                    for topic_group in session_group["topics"]:
                        topic = topic_group.get("topic")
                        if topic:
                            agent_topics.append(topic)
                        
                        messages = topic_group.get("messages", [])
                        agent_messages.extend(messages)
                break
        
        return {
            "mode": "postgres",
            "schemaHash": self.parsed_data["raw"].get("schemaHash", ""),
            "data": {
                "agents": [agent],
                "sessions": agent_sessions,
                "topics": agent_topics,
                "messages": agent_messages,
                "agentsToSessions": agents_to_sessions
            }
        }
    
    def get_batch_data(self, item_list: List[tuple]) -> Dict:
        """
        获取批量选中的数据
        
        Args:
            item_list: 项目列表 [(item_type, item_id), ...]
        
        Returns:
            批量数据字典
        """
        all_agents = []
        all_sessions = []
        all_topics = []
        all_messages = []
        all_agents_to_sessions = []
        
        agents_set = set()
        sessions_set = set()
        topics_set = set()
        messages_set = set()
        
        for item_type, item_id in item_list:
            if item_type == "主题":
                self._add_topic_to_batch(item_id, all_topics, all_messages, 
                                        topics_set, messages_set)
            elif item_type == "会话":
                self._add_session_to_batch(item_id, all_sessions, all_topics, 
                                          all_messages, sessions_set, topics_set, messages_set)
            elif item_type == "助手":
                self._add_agent_to_batch(item_id, all_agents, all_sessions, all_topics,
                                        all_messages, all_agents_to_sessions,
                                        agents_set, sessions_set, topics_set, messages_set)
            elif item_type == "消息":
                self._add_message_to_batch(item_id, all_messages, messages_set)
        
        return {
            "mode": "postgres",
            "schemaHash": self.parsed_data["raw"].get("schemaHash", ""),
            "data": {
                "agents": all_agents,
                "sessions": all_sessions,
                "topics": all_topics,
                "messages": all_messages,
                "agentsToSessions": all_agents_to_sessions
            },
            "stats": {
                "agentCount": len(all_agents),
                "sessionCount": len(all_sessions),
                "topicCount": len(all_topics),
                "messageCount": len(all_messages)
            }
        }
    
    def _add_topic_to_batch(self, topic_id, all_topics, all_messages, topics_set, messages_set):
        """添加主题到批量数据"""
        topic = self.parsed_data["topics"].get(topic_id)
        if topic and topic_id not in topics_set:
            all_topics.append(topic)
            topics_set.add(topic_id)
        
        messages = self.parsed_data["messagesByTopic"].get(topic_id, [])
        for msg in messages:
            msg_id = msg.get("id")
            if msg_id and msg_id not in messages_set:
                all_messages.append(msg)
                messages_set.add(msg_id)
    
    def _add_session_to_batch(self, session_id, all_sessions, all_topics, all_messages,
                             sessions_set, topics_set, messages_set):
        """添加会话到批量数据"""
        session = self.parsed_data["sessions"].get(session_id)
        if session and session_id not in sessions_set:
            all_sessions.append(session)
            sessions_set.add(session_id)
        
        for topic_id, topic in self.parsed_data["topics"].items():
            if topic.get("sessionId") == session_id and topic_id not in topics_set:
                all_topics.append(topic)
                topics_set.add(topic_id)
                
                messages = self.parsed_data["messagesByTopic"].get(topic_id, [])
                for msg in messages:
                    msg_id = msg.get("id")
                    if msg_id and msg_id not in messages_set:
                        all_messages.append(msg)
                        messages_set.add(msg_id)
    
    def _add_agent_to_batch(self, agent_id, all_agents, all_sessions, all_topics,
                           all_messages, all_agents_to_sessions,
                           agents_set, sessions_set, topics_set, messages_set):
        """添加助手到批量数据"""
        agent = self.parsed_data["agents"].get(agent_id)
        if agent and agent_id not in agents_set:
            all_agents.append(agent)
            agents_set.add(agent_id)
        
        for group in self.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                for session_group in group["sessions"]:
                    session_id = session_group["sessionId"]
                    session = session_group.get("session")
                    
                    if session and session_id not in sessions_set:
                        all_sessions.append(session)
                        sessions_set.add(session_id)
                    
                    rel_key = f"{agent_id}_{session_id}"
                    if rel_key not in {f"{r['agentId']}_{r['sessionId']}" for r in all_agents_to_sessions}:
                        all_agents_to_sessions.append({
                            "agentId": agent_id,
                            "sessionId": session_id
                        })
                    
                    for topic_group in session_group["topics"]:
                        topic_id = topic_group["topicId"]
                        topic = topic_group.get("topic")
                        
                        if topic and topic_id not in topics_set:
                            all_topics.append(topic)
                            topics_set.add(topic_id)
                        
                        messages = topic_group.get("messages", [])
                        for msg in messages:
                            msg_id = msg.get("id")
                            if msg_id and msg_id not in messages_set:
                                all_messages.append(msg)
                                messages_set.add(msg_id)
                break
    
    def _add_message_to_batch(self, msg_id, all_messages, messages_set):
        """添加消息到批量数据"""
        for topic_id, messages in self.parsed_data["messagesByTopic"].items():
            for msg in messages:
                if msg.get("id") == msg_id:
                    if msg_id not in messages_set:
                        all_messages.append(msg)
                        messages_set.add(msg_id)
                    break
