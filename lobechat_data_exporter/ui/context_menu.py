"""
右键菜单管理器
负责处理树形视图的右键菜单操作
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import json
from pathlib import Path
from typing import Optional

from ..exporters.markdown_exporter import MarkdownExporter
from ..exporters.json_exporter import JSONExporter
from ..utils.file_utils import (
    safe_filename, ensure_unique_name, set_file_times, 
    get_time_range_from_messages, write_file_with_timestamp,
    write_json_with_timestamp
)


class ContextMenuManager:
    """右键菜单管理器"""
    
    # 树形视图列索引常量
    # columns=("type", "topics", "messages", "time", "id")
    COL_TYPE = 0      # 类型列
    COL_TOPICS = 1    # 主题数列
    COL_MESSAGES = 2  # 消息数列
    COL_TIME = 3      # 时间列
    COL_ID = 4        # ID列
    
    def __init__(self, master, app):
        """
        初始化右键菜单管理器
        
        Args:
            master: 主窗口
            app: 应用实例
        """
        self.master = master
        self.app = app
        self.create_context_menus()
    
    def _get_item_id(self, values):
        """从values中获取ID（第4列，索引3）"""
        if values and len(values) > self.COL_ID:
            return values[self.COL_ID]
        return None
    
    def _get_item_type(self, values):
        """从values中获取类型（第1列，索引0）"""
        if values and len(values) > self.COL_TYPE:
            return values[self.COL_TYPE]
        return None
    
    def _get_item_time_info(self, item_type: str, item_id: str):
        """
        获取项目的时间信息（创建时间和修改时间）
        
        Args:
            item_type: 项目类型 (message/topic/session/agent)
            item_id: 项目ID
        
        Returns:
            (created_at, modified_at) 元组
        """
        if item_type == "message":
            # 单条消息
            for topic_id, messages in self.app.parsed_data["messagesByTopic"].items():
                for msg in messages:
                    if msg.get("id") == item_id:
                        created_at = msg.get("createdAt")
                        modified_at = msg.get("updatedAt") or created_at
                        return created_at, modified_at
        
        elif item_type == "topic":
            # 主题：使用主题创建时间和消息的最晚修改时间
            topic = self.app.parsed_data["topics"].get(item_id)
            messages = self.app.parsed_data["messagesByTopic"].get(item_id, [])
            
            if topic:
                created_at = topic.get("createdAt")
                # 从消息中获取最晚修改时间
                _, latest_modified = get_time_range_from_messages(messages)
                modified_at = latest_modified or topic.get("updatedAt") or created_at
                return created_at, modified_at
        
        elif item_type == "session":
            # 会话：使用会话创建时间和所有消息的最晚修改时间
            session = self.app.parsed_data["sessions"].get(item_id)
            if session:
                created_at = session.get("createdAt")
                
                # 收集该会话所有主题的消息
                all_messages = []
                for topic_id, topic in self.app.parsed_data["topics"].items():
                    if topic.get("sessionId") == item_id:
                        messages = self.app.parsed_data["messagesByTopic"].get(topic_id, [])
                        all_messages.extend(messages)
                
                _, latest_modified = get_time_range_from_messages(all_messages)
                modified_at = latest_modified or session.get("updatedAt") or created_at
                return created_at, modified_at
        
        elif item_type == "agent":
            # 助手：使用助手创建时间和所有消息的最晚修改时间
            agent = self.app.parsed_data["agents"].get(item_id)
            if agent:
                created_at = agent.get("createdAt")
                
                # 收集该助手所有消息
                all_messages = []
                for group in self.app.parsed_data["groups"]:
                    if group["agentId"] == item_id:
                        for session_group in group["sessions"]:
                            for topic_group in session_group["topics"]:
                                all_messages.extend(topic_group.get("messages", []))
                        break
                
                _, latest_modified = get_time_range_from_messages(all_messages)
                modified_at = latest_modified or agent.get("updatedAt") or created_at
                return created_at, modified_at
        
        return None, None
    
    def _get_topic_time_info(self, topic_group):
        """
        获取主题组的时间信息
        
        Args:
            topic_group: 主题组数据
        
        Returns:
            (created_at, modified_at) 元组
        """
        topic = topic_group.get("topic")
        messages = topic_group.get("messages", [])
        
        created_at = topic.get("createdAt") if topic else None
        _, latest_modified = get_time_range_from_messages(messages)
        modified_at = latest_modified or (topic.get("updatedAt") if topic else None) or created_at
        
        return created_at, modified_at
    
    def create_context_menus(self):
        """创建右键菜单 - 统一使用动态生成的菜单"""
        # 所有菜单都动态生成，不再创建静态菜单
        pass
    
    def show_context_menu(self, event):
        """显示右键菜单 - 统一使用动态生成的菜单"""
        # 检查是否有数据树
        if not hasattr(self.app, 'data_tree') or not self.app.data_tree:
            self.app.log_message("右键菜单不可用：树形视图未初始化", "WARNING")
            return
        
        # 检查是否有解析的数据
        if not self.app.parsed_data:
            from tkinter import messagebox
            messagebox.showinfo("提示", "请先解析JSON文件后再使用右键菜单功能")
            return
        
        try:
            # 获取点击的项目
            item = self.app.data_tree.identify_row(event.y)
            if not item:
                return
            
            # 如果点击的项目不在选中列表中，则只选中该项
            current_selection = self.app.data_tree.selection()
            if item not in current_selection:
                self.app.data_tree.selection_set(item)
                current_selection = (item,)
            
            # 统一使用动态菜单（单选和多选都使用同样的菜单结构）
            dynamic_menu = self._create_dynamic_batch_menu(current_selection)
            try:
                dynamic_menu.post(event.x_root, event.y_root)
            finally:
                dynamic_menu.grab_release()
        except Exception as e:
            self.app.log_message(f"显示右键菜单时出错: {str(e)}", "ERROR")
    
    def _create_dynamic_batch_menu(self, selection):
        """根据选中内容动态创建批量菜单"""
        # 分析选中的层级类型
        has_agent = False
        has_topic = False
        has_message = False
        only_messages = True
        
        for item in selection:
            values = self.app.data_tree.item(item, "values")
            if values:
                item_type = values[0]
                if item_type == "助手":
                    has_agent = True
                    only_messages = False
                elif item_type == "主题":
                    has_topic = True
                    only_messages = False
                elif item_type == "消息":
                    has_message = True
        
        # 创建动态菜单
        menu = tk.Menu(self.master, tearoff=0)
        
        # 根据选中层级添加分割导出选项
        if has_agent:
            # 包含助手层级：按助手、按主题、按消息
            menu.add_command(label="📁 按助手分割导出JSON", command=self.batch_split_by_agent_json)
            menu.add_command(label="📁 按助手分割导出Markdown", command=self.batch_split_by_agent_md)
            menu.add_separator()
            menu.add_command(label="📁 按主题分割导出JSON", command=self.batch_split_by_topic_json)
            menu.add_command(label="📁 按主题分割导出Markdown", command=self.batch_split_by_topic_md)
            menu.add_separator()
            menu.add_command(label="📁 按消息分割导出JSON", command=self.batch_split_by_message_json)
            menu.add_command(label="📁 按消息分割导出Markdown", command=self.batch_split_by_message_md)
        elif has_topic:
            # 无助手但有主题层级：按主题、按消息
            menu.add_command(label="📁 按主题分割导出JSON", command=self.batch_split_by_topic_json)
            menu.add_command(label="📁 按主题分割导出Markdown", command=self.batch_split_by_topic_md)
            menu.add_separator()
            menu.add_command(label="📁 按消息分割导出JSON", command=self.batch_split_by_message_json)
            menu.add_command(label="📁 按消息分割导出Markdown", command=self.batch_split_by_message_md)
        elif has_message:
            # 仅选中消息层级：显示按消息分割导出
            menu.add_command(label="📁 按消息分割导出JSON", command=self.batch_split_by_message_json)
            menu.add_command(label="📁 按消息分割导出Markdown", command=self.batch_split_by_message_md)
        
        # 添加分隔线（如果有分割导出选项）
        if has_agent or has_topic or has_message:
            menu.add_separator()
        
        # 复制功能
        menu.add_command(label="📋 复制JSON到剪贴板", command=self.batch_copy_json)
        menu.add_command(label="📋 复制Markdown到剪贴板", command=self.batch_copy_md)
        menu.add_command(label="📋 复制消息内容到剪贴板", command=self.batch_copy_message_content)
        
        menu.add_separator()
        menu.add_command(label="ℹ️ 查看选中统计", command=self.show_batch_stats)
        
        return menu
    
    def export_topic_md(self):
        """导出主题为Markdown"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        topic_id = self._get_item_id(values)  # 使用 _get_item_id 方法获取ID
        topic_label = self.app.data_tree.item(item, "text")
        
        # 找到主题数据
        for group in self.app.parsed_data["groups"]:
            for session_group in group["sessions"]:
                for topic_group in session_group["topics"]:
                    if topic_group["topicId"] == topic_id:
                        file_path = filedialog.asksaveasfilename(
                            title="保存Markdown文件",
                            defaultextension=".md",
                            filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")],
                            initialfile=f"{safe_filename(topic_label, topic_id)}.md"
                        )
                        
                        if file_path:
                            exporter = MarkdownExporter(self.app.parsed_data)
                            content = exporter.build_topic_markdown(
                                group.get("agent"),
                                session_group.get("session"),
                                topic_group,
                                group["agentLabel"],
                                True, True
                            )
                            Path(file_path).write_text(content, encoding='utf-8')
                            self.app.log_message(f"✅ 主题已导出: {file_path}", "SUCCESS")
                            messagebox.showinfo("导出成功", f"主题已保存到:\n{file_path}")
                        return
    
    def export_topic_json(self):
        """导出主题为JSON"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        topic_id = self._get_item_id(values)
        topic_label = self.app.data_tree.item(item, "text")
        
        exporter = JSONExporter(self.app.parsed_data)
        data = exporter.get_selected_item_data("topic", topic_id)
        
        if data:
            file_path = filedialog.asksaveasfilename(
                title="保存JSON文件",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile=f"{safe_filename(topic_label, topic_id)}.json"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.app.log_message(f"✅ 主题已导出为JSON: {file_path}", "SUCCESS")
    
    def copy_topic_md(self):
        """复制主题Markdown到剪贴板"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        topic_id = self._get_item_id(values)
        
        # 找到主题数据
        for group in self.app.parsed_data["groups"]:
            for session_group in group["sessions"]:
                for topic_group in session_group["topics"]:
                    if topic_group["topicId"] == topic_id:
                        exporter = MarkdownExporter(self.app.parsed_data)
                        content = exporter.build_topic_markdown(
                            group.get("agent"),
                            session_group.get("session"),
                            topic_group,
                            group["agentLabel"],
                            True, True
                        )
                        self.app.clipboard_manager.copy_to_clipboard(content)
                        self.app.log_message("✅ 已复制主题Markdown到剪贴板", "SUCCESS")
                        return
    
    def export_agent_merged_md(self):
        """导出助手整合Markdown"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        agent_label = self.app.data_tree.item(item, "text")
        
        # 找到助手数据
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                file_path = filedialog.asksaveasfilename(
                    title="保存Markdown文件",
                    defaultextension=".md",
                    filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")],
                    initialfile=f"{safe_filename(agent_label, agent_id)}_all.md"
                )
                
                if file_path:
                    exporter = MarkdownExporter(self.app.parsed_data)
                    content = exporter.build_agent_merged_markdown(group, True, True)
                    Path(file_path).write_text(content, encoding='utf-8')
                    self.app.log_message(f"✅ 助手对话已导出（整合版）: {file_path}", "SUCCESS")
                    messagebox.showinfo("导出成功", f"助手所有对话已保存到:\n{file_path}")
                return
    
    def export_agent_separated_md(self):
        """导出助手分离Markdown"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        agent_label = self.app.data_tree.item(item, "text")
        
        # 找到助手数据
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                output_dir = filedialog.askdirectory(title="选择导出目录")
                if not output_dir:
                    return
                
                agent_dir = Path(output_dir) / safe_filename(agent_label, agent_id)
                agent_dir.mkdir(exist_ok=True)
                
                exporter = MarkdownExporter(self.app.parsed_data)
                file_count = 0
                used_names = set()
                
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        filename = safe_filename(topic_group["topicLabel"], topic_group["topicId"])
                        filename = ensure_unique_name(filename, used_names)
                        
                        content = exporter.build_topic_markdown(
                            group.get("agent"),
                            session_group.get("session"),
                            topic_group,
                            group["agentLabel"],
                            True, True
                        )
                        
                        file_path = str(agent_dir / f"{filename}.md")
                        # 获取主题的时间信息并设置文件时间戳
                        created_at, modified_at = self._get_topic_time_info(topic_group)
                        write_file_with_timestamp(file_path, content, created_at, modified_at)
                        file_count += 1
                
                self.app.log_message(f"✅ 助手对话已导出（分离版）: {file_count}个文件", "SUCCESS")
                messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{agent_dir}")
                return
    
    def export_agent_json(self):
        """导出助手为JSON"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        agent_label = self.app.data_tree.item(item, "text")
        
        exporter = JSONExporter(self.app.parsed_data)
        data = exporter.get_selected_item_data("agent", agent_id)
        
        if data:
            file_path = filedialog.asksaveasfilename(
                title="保存JSON文件",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile=f"{safe_filename(agent_label, agent_id)}.json"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.app.log_message(f"✅ 助手已导出为JSON: {file_path}", "SUCCESS")
    
    def copy_agent_prompt(self):
        """复制助手提示词到剪贴板"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        
        # 找到助手数据
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                agent = group.get("agent")
                if agent and agent.get("systemRole"):
                    self.app.clipboard_manager.copy_to_clipboard(agent["systemRole"])
                    self.app.log_message("✅ 已复制助手提示词到剪贴板", "SUCCESS")
                else:
                    self.app.log_message("该助手没有系统提示词", "WARNING")
                return


    # ========== 通用导出/复制函数 ==========
    
    def export_item_json(self, item_type: str):
        """通用JSON导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        item_id = self._get_item_id(values)
        item_name = self.app.data_tree.item(item, "text")
        
        exporter = JSONExporter(self.app.parsed_data)
        data = exporter.get_selected_item_data(item_type, item_id)
        
        if data:
            file_path = filedialog.asksaveasfilename(
                title=f"导出{item_type}为JSON",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile=f"{safe_filename(item_name, item_id)}.json"
            )
            
            if file_path:
                # 获取时间信息并设置文件时间戳
                created_at, modified_at = self._get_item_time_info(item_type, item_id)
                write_json_with_timestamp(file_path, data, created_at, modified_at)
                self.app.log_message(f"✅ {item_type}已导出为JSON", "SUCCESS")
    
    def export_item_md(self, item_type: str):
        """通用Markdown导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        item_id = self._get_item_id(values)
        item_name = self.app.data_tree.item(item, "text")
        
        md_content = self._build_markdown_for_item(item, item_type)
        if not md_content:
            return
        
        file_path = filedialog.asksaveasfilename(
            title=f"导出{item_type}为Markdown",
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")],
            initialfile=f"{safe_filename(item_name, item_id)}.md"
        )
        
        if file_path:
            # 获取时间信息并设置文件时间戳
            created_at, modified_at = self._get_item_time_info(item_type, item_id)
            write_file_with_timestamp(file_path, md_content, created_at, modified_at)
            self.app.log_message(f"✅ {item_type}已导出为Markdown", "SUCCESS")
    
    def copy_item_json(self, item_type: str):
        """通用JSON复制"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        item_id = self._get_item_id(values)
        
        exporter = JSONExporter(self.app.parsed_data)
        data = exporter.get_selected_item_data(item_type, item_id)
        
        if data:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            self.app.clipboard_manager.copy_to_clipboard(json_str)
            self.app.log_message(f"✅ 已复制{item_type}的JSON到剪贴板", "SUCCESS")
    
    def copy_item_md(self, item_type: str):
        """通用Markdown复制"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        md_content = self._build_markdown_for_item(item, item_type)
        
        if md_content:
            self.app.clipboard_manager.copy_to_clipboard(md_content)
            self.app.log_message(f"✅ 已复制{item_type}的Markdown到剪贴板", "SUCCESS")
    
    def copy_message_content(self):
        """复制消息内容"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        msg_id = self._get_item_id(values)
        
        for topic_id, messages in self.app.parsed_data["messagesByTopic"].items():
            for msg in messages:
                if msg.get("id") == msg_id:
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        self.app.clipboard_manager.copy_to_clipboard(content)
                        self.app.log_message("✅ 已复制消息内容到剪贴板", "SUCCESS")
                    else:
                        json_str = json.dumps(content, indent=2, ensure_ascii=False)
                        self.app.clipboard_manager.copy_to_clipboard(json_str)
                        self.app.log_message("✅ 已复制消息内容(JSON)到剪贴板", "SUCCESS")
                    return
    
    def _build_markdown_for_item(self, item, item_type: str):
        """构建项目的Markdown内容"""
        values = self.app.data_tree.item(item, "values")
        item_id = self._get_item_id(values)
        
        exporter = MarkdownExporter(self.app.parsed_data)
        
        if item_type == "message":
            for topic_id, messages in self.app.parsed_data["messagesByTopic"].items():
                for msg in messages:
                    if msg.get("id") == item_id:
                        return exporter.build_single_message_markdown(msg)
        
        elif item_type == "topic":
            for group in self.app.parsed_data["groups"]:
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        if topic_group["topicId"] == item_id:
                            return exporter.build_topic_markdown(
                                group.get("agent"),
                                session_group.get("session"),
                                topic_group,
                                group["agentLabel"],
                                True, True
                            )
        
        elif item_type == "session":
            for group in self.app.parsed_data["groups"]:
                for session_group in group["sessions"]:
                    if session_group["sessionId"] == item_id:
                        return exporter.build_session_markdown(group, session_group)
        
        elif item_type == "agent":
            for group in self.app.parsed_data["groups"]:
                if group["agentId"] == item_id:
                    return exporter.build_agent_merged_markdown(group, True, True)
        
        return None
    
    # ========== 分割导出函数 ==========
    
    # ---------- 主题按消息分割 ----------
    
    def export_topic_split_json(self):
        """主题按消息分割JSON导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        topic_id = self._get_item_id(values)
        topic_label = self.app.data_tree.item(item, "text")
        
        # 找到主题数据
        for group in self.app.parsed_data["groups"]:
            for session_group in group["sessions"]:
                for topic_group in session_group["topics"]:
                    if topic_group["topicId"] == topic_id:
                        messages = topic_group.get("messages", [])
                        if not messages:
                            messagebox.showinfo("提示", "该主题没有消息可导出")
                            return
                        
                        output_dir = filedialog.askdirectory(title="选择导出目录")
                        if not output_dir:
                            return
                        
                        topic_dir = Path(output_dir) / safe_filename(topic_label, topic_id)
                        topic_dir.mkdir(exist_ok=True)
                        
                        exporter = JSONExporter(self.app.parsed_data)
                        file_count = 0
                        used_names = set()
                        
                        for idx, msg in enumerate(messages, 1):
                            msg_id = msg.get("id", f"msg_{idx}")
                            role = msg.get("role", "unknown")
                            content_preview = str(msg.get("content", ""))[:30].replace("\n", " ")
                            
                            filename = safe_filename(f"{idx:03d}_{role}_{content_preview}", msg_id)
                            filename = ensure_unique_name(filename, used_names)
                            
                            msg_data = {
                                "mode": "postgres",
                                "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                                "data": {"messages": [msg]}
                            }
                            
                            file_path = str(topic_dir / f"{filename}.json")
                            created_at = msg.get("createdAt")
                            modified_at = msg.get("updatedAt") or created_at
                            write_json_with_timestamp(file_path, msg_data, created_at, modified_at)
                            file_count += 1
                        
                        self.app.log_message(f"✅ 主题已按消息分割导出: {file_count}个JSON文件", "SUCCESS")
                        messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{topic_dir}")
                        return
    
    def export_topic_split_md(self):
        """主题按消息分割Markdown导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        topic_id = self._get_item_id(values)
        topic_label = self.app.data_tree.item(item, "text")
        
        # 找到主题数据
        for group in self.app.parsed_data["groups"]:
            for session_group in group["sessions"]:
                for topic_group in session_group["topics"]:
                    if topic_group["topicId"] == topic_id:
                        messages = topic_group.get("messages", [])
                        if not messages:
                            messagebox.showinfo("提示", "该主题没有消息可导出")
                            return
                        
                        output_dir = filedialog.askdirectory(title="选择导出目录")
                        if not output_dir:
                            return
                        
                        topic_dir = Path(output_dir) / safe_filename(topic_label, topic_id)
                        topic_dir.mkdir(exist_ok=True)
                        
                        exporter = MarkdownExporter(self.app.parsed_data)
                        file_count = 0
                        used_names = set()
                        
                        for idx, msg in enumerate(messages, 1):
                            msg_id = msg.get("id", f"msg_{idx}")
                            role = msg.get("role", "unknown")
                            content_preview = str(msg.get("content", ""))[:30].replace("\n", " ")
                            
                            filename = safe_filename(f"{idx:03d}_{role}_{content_preview}", msg_id)
                            filename = ensure_unique_name(filename, used_names)
                            
                            content = exporter.build_single_message_markdown(msg)
                            
                            file_path = str(topic_dir / f"{filename}.md")
                            created_at = msg.get("createdAt")
                            modified_at = msg.get("updatedAt") or created_at
                            write_file_with_timestamp(file_path, content, created_at, modified_at)
                            file_count += 1
                        
                        self.app.log_message(f"✅ 主题已按消息分割导出: {file_count}个Markdown文件", "SUCCESS")
                        messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{topic_dir}")
                        return
    
    # ---------- 会话按主题分割 ----------
    
    def export_session_split_json(self):
        """会话按主题分割JSON导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        session_id = self._get_item_id(values)
        session_label = self.app.data_tree.item(item, "text")
        
        # 找到会话数据
        for group in self.app.parsed_data["groups"]:
            for session_group in group["sessions"]:
                if session_group["sessionId"] == session_id:
                    topics = session_group.get("topics", [])
                    if not topics:
                        messagebox.showinfo("提示", "该会话没有主题可导出")
                        return
                    
                    output_dir = filedialog.askdirectory(title="选择导出目录")
                    if not output_dir:
                        return
                    
                    session_dir = Path(output_dir) / safe_filename(session_label, session_id)
                    session_dir.mkdir(exist_ok=True)
                    
                    exporter = JSONExporter(self.app.parsed_data)
                    file_count = 0
                    used_names = set()
                    
                    for topic_group in topics:
                        topic_id = topic_group["topicId"]
                        topic_label = topic_group["topicLabel"]
                        topic = topic_group.get("topic")
                        messages = topic_group.get("messages", [])
                        
                        filename = safe_filename(topic_label, topic_id)
                        filename = ensure_unique_name(filename, used_names)
                        
                        topic_data = {
                            "mode": "postgres",
                            "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                            "data": {
                                "topics": [topic] if topic else [],
                                "messages": messages
                            }
                        }
                        
                        file_path = str(session_dir / f"{filename}.json")
                        created_at, modified_at = self._get_topic_time_info(topic_group)
                        write_json_with_timestamp(file_path, topic_data, created_at, modified_at)
                        file_count += 1
                    
                    self.app.log_message(f"✅ 会话已按主题分割导出: {file_count}个JSON文件", "SUCCESS")
                    messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{session_dir}")
                    return
    
    def export_session_split_md(self):
        """会话按主题分割Markdown导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        session_id = self._get_item_id(values)
        session_label = self.app.data_tree.item(item, "text")
        
        # 找到会话数据
        for group in self.app.parsed_data["groups"]:
            for session_group in group["sessions"]:
                if session_group["sessionId"] == session_id:
                    topics = session_group.get("topics", [])
                    if not topics:
                        messagebox.showinfo("提示", "该会话没有主题可导出")
                        return
                    
                    output_dir = filedialog.askdirectory(title="选择导出目录")
                    if not output_dir:
                        return
                    
                    session_dir = Path(output_dir) / safe_filename(session_label, session_id)
                    session_dir.mkdir(exist_ok=True)
                    
                    exporter = MarkdownExporter(self.app.parsed_data)
                    file_count = 0
                    used_names = set()
                    
                    for topic_group in topics:
                        topic_id = topic_group["topicId"]
                        topic_label = topic_group["topicLabel"]
                        
                        filename = safe_filename(topic_label, topic_id)
                        filename = ensure_unique_name(filename, used_names)
                        
                        content = exporter.build_topic_markdown(
                            group.get("agent"),
                            session_group.get("session"),
                            topic_group,
                            group["agentLabel"],
                            True, True
                        )
                        
                        file_path = str(session_dir / f"{filename}.md")
                        created_at, modified_at = self._get_topic_time_info(topic_group)
                        write_file_with_timestamp(file_path, content, created_at, modified_at)
                        file_count += 1
                    
                    self.app.log_message(f"✅ 会话已按主题分割导出: {file_count}个Markdown文件", "SUCCESS")
                    messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{session_dir}")
                    return
    
    # ---------- 助手按会话分割 ----------
    
    def export_agent_split_by_session_json(self):
        """助手按会话分割JSON导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        agent_label = self.app.data_tree.item(item, "text")
        
        # 找到助手数据
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                sessions = group.get("sessions", [])
                if not sessions:
                    messagebox.showinfo("提示", "该助手没有会话可导出")
                    return
                
                output_dir = filedialog.askdirectory(title="选择导出目录")
                if not output_dir:
                    return
                
                agent_dir = Path(output_dir) / safe_filename(agent_label, agent_id)
                agent_dir.mkdir(exist_ok=True)
                
                file_count = 0
                used_names = set()
                
                for session_group in sessions:
                    session_id = session_group["sessionId"]
                    session_label = session_group["sessionLabel"]
                    session = session_group.get("session")
                    
                    # 收集会话下所有主题和消息
                    session_topics = []
                    session_messages = []
                    
                    for topic_group in session_group.get("topics", []):
                        topic = topic_group.get("topic")
                        if topic:
                            session_topics.append(topic)
                        messages = topic_group.get("messages", [])
                        session_messages.extend(messages)
                    
                    filename = safe_filename(session_label, session_id)
                    filename = ensure_unique_name(filename, used_names)
                    
                    session_data = {
                        "mode": "postgres",
                        "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                        "data": {
                            "sessions": [session] if session else [],
                            "topics": session_topics,
                            "messages": session_messages
                        }
                    }
                    
                    file_path = str(agent_dir / f"{filename}.json")
                    created_at, modified_at = get_time_range_from_messages(session_messages)
                    if not created_at and session:
                        created_at = session.get("createdAt")
                    write_json_with_timestamp(file_path, session_data, created_at, modified_at)
                    file_count += 1
                
                self.app.log_message(f"✅ 助手已按会话分割导出: {file_count}个JSON文件", "SUCCESS")
                messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{agent_dir}")
                return
    
    def export_agent_split_by_session_md(self):
        """助手按会话分割Markdown导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        agent_label = self.app.data_tree.item(item, "text")
        
        # 找到助手数据
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                sessions = group.get("sessions", [])
                if not sessions:
                    messagebox.showinfo("提示", "该助手没有会话可导出")
                    return
                
                output_dir = filedialog.askdirectory(title="选择导出目录")
                if not output_dir:
                    return
                
                agent_dir = Path(output_dir) / safe_filename(agent_label, agent_id)
                agent_dir.mkdir(exist_ok=True)
                
                exporter = MarkdownExporter(self.app.parsed_data)
                file_count = 0
                used_names = set()
                
                for session_group in sessions:
                    session_id = session_group["sessionId"]
                    session_label = session_group["sessionLabel"]
                    
                    filename = safe_filename(session_label, session_id)
                    filename = ensure_unique_name(filename, used_names)
                    
                    content = exporter.build_session_markdown(group, session_group)
                    
                    # 获取会话的时间信息
                    all_messages = []
                    for topic_group in session_group.get("topics", []):
                        all_messages.extend(topic_group.get("messages", []))
                    
                    file_path = str(agent_dir / f"{filename}.md")
                    created_at, modified_at = get_time_range_from_messages(all_messages)
                    session = session_group.get("session")
                    if not created_at and session:
                        created_at = session.get("createdAt")
                    write_file_with_timestamp(file_path, content, created_at, modified_at)
                    file_count += 1
                
                self.app.log_message(f"✅ 助手已按会话分割导出: {file_count}个Markdown文件", "SUCCESS")
                messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{agent_dir}")
                return
    
    # ---------- 助手按主题分割 ----------
    
    def export_agent_split_by_topic_json(self):
        """助手按主题分割JSON导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        agent_label = self.app.data_tree.item(item, "text")
        
        # 找到助手数据
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                output_dir = filedialog.askdirectory(title="选择导出目录")
                if not output_dir:
                    return
                
                agent_dir = Path(output_dir) / safe_filename(agent_label, agent_id)
                agent_dir.mkdir(exist_ok=True)
                
                file_count = 0
                used_names = set()
                
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        topic_id = topic_group["topicId"]
                        topic_label = topic_group["topicLabel"]
                        topic = topic_group.get("topic")
                        messages = topic_group.get("messages", [])
                        
                        filename = safe_filename(topic_label, topic_id)
                        filename = ensure_unique_name(filename, used_names)
                        
                        topic_data = {
                            "mode": "postgres",
                            "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                            "data": {
                                "topics": [topic] if topic else [],
                                "messages": messages
                            }
                        }
                        
                        file_path = str(agent_dir / f"{filename}.json")
                        created_at, modified_at = self._get_topic_time_info(topic_group)
                        write_json_with_timestamp(file_path, topic_data, created_at, modified_at)
                        file_count += 1
                
                if file_count == 0:
                    messagebox.showinfo("提示", "该助手没有主题可导出")
                    return
                
                self.app.log_message(f"✅ 助手已按主题分割导出: {file_count}个JSON文件", "SUCCESS")
                messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{agent_dir}")
                return
    
    def export_agent_split_by_topic_md(self):
        """助手按主题分割Markdown导出"""
        # 复用已有的export_agent_separated_md功能
        self.export_agent_separated_md()
    
    def export_agent_prompt_md(self):
        """导出助手提示词Markdown"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = self._get_item_id(values)
        
        for group in self.app.parsed_data["groups"]:
            if group["agentId"] == agent_id:
                agent = group.get("agent")
                if not agent or not agent.get("systemRole"):
                    self.app.log_message("该助手没有系统提示词", "WARNING")
                    return
                
                safe_name = safe_filename(group["agentLabel"], agent_id)
                file_path = filedialog.asksaveasfilename(
                    title="导出助手提示词",
                    defaultextension=".md",
                    filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")],
                    initialfile=f"{safe_name}_prompt.md"
                )
                
                if file_path:
                    content = f"# {group['agentLabel']} - 系统提示词\n\n```\n{agent['systemRole']}\n```\n"
                    # 使用助手的创建时间作为文件时间戳
                    created_at = agent.get("createdAt")
                    modified_at = agent.get("updatedAt") or created_at
                    write_file_with_timestamp(file_path, content, created_at, modified_at)
                    self.app.log_message(f"✅ 助手提示词已导出: {file_path}", "SUCCESS")
                break
    
    # ========== 批量操作函数 ==========
    
    def batch_export_json(self):
        """批量导出JSON"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data:
                self.app.log_message("没有选中任何项目", "WARNING")
                return
            
            from datetime import datetime
            file_path = filedialog.asksaveasfilename(
                title="批量导出JSON",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
                initialfile=f"batch_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if not file_path:
                return
            
            # 从批量数据中获取时间范围
            all_messages = batch_data["data"].get("messages", [])
            created_at, modified_at = get_time_range_from_messages(all_messages)
            
            # 写入文件并设置时间戳
            write_json_with_timestamp(file_path, batch_data, created_at, modified_at)
            
            stats = batch_data["stats"]
            self.app.log_message(
                f"✅ 批量导出成功 - "
                f"{stats['agentCount']}助手, {stats['sessionCount']}会话, "
                f"{stats['topicCount']}主题, {stats['messageCount']}消息",
                "SUCCESS"
            )
            messagebox.showinfo("导出成功", f"已导出到:\n{file_path}")
            
        except Exception as e:
            self.app.log_message(f"批量导出失败: {str(e)}", "ERROR")
            messagebox.showerror("批量导出失败", str(e))
    
    def batch_export_md(self):
        """批量导出Markdown（ZIP压缩包）"""
        try:
            selection = self.app.data_tree.selection()
            if not selection:
                self.app.log_message("没有选中任何项目", "WARNING")
                return
            
            from datetime import datetime
            import zipfile
            from ..utils.file_utils import ensure_unique_name
            
            file_path = filedialog.asksaveasfilename(
                title="批量导出Markdown",
                defaultextension=".zip",
                filetypes=[("ZIP文件", "*.zip"), ("所有文件", "*.*")],
                initialfile=f"batch_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
            
            if not file_path:
                return
            
            # 类型映射：中文→英文
            type_map = {"消息": "message", "主题": "topic", "会话": "session", "助手": "agent"}
            
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                used_names = set()
                file_count = 0
                
                for item in selection:
                    values = self.app.data_tree.item(item, "values")
                    if not values:
                        continue
                    
                    item_name = self.app.data_tree.item(item, "text")
                    item_id = self._get_item_id(values)
                    item_type_cn = values[0]  # 中文类型
                    item_type_en = type_map.get(item_type_cn, item_type_cn)  # 转换为英文
                    
                    md_content = self._build_markdown_for_item(item, item_type_en)
                    if not md_content:
                        continue
                    
                    filename = safe_filename(item_name, item_id)
                    filename = ensure_unique_name(filename, used_names)
                    
                    zipf.writestr(f"{filename}.md", md_content.encode('utf-8'))
                    file_count += 1
            
            self.app.log_message(f"✅ 批量导出成功 - 共{file_count}个Markdown文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{file_path}")
            
        except Exception as e:
            self.app.log_message(f"批量导出失败: {str(e)}", "ERROR")
            messagebox.showerror("批量导出失败", str(e))
    
    def batch_copy_json(self):
        """批量复制JSON到剪贴板"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data:
                self.app.log_message("没有选中任何项目", "WARNING")
                return
            
            json_str = json.dumps(batch_data, indent=2, ensure_ascii=False)
            self.app.clipboard_manager.copy_to_clipboard(json_str)
            
            stats = batch_data["stats"]
            self.app.log_message(
                f"✅ 已复制批量数据到剪贴板 - "
                f"{stats['agentCount']}助手, {stats['sessionCount']}会话, "
                f"{stats['topicCount']}主题, {stats['messageCount']}消息",
                "SUCCESS"
            )
        except Exception as e:
            self.app.log_message(f"批量复制失败: {str(e)}", "ERROR")
            messagebox.showerror("批量复制失败", str(e))
    
    def batch_copy_md(self):
        """批量复制Markdown到剪贴板"""
        try:
            selection = self.app.data_tree.selection()
            if not selection:
                self.app.log_message("没有选中任何项目", "WARNING")
                return
            
            from datetime import datetime
            md_lines = ["# 批量导出的对话", "", f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
            
            # 类型映射：中文→英文
            type_map = {"消息": "message", "主题": "topic", "会话": "session", "助手": "agent"}
            
            for item in selection:
                values = self.app.data_tree.item(item, "values")
                if not values:
                    continue
                
                item_type_cn = values[0]  # 中文类型
                item_type_en = type_map.get(item_type_cn, item_type_cn)  # 转换为英文
                
                md_content = self._build_markdown_for_item(item, item_type_en)
                if md_content:
                    md_lines.append(md_content)
                    md_lines.append("\n---\n")
            
            md_text = "\n".join(md_lines)
            self.app.clipboard_manager.copy_to_clipboard(md_text)
            
            self.app.log_message(f"✅ 已复制{len(selection)}个项目的Markdown到剪贴板", "SUCCESS")
        except Exception as e:
            self.app.log_message(f"批量复制失败: {str(e)}", "ERROR")
            messagebox.showerror("批量复制失败", str(e))
    
    def batch_copy_message_content(self):
        """批量复制消息内容到剪贴板（纯文字）"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["messages"]:
                self.app.log_message("没有选中任何消息数据", "WARNING")
                return
            
            content_lines = []
            for msg in batch_data["data"]["messages"]:
                content = msg.get("content", "")
                if isinstance(content, str):
                    content_lines.append(content)
                else:
                    # 如果content不是字符串（如列表或字典），尝试转换
                    content_lines.append(json.dumps(content, ensure_ascii=False))
            
            combined_content = "\n\n---\n\n".join(content_lines)
            self.app.clipboard_manager.copy_to_clipboard(combined_content)
            
            msg_count = len(batch_data["data"]["messages"])
            self.app.log_message(f"✅ 已复制{msg_count}条消息内容到剪贴板", "SUCCESS")
        except Exception as e:
            self.app.log_message(f"批量复制失败: {str(e)}", "ERROR")
            messagebox.showerror("批量复制失败", str(e))
    
    def show_batch_stats(self):
        """显示批量统计"""
        selection = self.app.data_tree.selection()
        if not selection:
            messagebox.showinfo("统计信息", "没有选中任何项目")
            return
        
        type_counts = {"助手": 0, "会话": 0, "主题": 0, "消息": 0}
        
        for item in selection:
            values = self.app.data_tree.item(item, "values")
            if values:
                item_type = values[0]
                if item_type in type_counts:
                    type_counts[item_type] += 1
        
        # 获取批量数据统计
        batch_data = self._get_batch_selected_data()
        stats = batch_data["stats"] if batch_data else {}
        
        stats_text = f"""批量选中统计信息

选中项目：
• 助手节点: {type_counts['助手']} 个
• 会话节点: {type_counts['会话']} 个
• 主题节点: {type_counts['主题']} 个
• 消息节点: {type_counts['消息']} 个
• 总计: {len(selection)} 个

包含数据：
• 助手数据: {stats.get('agentCount', 0)} 个
• 会话数据: {stats.get('sessionCount', 0)} 个
• 主题数据: {stats.get('topicCount', 0)} 个
• 消息数据: {stats.get('messageCount', 0)} 条
"""
        
        messagebox.showinfo("批量选中统计", stats_text)
        self.app.log_message(f"查看批量统计 - 选中{len(selection)}项", "INFO")
    
    # ========== 批量数据收集辅助函数 ==========
    
    def _get_batch_selected_data(self):
        """获取批量选中的数据"""
        selection = self.app.data_tree.selection()
        if not selection:
            return None
        
        # 收集所有选中项的数据
        all_agents = []
        all_sessions = []
        all_topics = []
        all_messages = []
        all_agents_to_sessions = []
        
        agents_set = set()
        sessions_set = set()
        topics_set = set()
        messages_set = set()
        
        for item in selection:
            values = self.app.data_tree.item(item, "values")
            if not values:
                continue
            
            item_type = values[0]
            item_id = self._get_item_id(values)
            
            if item_type == "主题":
                # 添加主题和消息
                # 首先尝试从标准topics字典获取
                topic = self.app.parsed_data["topics"].get(item_id)
                if topic and item_id not in topics_set:
                    all_topics.append(topic)
                    topics_set.add(item_id)
                
                # 获取消息 - 先尝试从标准messagesByTopic获取
                messages = self.app.parsed_data["messagesByTopic"].get(item_id, [])
                
                # 如果是默认对话（topicId以default_开头），从groups中获取消息
                if not messages and item_id.startswith("default_"):
                    for group in self.app.parsed_data["groups"]:
                        for session_group in group["sessions"]:
                            for topic_group in session_group["topics"]:
                                if topic_group["topicId"] == item_id:
                                    messages = topic_group.get("messages", [])
                                    # 如果topic不在标准字典中，从topic_group获取
                                    if not topic and topic_group.get("topic"):
                                        topic = topic_group["topic"]
                                        if item_id not in topics_set:
                                            all_topics.append(topic)
                                            topics_set.add(item_id)
                                    break
                            if messages:
                                break
                        if messages:
                            break
                
                for msg in messages:
                    msg_id = msg.get("id")
                    if msg_id and msg_id not in messages_set:
                        all_messages.append(msg)
                        messages_set.add(msg_id)
            
            elif item_type == "会话":
                # 添加会话、所有主题和消息
                session = self.app.parsed_data["sessions"].get(item_id)
                if session and item_id not in sessions_set:
                    all_sessions.append(session)
                    sessions_set.add(item_id)
                
                # 找到该会话的所有主题
                for topic_id, topic in self.app.parsed_data["topics"].items():
                    if topic.get("sessionId") == item_id and topic_id not in topics_set:
                        all_topics.append(topic)
                        topics_set.add(topic_id)
                        
                        # 添加主题的消息
                        messages = self.app.parsed_data["messagesByTopic"].get(topic_id, [])
                        for msg in messages:
                            msg_id = msg.get("id")
                            if msg_id and msg_id not in messages_set:
                                all_messages.append(msg)
                                messages_set.add(msg_id)
            
            elif item_type == "助手":
                # 添加助手、所有会话、主题和消息
                agent = self.app.parsed_data["agents"].get(item_id)
                if agent and item_id not in agents_set:
                    all_agents.append(agent)
                    agents_set.add(item_id)
                
                # 找到该助手的所有数据
                for group in self.app.parsed_data["groups"]:
                    if group["agentId"] == item_id:
                        for session_group in group["sessions"]:
                            session_id = session_group["sessionId"]
                            session = session_group.get("session")
                            
                            if session and session_id not in sessions_set:
                                all_sessions.append(session)
                                sessions_set.add(session_id)
                            
                            # 添加关联关系
                            rel_key = f"{item_id}_{session_id}"
                            if rel_key not in {f"{r['agentId']}_{r['sessionId']}" for r in all_agents_to_sessions}:
                                all_agents_to_sessions.append({
                                    "agentId": item_id,
                                    "sessionId": session_id
                                })
                            
                            # 该会话的所有主题和消息
                            for topic_group in session_group["topics"]:
                                topic_id = topic_group["topicId"]
                                topic = topic_group.get("topic")
                                
                                if topic and topic_id not in topics_set:
                                    all_topics.append(topic)
                                    topics_set.add(topic_id)
                                
                                # 该主题的所有消息
                                messages = topic_group.get("messages", [])
                                for msg in messages:
                                    msg_id = msg.get("id")
                                    if msg_id and msg_id not in messages_set:
                                        all_messages.append(msg)
                                        messages_set.add(msg_id)
                        break
            
            elif item_type == "消息":
                # 添加单条消息 - 先从标准messagesByTopic获取
                found = False
                for topic_id, messages in self.app.parsed_data["messagesByTopic"].items():
                    for msg in messages:
                        if msg.get("id") == item_id:
                            if item_id not in messages_set:
                                all_messages.append(msg)
                                messages_set.add(item_id)
                            found = True
                            break
                    if found:
                        break
                
                # 如果没找到，从groups中获取（可能是默认对话的消息）
                if not found:
                    for group in self.app.parsed_data["groups"]:
                        for session_group in group["sessions"]:
                            for topic_group in session_group["topics"]:
                                for msg in topic_group.get("messages", []):
                                    if msg.get("id") == item_id:
                                        if item_id not in messages_set:
                                            all_messages.append(msg)
                                            messages_set.add(item_id)
                                        found = True
                                        break
                                if found:
                                    break
                            if found:
                                break
                        if found:
                            break
        
        return {
            "mode": "postgres",
            "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
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
    
    # ========== 批量分割导出函数 ==========
    
    def batch_split_by_agent_json(self):
        """批量按助手分割导出JSON - 目录结构: 总文件夹/助手.json"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["agents"]:
                self.app.log_message("没有选中任何助手数据", "WARNING")
                return
            
            from datetime import datetime
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                return
            
            export_dir = Path(output_dir) / f"batch_agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_dir.mkdir(exist_ok=True)
            
            file_count = 0
            agent_ids_set = {a.get("id") for a in batch_data["data"]["agents"]}
            used_names = set()
            
            for group in self.app.parsed_data["groups"]:
                agent_id = group["agentId"]
                if agent_id not in agent_ids_set:
                    continue
                
                agent_label = group["agentLabel"]
                agent = group.get("agent")
                
                # 收集助手的所有数据
                agent_sessions = []
                agent_topics = []
                agent_messages = []
                agent_relations = []
                
                for session_group in group["sessions"]:
                    session = session_group.get("session")
                    if session:
                        agent_sessions.append(session)
                        agent_relations.append({"agentId": agent_id, "sessionId": session_group["sessionId"]})
                    
                    for topic_group in session_group["topics"]:
                        topic = topic_group.get("topic")
                        if topic:
                            agent_topics.append(topic)
                        agent_messages.extend(topic_group.get("messages", []))
                
                filename = safe_filename(agent_label, agent_id)
                filename = ensure_unique_name(filename, used_names)
                
                agent_data = {
                    "mode": "postgres",
                    "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                    "data": {
                        "agents": [agent] if agent else [],
                        "sessions": agent_sessions,
                        "topics": agent_topics,
                        "messages": agent_messages,
                        "agentsToSessions": agent_relations
                    }
                }
                
                file_path = str(export_dir / f"{filename}.json")
                created_at, modified_at = get_time_range_from_messages(agent_messages)
                if not created_at and agent:
                    created_at = agent.get("createdAt")
                write_json_with_timestamp(file_path, agent_data, created_at, modified_at)
                file_count += 1
            
            self.app.log_message(f"✅ 批量按助手分割导出: {file_count}个JSON文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{export_dir}")
            
        except Exception as e:
            self.app.log_message(f"批量分割导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def batch_split_by_agent_md(self):
        """批量按助手分割导出Markdown - 目录结构: 总文件夹/助手.md"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["agents"]:
                self.app.log_message("没有选中任何助手数据", "WARNING")
                return
            
            from datetime import datetime
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                return
            
            export_dir = Path(output_dir) / f"batch_agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_dir.mkdir(exist_ok=True)
            
            exporter = MarkdownExporter(self.app.parsed_data)
            file_count = 0
            agent_ids_set = {a.get("id") for a in batch_data["data"]["agents"]}
            used_names = set()
            
            for group in self.app.parsed_data["groups"]:
                agent_id = group["agentId"]
                if agent_id not in agent_ids_set:
                    continue
                
                agent_label = group["agentLabel"]
                agent = group.get("agent")
                
                filename = safe_filename(agent_label, agent_id)
                filename = ensure_unique_name(filename, used_names)
                
                content = exporter.build_agent_merged_markdown(group, True, True)
                
                file_path = str(export_dir / f"{filename}.md")
                
                # 获取时间范围
                all_messages = []
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        all_messages.extend(topic_group.get("messages", []))
                
                created_at, modified_at = get_time_range_from_messages(all_messages)
                if not created_at and agent:
                    created_at = agent.get("createdAt")
                write_file_with_timestamp(file_path, content, created_at, modified_at)
                file_count += 1
            
            self.app.log_message(f"✅ 批量按助手分割导出: {file_count}个Markdown文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{export_dir}")
            
        except Exception as e:
            self.app.log_message(f"批量分割导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def batch_split_by_topic_json(self):
        """批量按主题分割导出JSON - 目录结构: 总文件夹/助手文件夹/主题.json"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["topics"]:
                self.app.log_message("没有选中任何主题数据", "WARNING")
                return
            
            from datetime import datetime
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                return
            
            export_dir = Path(output_dir) / f"batch_topics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_dir.mkdir(exist_ok=True)
            
            file_count = 0
            topic_ids_set = {t.get("id") for t in batch_data["data"]["topics"]}
            
            for group in self.app.parsed_data["groups"]:
                agent_label = group["agentLabel"]
                agent_id = group["agentId"]
                agent_dir_name = safe_filename(agent_label, agent_id)
                agent_dir = None  # 延迟创建
                used_names = set()
                
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        topic_id = topic_group["topicId"]
                        if topic_id not in topic_ids_set:
                            continue
                        
                        # 延迟创建助手目录
                        if agent_dir is None:
                            agent_dir = export_dir / agent_dir_name
                            agent_dir.mkdir(exist_ok=True)
                        
                        topic = topic_group.get("topic")
                        messages = topic_group.get("messages", [])
                        topic_label = topic_group["topicLabel"]
                        
                        filename = safe_filename(topic_label, topic_id)
                        filename = ensure_unique_name(filename, used_names)
                        
                        topic_data = {
                            "mode": "postgres",
                            "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                            "data": {"topics": [topic] if topic else [], "messages": messages}
                        }
                        
                        file_path = str(agent_dir / f"{filename}.json")
                        created_at, modified_at = self._get_topic_time_info(topic_group)
                        write_json_with_timestamp(file_path, topic_data, created_at, modified_at)
                        file_count += 1
            
            self.app.log_message(f"✅ 批量按主题分割导出: {file_count}个JSON文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{export_dir}")
            
        except Exception as e:
            self.app.log_message(f"批量分割导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def batch_split_by_topic_md(self):
        """批量按主题分割导出Markdown - 目录结构: 总文件夹/助手文件夹/主题.md"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["topics"]:
                self.app.log_message("没有选中任何主题数据", "WARNING")
                return
            
            from datetime import datetime
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                return
            
            export_dir = Path(output_dir) / f"batch_topics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_dir.mkdir(exist_ok=True)
            
            exporter = MarkdownExporter(self.app.parsed_data)
            file_count = 0
            topic_ids_set = {t.get("id") for t in batch_data["data"]["topics"]}
            
            for group in self.app.parsed_data["groups"]:
                agent_label = group["agentLabel"]
                agent_id = group["agentId"]
                agent_dir_name = safe_filename(agent_label, agent_id)
                agent_dir = None
                used_names = set()
                
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        topic_id = topic_group["topicId"]
                        if topic_id not in topic_ids_set:
                            continue
                        
                        if agent_dir is None:
                            agent_dir = export_dir / agent_dir_name
                            agent_dir.mkdir(exist_ok=True)
                        
                        topic_label = topic_group["topicLabel"]
                        filename = safe_filename(topic_label, topic_id)
                        filename = ensure_unique_name(filename, used_names)
                        
                        content = exporter.build_topic_markdown(
                            group.get("agent"), session_group.get("session"),
                            topic_group, group["agentLabel"], True, True
                        )
                        
                        file_path = str(agent_dir / f"{filename}.md")
                        created_at, modified_at = self._get_topic_time_info(topic_group)
                        write_file_with_timestamp(file_path, content, created_at, modified_at)
                        file_count += 1
            
            self.app.log_message(f"✅ 批量按主题分割导出: {file_count}个Markdown文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{export_dir}")
            
        except Exception as e:
            self.app.log_message(f"批量分割导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def batch_split_by_message_json(self):
        """批量按消息分割导出JSON - 目录结构: 总文件夹/助手文件夹/主题文件夹/消息.json"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["messages"]:
                self.app.log_message("没有选中任何消息数据", "WARNING")
                return
            
            from datetime import datetime
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                return
            
            export_dir = Path(output_dir) / f"batch_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_dir.mkdir(exist_ok=True)
            
            file_count = 0
            msg_ids_set = {m.get("id") for m in batch_data["data"]["messages"]}
            
            for group in self.app.parsed_data["groups"]:
                agent_label = group["agentLabel"]
                agent_id = group["agentId"]
                agent_dir_name = safe_filename(agent_label, agent_id)
                agent_dir = None
                used_topic_names = set()
                
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        topic_label = topic_group["topicLabel"]
                        topic_id = topic_group["topicId"]
                        topic_dir = None
                        used_msg_names = set()
                        msg_idx = 0
                        
                        for msg in topic_group.get("messages", []):
                            if msg.get("id") not in msg_ids_set:
                                continue
                            
                            if agent_dir is None:
                                agent_dir = export_dir / agent_dir_name
                                agent_dir.mkdir(exist_ok=True)
                            
                            if topic_dir is None:
                                topic_dir_name = safe_filename(topic_label, topic_id)
                                topic_dir_name = ensure_unique_name(topic_dir_name, used_topic_names)
                                topic_dir = agent_dir / topic_dir_name
                                topic_dir.mkdir(exist_ok=True)
                            
                            msg_idx += 1
                            msg_id = msg.get("id", f"msg_{msg_idx}")
                            role = msg.get("role", "unknown")
                            content_preview = str(msg.get("content", ""))[:30].replace("\n", " ")
                            
                            filename = safe_filename(f"{msg_idx:03d}_{role}_{content_preview}", msg_id)
                            filename = ensure_unique_name(filename, used_msg_names)
                            
                            msg_data = {
                                "mode": "postgres",
                                "schemaHash": self.app.parsed_data["raw"].get("schemaHash", ""),
                                "data": {"messages": [msg]}
                            }
                            
                            file_path = str(topic_dir / f"{filename}.json")
                            created_at = msg.get("createdAt")
                            modified_at = msg.get("updatedAt") or created_at
                            write_json_with_timestamp(file_path, msg_data, created_at, modified_at)
                            file_count += 1
            
            self.app.log_message(f"✅ 批量按消息分割导出: {file_count}个JSON文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个JSON文件到:\n{export_dir}")
            
        except Exception as e:
            self.app.log_message(f"批量分割导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def batch_split_by_message_md(self):
        """批量按消息分割导出Markdown - 目录结构: 总文件夹/助手文件夹/主题文件夹/消息.md"""
        try:
            batch_data = self._get_batch_selected_data()
            if not batch_data or not batch_data["data"]["messages"]:
                self.app.log_message("没有选中任何消息数据", "WARNING")
                return
            
            from datetime import datetime
            output_dir = filedialog.askdirectory(title="选择导出目录")
            if not output_dir:
                return
            
            export_dir = Path(output_dir) / f"batch_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_dir.mkdir(exist_ok=True)
            
            exporter = MarkdownExporter(self.app.parsed_data)
            file_count = 0
            msg_ids_set = {m.get("id") for m in batch_data["data"]["messages"]}
            
            for group in self.app.parsed_data["groups"]:
                agent_label = group["agentLabel"]
                agent_id = group["agentId"]
                agent_dir_name = safe_filename(agent_label, agent_id)
                agent_dir = None
                used_topic_names = set()
                
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        topic_label = topic_group["topicLabel"]
                        topic_id = topic_group["topicId"]
                        topic_dir = None
                        used_msg_names = set()
                        msg_idx = 0
                        
                        for msg in topic_group.get("messages", []):
                            if msg.get("id") not in msg_ids_set:
                                continue
                            
                            if agent_dir is None:
                                agent_dir = export_dir / agent_dir_name
                                agent_dir.mkdir(exist_ok=True)
                            
                            if topic_dir is None:
                                topic_dir_name = safe_filename(topic_label, topic_id)
                                topic_dir_name = ensure_unique_name(topic_dir_name, used_topic_names)
                                topic_dir = agent_dir / topic_dir_name
                                topic_dir.mkdir(exist_ok=True)
                            
                            msg_idx += 1
                            msg_id = msg.get("id", f"msg_{msg_idx}")
                            role = msg.get("role", "unknown")
                            content_preview = str(msg.get("content", ""))[:30].replace("\n", " ")
                            
                            filename = safe_filename(f"{msg_idx:03d}_{role}_{content_preview}", msg_id)
                            filename = ensure_unique_name(filename, used_msg_names)
                            
                            content = exporter.build_single_message_markdown(msg)
                            
                            file_path = str(topic_dir / f"{filename}.md")
                            created_at = msg.get("createdAt")
                            modified_at = msg.get("updatedAt") or created_at
                            write_file_with_timestamp(file_path, content, created_at, modified_at)
                            file_count += 1
            
            self.app.log_message(f"✅ 批量按消息分割导出: {file_count}个Markdown文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{export_dir}")
            
        except Exception as e:
            self.app.log_message(f"批量分割导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
