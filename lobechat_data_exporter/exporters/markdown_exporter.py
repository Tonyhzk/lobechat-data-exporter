"""
Markdown 导出器
负责构建各种格式的 Markdown 内容
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from ..utils.file_utils import safe_filename, ensure_unique_name, format_datetime


class MarkdownExporter:
    """Markdown 导出器 - 只负责构建 Markdown 内容"""
    
    def __init__(self, parsed_data: Dict):
        """
        初始化导出器
        
        Args:
            parsed_data: 解析后的数据
        """
        self.parsed_data = parsed_data
    
    def build_agent_readme(self, group: Dict, include_metadata: bool, include_system_prompt: bool) -> str:
        """构建助手README内容"""
        lines = [f"# {group['agentLabel']}", ""]
        
        agent = group.get("agent")
        
        if include_metadata and agent:
            lines.append("## 助手信息")
            lines.append("")
            lines.append(f"- **助手ID**: {agent.get('id', '')}")
            if agent.get("model"):
                lines.append(f"- **模型**: {agent['model']}")
            if agent.get("provider"):
                lines.append(f"- **提供商**: {agent['provider']}")
            if agent.get("description"):
                lines.append(f"- **描述**: {agent['description']}")
            lines.append("")
        
        if include_system_prompt and agent and agent.get("systemRole"):
            lines.append("## 系统提示词")
            lines.append("")
            lines.append("```")
            lines.append(agent["systemRole"])
            lines.append("```")
            lines.append("")
        
        # 会话统计
        session_count = len(group["sessions"])
        topic_count = sum(len(s["topics"]) for s in group["sessions"])
        message_count = sum(sum(len(t["messages"]) for t in s["topics"]) for s in group["sessions"])
        
        lines.append("## 统计信息")
        lines.append("")
        lines.append(f"- 会话数量: {session_count}")
        lines.append(f"- 主题数量: {topic_count}")
        lines.append(f"- 消息数量: {message_count}")
        lines.append("")
        
        # 会话列表
        if group["sessions"]:
            lines.append("## 会话列表")
            lines.append("")
            for session_group in group["sessions"]:
                session_msg_count = sum(len(t["messages"]) for t in session_group["topics"])
                lines.append(
                    f"- {session_group['sessionLabel']} "
                    f"({len(session_group['topics'])}主题, {session_msg_count}消息)"
                )
            lines.append("")
        
        return "\n".join(lines)
    
    def build_agent_merged_markdown(self, group: Dict, include_metadata: bool, include_system_prompt: bool) -> str:
        """构建助手整合Markdown内容"""
        lines = [f"# {group['agentLabel']} - 完整对话", ""]
        
        agent = group.get("agent")
        
        if include_metadata and agent:
            lines.append("## 助手信息")
            lines.append("")
            if agent.get("id"):
                lines.append(f"- **ID**: {agent['id']}")
            if agent.get("model"):
                lines.append(f"- **模型**: {agent['model']}")
            if agent.get("provider"):
                lines.append(f"- **提供商**: {agent['provider']}")
            lines.append("")
        
        if include_system_prompt and agent and agent.get("systemRole"):
            lines.append("## 系统提示词")
            lines.append("")
            lines.append("```")
            lines.append(agent["systemRole"])
            lines.append("```")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        # 所有对话
        for session_group in group["sessions"]:
            for topic_group in session_group["topics"]:
                lines.append(f"## {topic_group['topicLabel']}")
                lines.append("")
                
                if include_metadata:
                    if session_group.get("session"):
                        lines.append(f"**会话**: {session_group['sessionLabel']}")
                    if topic_group["topic"] and topic_group["topic"].get("createdAt"):
                        lines.append(f"**创建时间**: {format_datetime(topic_group['topic']['createdAt'])}")
                    lines.append("")
                
                # 消息
                for msg in topic_group["messages"]:
                    role = msg.get("role", "").capitalize()
                    timestamp = format_datetime(msg.get("createdAt") or msg.get("updatedAt"))
                    
                    lines.append(f"### {timestamp} - {role}")
                    lines.append("")
                    lines.extend(self.prettify_content(msg.get("content")))
                    lines.append("")
                
                lines.append("---")
                lines.append("")
        
        return "\n".join(lines)
    
    def build_topic_markdown(self, agent: Optional[Dict], session: Optional[Dict], 
                            topic_group: Dict, agent_label: str,
                            include_metadata: bool, include_system_prompt: bool) -> str:
        """构建单个主题的Markdown内容"""
        lines = [f"# {topic_group['topicLabel']}", ""]
        
        if include_metadata:
            # 会话信息
            if session:
                lines.append("## 会话信息")
                lines.append("")
                if session.get("title"):
                    lines.append(f"- **会话标题**: {session['title']}")
                if session.get("id"):
                    lines.append(f"- **会话ID**: {session['id']}")
                if session.get("createdAt"):
                    lines.append(f"- **创建时间**: {format_datetime(session['createdAt'])}")
                lines.append("")
            
            # 主题信息
            topic = topic_group.get("topic")
            if topic:
                lines.append("## 主题信息")
                lines.append("")
                if topic.get("id"):
                    lines.append(f"- **主题ID**: {topic['id']}")
                if topic.get("createdAt"):
                    lines.append(f"- **创建时间**: {format_datetime(topic['createdAt'])}")
                lines.append("")
        
        # 助手信息
        if agent and include_metadata:
            lines.append("## 助手信息")
            lines.append("")
            lines.append(f"- **助手**: {agent_label}")
            if agent.get("model"):
                lines.append(f"- **模型**: {agent['model']}")
            if agent.get("provider"):
                lines.append(f"- **提供商**: {agent['provider']}")
            lines.append("")
        
        # 系统提示词
        if include_system_prompt and agent and agent.get("systemRole"):
            lines.append("## 系统提示词")
            lines.append("")
            lines.append("```")
            lines.append(agent["systemRole"])
            lines.append("```")
            lines.append("")
        
        # 消息
        lines.append("## 对话内容")
        lines.append("")
        
        for msg in topic_group["messages"]:
            role = msg.get("role", "").capitalize()
            timestamp = format_datetime(msg.get("createdAt") or msg.get("updatedAt"))
            
            lines.append(f"### {timestamp} - {role}")
            lines.append("")
            
            lines.extend(self.prettify_content(msg.get("content")))
            
            # 推理内容
            if msg.get("reasoning"):
                lines.append("**推理过程**:")
                lines.append("")
                lines.extend(self.prettify_content(msg["reasoning"]))
            
            # 搜索内容
            if msg.get("search"):
                lines.append("**搜索上下文**:")
                lines.append("")
                lines.extend(self.prettify_content(msg["search"]))
            
            lines.append("")
        
        return "\n".join(lines)
    
    def build_session_markdown(self, group: Dict, session_group: Dict) -> str:
        """构建会话Markdown内容"""
        lines = [f"# {session_group['sessionLabel']}", ""]
        
        agent = group.get("agent")
        
        if agent:
            lines.append("## 助手信息")
            lines.append("")
            lines.append(f"- **助手**: {group['agentLabel']}")
            if agent.get("model"):
                lines.append(f"- **模型**: {agent['model']}")
            if agent.get("provider"):
                lines.append(f"- **提供商**: {agent['provider']}")
            lines.append("")
        
        # 所有主题
        for topic_group in session_group["topics"]:
            lines.append(f"## {topic_group['topicLabel']}")
            lines.append("")
            
            for msg in topic_group["messages"]:
                role = msg.get("role", "").capitalize()
                timestamp = format_datetime(msg.get("createdAt") or msg.get("updatedAt"))
                
                lines.append(f"### {timestamp} - {role}")
                lines.append("")
                lines.extend(self.prettify_content(msg.get("content")))
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def build_single_message_markdown(self, msg: Dict) -> str:
        """构建单条消息的Markdown内容"""
        lines = ["# 单条消息", ""]
        
        # 消息基本信息
        lines.append("## 消息信息")
        lines.append("")
        
        msg_id = msg.get("id", "")
        if msg_id:
            lines.append(f"- **消息ID**: {msg_id}")
        
        role = msg.get("role", "unknown")
        lines.append(f"- **角色**: {role}")
        
        created_at = msg.get("createdAt") or msg.get("updatedAt")
        if created_at:
            lines.append(f"- **时间**: {format_datetime(created_at)}")
        
        model = msg.get("model")
        if model:
            lines.append(f"- **模型**: {model}")
        
        provider = msg.get("provider")
        if provider:
            lines.append(f"- **提供商**: {provider}")
        
        lines.append("")
        
        # 消息内容
        lines.append("## 消息内容")
        lines.append("")
        lines.extend(self.prettify_content(msg.get("content")))
        lines.append("")
        
        # 推理过程
        if msg.get("reasoning"):
            lines.append("## 推理过程")
            lines.append("")
            lines.extend(self.prettify_content(msg["reasoning"]))
            lines.append("")
        
        # 搜索结果
        if msg.get("search"):
            lines.append("## 搜索结果")
            lines.append("")
            lines.extend(self.prettify_content(msg["search"]))
            lines.append("")
        
        # 元数据
        metadata = msg.get("metadata")
        if metadata:
            lines.append("## 性能指标")
            lines.append("")
            lines.append("| 指标 | 值 |")
            lines.append("|------|-----|")
            
            if metadata.get("totalTokens"):
                lines.append(f"| 总Token数 | {metadata['totalTokens']} |")
            if metadata.get("inputTextTokens"):
                lines.append(f"| 输入Token | {metadata['inputTextTokens']} |")
            if metadata.get("outputTextTokens"):
                lines.append(f"| 输出Token | {metadata['outputTextTokens']} |")
            if metadata.get("cost"):
                lines.append(f"| 费用 | ${metadata['cost']:.6f} |")
            if metadata.get("tps"):
                lines.append(f"| Token/秒 | {metadata['tps']:.2f} |")
            if metadata.get("latency"):
                lines.append(f"| 延迟 | {metadata['latency']}ms |")
            if metadata.get("ttft"):
                lines.append(f"| 首字时间 | {metadata['ttft']}ms |")
            
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def prettify_content(content) -> List[str]:
        """美化内容输出"""
        if content is None or content == "":
            return ["_无内容_", ""]
        
        if isinstance(content, dict) or isinstance(content, list):
            try:
                json_str = json.dumps(content, indent=2, ensure_ascii=False)
                return ["```json", json_str, "```", ""]
            except:
                return [str(content), ""]
        
        text = str(content).strip()
        
        # 尝试解析JSON
        if text.startswith('{') or text.startswith('['):
            try:
                parsed = json.loads(text)
                json_str = json.dumps(parsed, indent=2, ensure_ascii=False)
                return ["```json", json_str, "```", ""]
            except:
                pass
        
        # 如果包含换行符，使用代码块
        if '\n' in text:
            return ["```", text, "```", ""]
        
        return [text, ""]
