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
from ..utils.file_utils import safe_filename


class ContextMenuManager:
    """右键菜单管理器"""
    
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
    
    def create_context_menus(self):
        """创建右键菜单"""
        # 消息右键菜单
        self.message_menu = tk.Menu(self.master, tearoff=0)
        self.message_menu.add_command(label="📄 导出为JSON", command=lambda: self.export_item_json("message"))
        self.message_menu.add_command(label="📝 导出为Markdown", command=lambda: self.export_item_md("message"))
        self.message_menu.add_separator()
        self.message_menu.add_command(label="📋 复制JSON到剪贴板", command=lambda: self.copy_item_json("message"))
        self.message_menu.add_command(label="📋 复制Markdown到剪贴板", command=lambda: self.copy_item_md("message"))
        self.message_menu.add_command(label="📋 复制消息内容", command=self.copy_message_content)
        
        # 主题右键菜单
        self.topic_menu = tk.Menu(self.master, tearoff=0)
        self.topic_menu.add_command(label="📄 导出为JSON", command=lambda: self.export_item_json("topic"))
        self.topic_menu.add_command(label="📝 导出为Markdown", command=lambda: self.export_item_md("topic"))
        self.topic_menu.add_separator()
        self.topic_menu.add_command(label="📋 复制JSON到剪贴板", command=lambda: self.copy_item_json("topic"))
        self.topic_menu.add_command(label="📋 复制Markdown到剪贴板", command=lambda: self.copy_item_md("topic"))
        
        # 会话右键菜单
        self.session_menu = tk.Menu(self.master, tearoff=0)
        self.session_menu.add_command(label="📄 导出为JSON", command=lambda: self.export_item_json("session"))
        self.session_menu.add_command(label="📁 导出按主题分割的JSON", command=self.export_session_split_json)
        self.session_menu.add_command(label="📝 导出为Markdown", command=lambda: self.export_item_md("session"))
        self.session_menu.add_command(label="📁 导出按主题分割的Markdown", command=self.export_session_split_md)
        self.session_menu.add_separator()
        self.session_menu.add_command(label="📋 复制JSON到剪贴板", command=lambda: self.copy_item_json("session"))
        self.session_menu.add_command(label="📋 复制Markdown到剪贴板", command=lambda: self.copy_item_md("session"))
        
        # 助手右键菜单
        self.agent_menu = tk.Menu(self.master, tearoff=0)
        self.agent_menu.add_command(label="📄 导出为JSON", command=lambda: self.export_item_json("agent"))
        self.agent_menu.add_command(label="📁 导出按会话分割的JSON", command=self.export_agent_split_json)
        self.agent_menu.add_command(label="📝 导出为Markdown", command=lambda: self.export_item_md("agent"))
        self.agent_menu.add_command(label="📁 导出按会话分割的Markdown", command=self.export_agent_split_md)
        self.agent_menu.add_separator()
        self.agent_menu.add_command(label="💬 导出助手提示词(Markdown)", command=self.export_agent_prompt_md)
        self.agent_menu.add_command(label="💬 复制助手提示词到剪贴板", command=self.copy_agent_prompt)
        self.agent_menu.add_separator()
        self.agent_menu.add_command(label="📋 复制JSON到剪贴板", command=lambda: self.copy_item_json("agent"))
        self.agent_menu.add_command(label="📋 复制Markdown到剪贴板", command=lambda: self.copy_item_md("agent"))
        
        # 批量操作菜单
        self.batch_menu = tk.Menu(self.master, tearoff=0)
        self.batch_menu.add_command(label="📦 批量导出为JSON", command=self.batch_export_json)
        self.batch_menu.add_command(label="📦 批量导出为Markdown", command=self.batch_export_md)
        self.batch_menu.add_separator()
        self.batch_menu.add_command(label="📋 批量复制JSON到剪贴板", command=self.batch_copy_json)
        self.batch_menu.add_command(label="📋 批量复制Markdown到剪贴板", command=self.batch_copy_md)
        self.batch_menu.add_separator()
        self.batch_menu.add_command(label="ℹ️ 查看选中统计", command=self.show_batch_stats)
    
    def show_context_menu(self, event):
        """显示右键菜单"""
        if not self.app.parsed_data:
            return
        
        # 获取点击的项目
        item = self.app.data_tree.identify_row(event.y)
        if not item:
            return
        
        # 如果点击的项目不在选中列表中，则只选中该项
        current_selection = self.app.data_tree.selection()
        if item not in current_selection:
            self.app.data_tree.selection_set(item)
            current_selection = (item,)
        
        # 检查是否多选
        if len(current_selection) > 1:
            try:
                self.batch_menu.post(event.x_root, event.y_root)
            finally:
                self.batch_menu.grab_release()
            return
        
        # 单选情况，显示对应类型的菜单
        values = self.app.data_tree.item(item, "values")
        if not values:
            return
        
        item_type = values[0]
        
        # 显示对应的菜单
        try:
            if item_type == "消息":
                self.message_menu.post(event.x_root, event.y_root)
            elif item_type == "主题":
                self.topic_menu.post(event.x_root, event.y_root)
            elif item_type == "会话":
                self.session_menu.post(event.x_root, event.y_root)
            elif item_type == "助手":
                self.agent_menu.post(event.x_root, event.y_root)
        finally:
            self.message_menu.grab_release()
            self.topic_menu.grab_release()
            self.session_menu.grab_release()
            self.agent_menu.grab_release()
            self.batch_menu.grab_release()
    
    def export_topic_md(self):
        """导出主题为Markdown"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        topic_id = values[2]
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
        topic_id = values[2]
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
        topic_id = values[2]
        
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
        agent_id = values[2]
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
        agent_id = values[2]
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
                
                from ..utils.file_utils import ensure_unique_name
                
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
                        
                        (agent_dir / f"{filename}.md").write_text(content, encoding='utf-8')
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
        agent_id = values[2]
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
        agent_id = values[2]
        
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
        item_id = values[2]
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
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.app.log_message(f"✅ {item_type}已导出为JSON", "SUCCESS")
    
    def export_item_md(self, item_type: str):
        """通用Markdown导出"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        item_id = values[2]
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
            Path(file_path).write_text(md_content, encoding='utf-8')
            self.app.log_message(f"✅ {item_type}已导出为Markdown", "SUCCESS")
    
    def copy_item_json(self, item_type: str):
        """通用JSON复制"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        item_id = values[2]
        
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
        msg_id = values[2]
        
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
        item_id = values[2]
        
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
    
    def export_session_split_json(self):
        """会话分割JSON导出"""
        messagebox.showinfo("提示", "该功能待实现：导出会话按主题分割的JSON文件")
    
    def export_session_split_md(self):
        """会话分割Markdown导出"""
        messagebox.showinfo("提示", "该功能待实现：导出会话按主题分割的Markdown文件")
    
    def export_agent_split_json(self):
        """助手分割JSON导出"""
        messagebox.showinfo("提示", "该功能待实现：导出助手按会话分割的JSON文件")
    
    def export_agent_split_md(self):
        """助手分割Markdown导出"""
        self.export_agent_separated_md()  # 复用已有功能
    
    def export_agent_prompt_md(self):
        """导出助手提示词Markdown"""
        selection = self.app.data_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        values = self.app.data_tree.item(item, "values")
        agent_id = values[2]
        
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
                    Path(file_path).write_text(content, encoding='utf-8')
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
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, indent=2, ensure_ascii=False)
            
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
                    item_id = values[2]
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
            item_id = values[2]
            
            if item_type == "主题":
                # 添加主题和消息
                topic = self.app.parsed_data["topics"].get(item_id)
                if topic and item_id not in topics_set:
                    all_topics.append(topic)
                    topics_set.add(item_id)
                
                messages = self.app.parsed_data["messagesByTopic"].get(item_id, [])
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
                # 添加单条消息
                for topic_id, messages in self.app.parsed_data["messagesByTopic"].items():
                    for msg in messages:
                        if msg.get("id") == item_id:
                            if item_id not in messages_set:
                                all_messages.append(msg)
                                messages_set.add(item_id)
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
