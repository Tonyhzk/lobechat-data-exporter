"""
LobeChat 数据导出工具主窗口
整合所有功能模块
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import json
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from ..config import *
from ..core.parser import LobeChatParser
from ..core.db_connector import DBConfig, PostgreSQLConnector
from ..core.db_parser import DatabaseParser
from ..exporters.markdown_exporter import MarkdownExporter
from ..exporters.json_exporter import JSONExporter
from ..utils.clipboard import ClipboardManager
from ..utils.file_utils import (
    safe_filename, ensure_unique_name, format_datetime, get_app_path,
    write_file_with_timestamp, get_time_range_from_messages
)
from .components import create_toolbar, create_file_selector, create_stats_area, create_export_options, create_log_area
from .tree_view import TreeViewController
from .context_menu import ContextMenuManager
from .data_tabs import DataTabsController


class LobeChatDataExporter:
    """LobeChat 数据导出工具主应用"""
    
    def __init__(self, master):
        self.master = master
        self.master.title(WINDOW_TITLE)
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.master.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        
        # 数据存储
        self.parsed_data = None
        self.json_file_path = None
        self.current_theme = DEFAULT_THEME
        self.is_macos = platform.system() == 'Darwin'
        
        # 加载配置
        self.config = self.load_config()
        self.current_theme = self.config.get("theme", DEFAULT_THEME)
        
        # 设置主题
        self.style = ttk_boot.Style(self.current_theme)
        
        # 初始化组件管理器
        self.clipboard_manager = None
        self.tree_controller = None
        self.context_menu_manager = None
        
        # 创建UI
        self.create_ui()
        
        # 初始化拖拽（如果支持）
        self.setup_drag_drop()
        
        # 居中显示
        self.center_window()
        
        # 日志
        self.log_message("LobeChat 数据导出工具已启动", "INFO")
        if ENABLE_DEBUG:
            self.log_message(f"DEBUG模式已启用，当前主题: {self.current_theme}", "DEBUG")
    
    def setup_drag_drop(self):
        """设置拖拽功能"""
        try:
            from ..utils.drag_drop import setup_drag_drop
            setup_drag_drop(self.master, self.file_entry, self.handle_file_drop)
            if ENABLE_DEBUG:
                self.log_message("DEBUG: 拖拽功能已启用", "DEBUG")
        except Exception as e:
            self.log_message(f"拖拽功能不可用: {e}", "WARNING")
    
    def handle_file_drop(self, file_path: str):
        """处理文件拖拽"""
        if file_path and file_path.lower().endswith('.json'):
            self.file_path_var.set(file_path)
            self.log_message(f"已拖入文件: {os.path.basename(file_path)}", "INFO")
            self.master.after(100, self.parse_json_file)
        else:
            self.log_message("请拖入JSON文件", "WARNING")
    
    def create_ui(self):
        """创建用户界面"""
        # 初始化剪贴板管理器（必须在创建右键菜单之前）
        self.clipboard_manager = ClipboardManager(self.master)
        
        # 顶部工具栏
        create_toolbar(self.master, self)
        
        # 主容器
        main_container = ttk.Frame(self.master, padding=10)
        main_container.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)
        
        # 1. 文件选择区域
        self.file_path_var, self.file_entry = create_file_selector(main_container, self)
        
        # 2. 统计信息区域
        self.stat_labels = create_stats_area(main_container)
        
        # 3. 主内容区域（树形视图和导出选项）
        self.create_main_content(main_container)
        
        # 4. 日志显示区域
        self.log_text = create_log_area(main_container, self.current_theme)
    
    def create_main_content(self, parent):
        """创建主内容区域 - 仅包含数据选项卡控制器"""
        # 数据选项卡控制器（新版）
        data_frame = ttk.LabelFrame(parent, text="📂 数据结构", padding=10)
        data_frame.grid(row=2, column=0, sticky=(N, S, E, W), pady=(0, 10))
        
        # 创建数据选项卡控制器
        self.data_tabs_controller = DataTabsController(data_frame, self)
        
        # 创建右键菜单管理器（必须先创建，以便绑定事件）
        self.context_menu_manager = ContextMenuManager(self.master, self)
        
        # 获取综合视图的树形控制器（用于右键菜单）
        if "overview" in self.data_tabs_controller.tabs:
            self.tree_controller = self.data_tabs_controller.tabs["overview"]["controller"]
            self.data_tree = self.tree_controller.tree
            
            # 绑定右键菜单事件
            self._bind_context_menu(self.data_tree)
        else:
            self.tree_controller = None
            self.data_tree = None
            self.log_message("警告：未找到综合视图选项卡", "WARNING")
        
        # 从数据选项卡控制器获取导出选项变量
        if hasattr(self.data_tabs_controller, 'md_export_mode'):
            self.md_export_mode = self.data_tabs_controller.md_export_mode
        else:
            self.md_export_mode = tk.StringVar(value="directory")
        
        if hasattr(self.data_tabs_controller, 'md_include_metadata'):
            self.md_include_metadata = self.data_tabs_controller.md_include_metadata
        else:
            self.md_include_metadata = tk.BooleanVar(value=True)
        
        if hasattr(self.data_tabs_controller, 'md_include_system_prompt'):
            self.md_include_system_prompt = self.data_tabs_controller.md_include_system_prompt
        else:
            self.md_include_system_prompt = tk.BooleanVar(value=True)
        
        self.json_export_vars = {}
    
    def browse_file(self):
        """浏览选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择LobeChat备份文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.log_message(f"已选择文件: {file_path}", "INFO")
            # 自动触发解析
            self.master.after(100, self.parse_json_file)
    
    def parse_json_file(self):
        """解析JSON文件"""
        file_path = self.file_path_var.get().strip()
        
        if not file_path:
            messagebox.showwarning("警告", "请先选择JSON文件！")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("错误", "文件不存在！")
            return
        
        self.log_message(f"开始解析文件: {os.path.basename(file_path)}", "INFO")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # 使用解析器
            parser = LobeChatParser(log_callback=self.log_message)
            self.parsed_data = parser.parse(raw_data, file_path)
            self.json_file_path = file_path
            
            # 更新UI
            self.update_stats()
            
            # 更新数据选项卡控制器（新版）
            if hasattr(self, 'data_tabs_controller'):
                self.data_tabs_controller.update_data(self.parsed_data)
            # 兼容旧版：如果没有选项卡控制器，则直接更新树形视图
            elif hasattr(self, 'tree_controller'):
                self.tree_controller.update_tree(self.parsed_data)
            
            self.log_message("✅ 数据解析成功！", "SUCCESS")
            
        except json.JSONDecodeError as e:
            self.log_message(f"JSON解析失败: {str(e)}", "ERROR")
            messagebox.showerror("解析失败", f"JSON格式错误：\n{str(e)}")
        except Exception as e:
            self.log_message(f"解析失败: {str(e)}", "ERROR")
            messagebox.showerror("解析失败", str(e))
    
    def update_stats(self):
        """更新统计信息"""
        if not self.parsed_data:
            return
        
        stats = self.parsed_data["stats"]
        for key, label in self.stat_labels.items():
            label.config(text=str(stats.get(key, 0)))
    
    def export_markdown(self):
        """导出Markdown"""
        if not self.parsed_data:
            messagebox.showwarning("警告", "请先解析JSON文件！")
            return
        
        mode = self.md_export_mode.get()
        
        if mode == "single_file":
            # 全部内容为一个文件
            self.export_markdown_single_file()
        elif mode == "agent_file":
            # 每个助手一个文件
            self.export_markdown_agent_files()
        elif mode == "topic_file":
            # 每个主题一个文件：助手/主题.md
            self.export_markdown_directory()
        elif mode == "message_file":
            # 每个对话一个文件：助手/主题/对话.md
            self.export_markdown_message_files()
        # 保持旧模式兼容
        elif mode == "directory":
            self.export_markdown_directory()
        elif mode == "single_topic":
            messagebox.showinfo("提示", "请在左侧树形视图中右键点击主题节点进行导出")
        elif mode == "agent_merge":
            messagebox.showinfo("提示", "请在左侧树形视图中右键点击助手节点进行整合导出")
        elif mode == "agent_separate":
            messagebox.showinfo("提示", "请在左侧树形视图中右键点击助手节点进行分离导出")
    
    def export_markdown_single_file(self):
        """导出所有对话为单个Markdown文件"""
        file_path = filedialog.asksaveasfilename(
            title="保存Markdown文件",
            defaultextension=".md",
            filetypes=[("Markdown文件", "*.md"), ("所有文件", "*.*")],
            initialfile=f"{self.parsed_data['sourceFileName'].replace('.json', '')}_all.md"
        )
        
        if not file_path:
            return
        
        self.log_message("开始导出Markdown（全部为一个文件）...", "INFO")
        
        try:
            exporter = MarkdownExporter(self.parsed_data)
            include_metadata = self.md_include_metadata.get()
            include_system_prompt = self.md_include_system_prompt.get()
            
            lines = [
                "# LobeChat 全部对话",
                "",
                f"- **源文件**: `{self.parsed_data['sourceFileName']}`",
                f"- **助手数**: {self.parsed_data['stats']['agentCount']}",
                f"- **主题数**: {self.parsed_data['stats']['topicCount']}",
                f"- **消息数**: {self.parsed_data['stats']['messageCount']}",
                "",
                "---",
                ""
            ]
            
            for group in self.parsed_data["groups"]:
                # 助手标题
                lines.append(f"# 助手: {group['agentLabel']}")
                lines.append("")
                
                # 助手系统提示词
                if include_system_prompt:
                    agent = group.get("agent")
                    if agent:
                        system_role = agent.get("systemRole", "")
                        if system_role:
                            lines.append("## 系统提示词")
                            lines.append("")
                            lines.append("```")
                            lines.append(system_role)
                            lines.append("```")
                            lines.append("")
                
                # 遍历主题
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        lines.append(f"## 主题: {topic_group['topicLabel']}")
                        lines.append("")
                        
                        messages = topic_group.get("messages", [])
                        for msg in messages:
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            
                            role_label = "👤 用户" if role == "user" else "🤖 助手" if role == "assistant" else f"⚙️ {role}"
                            
                            lines.append(f"### {role_label}")
                            
                            if include_metadata:
                                created_at = msg.get("createdAt")
                                model = msg.get("model", "")
                                if created_at or model:
                                    meta_parts = []
                                    if created_at:
                                        meta_parts.append(f"时间: {format_datetime(created_at)}")
                                    if model:
                                        meta_parts.append(f"模型: {model}")
                                    lines.append(f"*{' | '.join(meta_parts)}*")
                            
                            lines.append("")
                            lines.append(content if content else "(空)")
                            lines.append("")
                        
                        lines.append("---")
                        lines.append("")
                
                lines.append("")
            
            # 写入文件
            content = "\n".join(lines)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.log_message(f"✅ 导出完成！文件: {file_path}", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出到:\n{file_path}")
            
        except Exception as e:
            self.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def export_markdown_agent_files(self):
        """导出每个助手为单独的Markdown文件"""
        output_dir = filedialog.askdirectory(title="选择导出目录")
        if not output_dir:
            return
        
        self.log_message("开始导出Markdown（每个助手一个文件）...", "INFO")
        
        try:
            export_path = Path(output_dir) / f"{self.parsed_data['sourceFileName'].replace('.json', '')}_agents"
            export_path.mkdir(exist_ok=True)
            
            exporter = MarkdownExporter(self.parsed_data)
            include_metadata = self.md_include_metadata.get()
            include_system_prompt = self.md_include_system_prompt.get()
            
            file_count = 0
            index_lines = [
                "# LobeChat 助手列表",
                "",
                f"- **源文件**: `{self.parsed_data['sourceFileName']}`",
                ""
            ]
            
            used_names = set()
            for group in self.parsed_data["groups"]:
                # 文件名
                filename = safe_filename(group["agentLabel"], group["agentId"])
                filename = ensure_unique_name(filename, used_names)
                
                lines = [
                    f"# {group['agentLabel']}",
                    "",
                ]
                
                # 助手系统提示词
                if include_system_prompt:
                    agent = group.get("agent")
                    if agent:
                        system_role = agent.get("systemRole", "")
                        if system_role:
                            lines.append("## 系统提示词")
                            lines.append("")
                            lines.append("```")
                            lines.append(system_role)
                            lines.append("```")
                            lines.append("")
                
                # 统计信息
                topic_count = sum(len(s["topics"]) for s in group["sessions"])
                message_count = sum(sum(len(t["messages"]) for t in s["topics"]) for s in group["sessions"])
                
                lines.append(f"- **主题数**: {topic_count}")
                lines.append(f"- **消息数**: {message_count}")
                lines.append("")
                lines.append("---")
                lines.append("")
                
                # 遍历主题
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        lines.append(f"## {topic_group['topicLabel']}")
                        lines.append("")
                        
                        messages = topic_group.get("messages", [])
                        for msg in messages:
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            
                            role_label = "👤 用户" if role == "user" else "🤖 助手" if role == "assistant" else f"⚙️ {role}"
                            
                            lines.append(f"### {role_label}")
                            
                            if include_metadata:
                                created_at = msg.get("createdAt")
                                model = msg.get("model", "")
                                if created_at or model:
                                    meta_parts = []
                                    if created_at:
                                        meta_parts.append(f"时间: {format_datetime(created_at)}")
                                    if model:
                                        meta_parts.append(f"模型: {model}")
                                    lines.append(f"*{' | '.join(meta_parts)}*")
                            
                            lines.append("")
                            lines.append(content if content else "(空)")
                            lines.append("")
                        
                        lines.append("---")
                        lines.append("")
                
                # 写入文件
                file_path = export_path / f"{filename}.md"
                content = "\n".join(lines)
                
                # 获取时间信息
                agent_all_messages = []
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        agent_all_messages.extend(topic_group.get("messages", []))
                
                agent_created_at, agent_modified_at = get_time_range_from_messages(agent_all_messages)
                agent = group.get("agent")
                if agent and agent.get("createdAt"):
                    agent_created_at = agent.get("createdAt")
                
                write_file_with_timestamp(str(file_path), content, agent_created_at, agent_modified_at)
                file_count += 1
                
                # 索引
                index_lines.append(f"- [{group['agentLabel']}]({filename}.md) - {topic_count}主题, {message_count}消息")
            
            # 写入索引
            (export_path / "index.md").write_text("\n".join(index_lines), encoding='utf-8')
            file_count += 1
            
            self.log_message(f"✅ 导出完成！共{file_count}个文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{export_path}")
            
        except Exception as e:
            self.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def export_markdown_directory(self):
        """按目录结构导出Markdown"""
        output_dir = filedialog.askdirectory(title="选择导出目录")
        if not output_dir:
            return
        
        self.log_message("开始按目录结构导出Markdown...", "INFO")
        
        try:
            export_path = Path(output_dir) / f"{self.parsed_data['sourceFileName'].replace('.json', '')}_markdown"
            export_path.mkdir(exist_ok=True)
            
            exporter = MarkdownExporter(self.parsed_data)
            include_metadata = self.md_include_metadata.get()
            include_system_prompt = self.md_include_system_prompt.get()
            
            file_count = 0
            index_lines = [
                "# LobeChat 对话索引",
                "",
                f"- **源文件**: `{self.parsed_data['sourceFileName']}`",
                ""
            ]
            
            for group in self.parsed_data["groups"]:
                # 创建助手目录
                agent_dir_name = safe_filename(group["agentLabel"], group["agentId"])
                agent_dir = export_path / agent_dir_name
                agent_dir.mkdir(exist_ok=True)
                
                # README - 使用助手的时间信息
                readme_content = exporter.build_agent_readme(group, include_metadata, include_system_prompt)
                readme_path = str(agent_dir / "README.md")
                
                # 收集助手所有消息以获取时间范围
                agent_all_messages = []
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        agent_all_messages.extend(topic_group.get("messages", []))
                
                agent_created_at, agent_modified_at = get_time_range_from_messages(agent_all_messages)
                agent = group.get("agent")
                if agent and agent.get("createdAt"):
                    agent_created_at = agent.get("createdAt")
                
                write_file_with_timestamp(readme_path, readme_content, agent_created_at, agent_modified_at)
                file_count += 1
                
                # 索引
                session_count = len(group["sessions"])
                topic_count = sum(len(s["topics"]) for s in group["sessions"])
                message_count = sum(sum(len(t["messages"]) for t in s["topics"]) for s in group["sessions"])
                
                index_lines.append(
                    f"- [{group['agentLabel']}]({agent_dir_name}/README.md) - "
                    f"{session_count}会话, {topic_count}主题, {message_count}消息"
                )
                
                # 导出主题
                used_names = set()
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        filename = safe_filename(topic_group["topicLabel"], topic_group["topicId"])
                        filename = ensure_unique_name(filename, used_names)
                        
                        content = exporter.build_topic_markdown(
                            group.get("agent"), session_group["session"], topic_group,
                            group["agentLabel"], include_metadata, include_system_prompt
                        )
                        
                        file_path = str(agent_dir / f"{filename}.md")
                        
                        # 获取主题的时间信息
                        topic = topic_group.get("topic")
                        messages = topic_group.get("messages", [])
                        created_at = topic.get("createdAt") if topic else None
                        _, latest_modified = get_time_range_from_messages(messages)
                        modified_at = latest_modified or (topic.get("updatedAt") if topic else None) or created_at
                        
                        write_file_with_timestamp(file_path, content, created_at, modified_at)
                        file_count += 1
            
            # 写入索引
            (export_path / "index.md").write_text("\n".join(index_lines), encoding='utf-8')
            file_count += 1
            
            self.log_message(f"✅ 导出完成！共{file_count}个文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{export_path}")
            
        except Exception as e:
            self.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def export_markdown_message_files(self):
        """按对话导出Markdown - 每个对话一个文件（三级目录结构：助手/主题/对话.md）"""
        output_dir = filedialog.askdirectory(title="选择导出目录")
        if not output_dir:
            return
        
        self.log_message("开始导出Markdown（每个对话一个文件）...", "INFO")
        
        try:
            export_path = Path(output_dir) / f"{self.parsed_data['sourceFileName'].replace('.json', '')}_messages"
            export_path.mkdir(exist_ok=True)
            
            exporter = MarkdownExporter(self.parsed_data)
            include_metadata = self.md_include_metadata.get()
            include_system_prompt = self.md_include_system_prompt.get()
            
            file_count = 0
            index_lines = [
                "# LobeChat 对话索引",
                "",
                f"- **源文件**: `{self.parsed_data['sourceFileName']}`",
                f"- **导出模式**: 每个对话一个文件",
                ""
            ]
            
            for group in self.parsed_data["groups"]:
                # 创建助手目录
                agent_dir_name = safe_filename(group["agentLabel"], group["agentId"])
                agent_dir = export_path / agent_dir_name
                agent_dir.mkdir(exist_ok=True)
                
                # 助手 README
                readme_content = exporter.build_agent_readme(group, include_metadata, include_system_prompt)
                readme_path = str(agent_dir / "README.md")
                
                agent_all_messages = []
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        agent_all_messages.extend(topic_group.get("messages", []))
                
                agent_created_at, agent_modified_at = get_time_range_from_messages(agent_all_messages)
                agent = group.get("agent")
                if agent and agent.get("createdAt"):
                    agent_created_at = agent.get("createdAt")
                
                write_file_with_timestamp(readme_path, readme_content, agent_created_at, agent_modified_at)
                file_count += 1
                
                # 索引
                session_count = len(group["sessions"])
                topic_count = sum(len(s["topics"]) for s in group["sessions"])
                message_count = sum(sum(len(t["messages"]) for t in s["topics"]) for s in group["sessions"])
                
                index_lines.append(
                    f"- [{group['agentLabel']}]({agent_dir_name}/README.md) - "
                    f"{session_count}会话, {topic_count}主题, {message_count}消息"
                )
                
                # 遍历主题
                used_topic_names = set()
                for session_group in group["sessions"]:
                    for topic_group in session_group["topics"]:
                        # 创建主题目录
                        topic_dir_name = safe_filename(topic_group["topicLabel"], topic_group["topicId"])
                        topic_dir_name = ensure_unique_name(topic_dir_name, used_topic_names)
                        topic_dir = agent_dir / topic_dir_name
                        topic_dir.mkdir(exist_ok=True)
                        
                        # 主题 README
                        topic = topic_group.get("topic")
                        messages = topic_group.get("messages", [])
                        
                        topic_readme_lines = [
                            f"# {topic_group['topicLabel']}",
                            "",
                            f"- **消息数**: {len(messages)}",
                        ]
                        if topic and topic.get("createdAt"):
                            topic_readme_lines.append(f"- **创建时间**: {format_datetime(topic.get('createdAt'))}")
                        
                        topic_readme_lines.append("")
                        topic_readme_lines.append("## 对话列表")
                        topic_readme_lines.append("")
                        
                        # 导出每条消息为单独文件
                        for i, msg in enumerate(messages):
                            role = msg.get("role", "unknown")
                            content = msg.get("content", "")
                            created_at = msg.get("createdAt")
                            model = msg.get("model", "")
                            
                            # 生成文件名：序号_角色_时间
                            time_str = format_datetime(created_at).replace(":", "-").replace(" ", "_") if created_at else ""
                            msg_filename = f"{i+1:04d}_{role}_{time_str}"
                            msg_filename = safe_filename(msg_filename, msg.get("id", ""))
                            
                            # 构建消息内容
                            msg_lines = [
                                f"# 消息 #{i+1}",
                                "",
                                f"- **角色**: {role}",
                                f"- **时间**: {format_datetime(created_at) if created_at else '-'}",
                            ]
                            if model:
                                msg_lines.append(f"- **模型**: {model}")
                            
                            if include_metadata:
                                metadata = msg.get("metadata") or {}
                                tokens = metadata.get("totalTokens", 0)
                                if tokens:
                                    msg_lines.append(f"- **Token**: {tokens}")
                            
                            msg_lines.append("")
                            msg_lines.append("## 内容")
                            msg_lines.append("")
                            msg_lines.append(content if content else "(空)")
                            
                            # 写入文件
                            msg_file_path = str(topic_dir / f"{msg_filename}.md")
                            msg_content = "\n".join(msg_lines)
                            write_file_with_timestamp(msg_file_path, msg_content, created_at, created_at)
                            file_count += 1
                            
                            # 添加到主题README索引
                            role_emoji = "👤" if role == "user" else "🤖" if role == "assistant" else "⚙️"
                            preview = content[:50].replace("\n", " ") + "..." if len(content) > 50 else content.replace("\n", " ")
                            topic_readme_lines.append(f"- {role_emoji} [{msg_filename}]({msg_filename}.md) - {preview}")
                        
                        # 写入主题README
                        topic_readme_path = str(topic_dir / "README.md")
                        topic_readme_content = "\n".join(topic_readme_lines)
                        topic_created = topic.get("createdAt") if topic else None
                        _, topic_modified = get_time_range_from_messages(messages)
                        write_file_with_timestamp(topic_readme_path, topic_readme_content, topic_created, topic_modified)
                        file_count += 1
            
            # 写入总索引
            (export_path / "index.md").write_text("\n".join(index_lines), encoding='utf-8')
            file_count += 1
            
            self.log_message(f"✅ 导出完成！共{file_count}个文件", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出{file_count}个Markdown文件到:\n{export_path}")
            
        except Exception as e:
            self.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def export_custom_json(self):
        """导出自定义JSON"""
        if not self.parsed_data:
            messagebox.showwarning("警告", "请先解析JSON文件！")
            return
        
        selected_modules = [key for key, var in self.json_export_vars.items() if var.get()]
        
        if not selected_modules:
            messagebox.showwarning("警告", "请至少选择一个模块！")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="保存JSON文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile=f"{self.parsed_data['sourceFileName'].replace('.json', '')}_custom.json"
        )
        
        if not file_path:
            return
        
        self.log_message(f"开始导出自定义JSON，包含模块: {', '.join(selected_modules)}", "INFO")
        
        try:
            exporter = JSONExporter(self.parsed_data)
            export_data = exporter.build_custom_json(selected_modules)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"✅ 自定义JSON导出成功: {file_path}", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出包含 {len(selected_modules)} 个模块的JSON文件")
            
        except Exception as e:
            self.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def toggle_all_json_modules(self, select_all: bool):
        """切换所有JSON模块选择"""
        for var in self.json_export_vars.values():
            var.set(select_all)
        self.log_message(f"已{'全选' if select_all else '取消全选'}所有模块", "INFO")
    
    def select_config_only(self):
        """仅选择配置相关模块"""
        config_modules = {"userSettings", "aiProviders", "aiModels", "agents"}
        for module_key, var in self.json_export_vars.items():
            var.set(module_key in config_modules)
        self.log_message("已选择配置相关模块", "INFO")
    
    def toggle_theme(self):
        """切换主题"""
        new_theme = THEME_LIGHT if self.current_theme == THEME_DARK else THEME_DARK
        self.current_theme = new_theme
        self.style.theme_use(new_theme)
        
        # 更新数据选项卡控制器（新版）
        if hasattr(self, 'data_tabs_controller'):
            self.data_tabs_controller.configure_theme(new_theme)
        # 兼容旧版
        elif hasattr(self, 'tree_controller'):
            self.tree_controller.configure_style(new_theme)
        
        # 更新日志区域
        if hasattr(self, 'log_text'):
            if new_theme == THEME_DARK:
                self.log_text.config(bg="#1e1e1e", fg="#e0e0e0")
            else:
                self.log_text.config(bg="#ffffff", fg="#000000")
        
        self.config["theme"] = new_theme
        self.save_config()
        self.log_message(f"主题已切换为: {new_theme}", "INFO")
    
    def reload_data(self):
        """重新加载数据"""
        if self.json_file_path and os.path.exists(self.json_file_path):
            self.file_path_var.set(self.json_file_path)
            self.parse_json_file()
        else:
            messagebox.showinfo("提示", "请先选择并解析JSON文件！")
    
    # ==================== 数据库功能 ====================
    
    def _update_db_stats(self, connector: PostgreSQLConnector, user_id: Optional[str] = None):
        """
        更新数据库统计信息（仅执行COUNT查询，不加载详细数据）
        
        Args:
            connector: 数据库连接器
            user_id: 用户ID（可选）
        """
        try:
            # 统计助手数量
            agent_query = "SELECT COUNT(*) as count FROM agents"
            if user_id:
                agent_query += f" WHERE user_id = '{user_id}'"
            agent_result = connector.execute_query(agent_query)
            agent_count = agent_result[0]["count"] if agent_result else 0
            
            # 统计主题数量
            topic_query = "SELECT COUNT(*) as count FROM topics"
            if user_id:
                topic_query += f" WHERE user_id = '{user_id}'"
            topic_result = connector.execute_query(topic_query)
            topic_count = topic_result[0]["count"] if topic_result else 0
            
            # 统计消息数量
            message_query = "SELECT COUNT(*) as count FROM messages"
            if user_id:
                message_query += f" WHERE user_id = '{user_id}'"
            message_result = connector.execute_query(message_query)
            message_count = message_result[0]["count"] if message_result else 0
            
            # 更新UI显示
            self.stat_labels["agentCount"].config(text=str(agent_count))
            self.stat_labels["topicCount"].config(text=str(topic_count))
            self.stat_labels["messageCount"].config(text=str(message_count))
            
            self.log_message(f"📊 统计信息: {agent_count}个助手, {topic_count}个主题, {message_count}条消息", "INFO")
            
        except Exception as e:
            self.log_message(f"获取统计信息失败: {str(e)}", "WARNING")
    
    def show_db_connection_dialog(self):
        """显示数据库连接对话框"""
        from .db_dialog import show_db_connection_dialog
        
        # 从配置中获取上次的数据库配置
        db_config = self.config.get("db_config", {})
        
        show_db_connection_dialog(
            self.master,
            callback=self._on_db_connected,
            log_callback=self.log_message,
            initial_config=db_config
        )
    
    def _on_db_connected(self, connector: PostgreSQLConnector, config: Dict):
        """
        数据库连接成功的回调 - 使用懒加载模式
        
        Args:
            connector: 数据库连接器
            config: 连接配置
        """
        self.log_message("数据库连接成功，正在初始化...", "INFO")
        
        try:
            # 保存数据库配置
            save_password = config.get("save_password", False)
            if save_password:
                # 用户选择了保存密码
                safe_config = {k: v for k, v in config.items()}
            else:
                # 不保存密码
                safe_config = {k: v for k, v in config.items() if k != "password"}
            self.config["db_config"] = safe_config
            self.save_config()
            
            # 更新文件路径显示
            self.file_path_var.set(f"🗄️ 数据库: {config['host']}:{config['port']}/{config['database']}")
            self.json_file_path = None  # 清除JSON文件路径
            
            # 获取统计信息（快速COUNT查询，不加载详细数据）
            user_id = config.get("user_id")
            self._update_db_stats(connector, user_id)
            
            # 使用新的懒加载数据库标签页
            if hasattr(self, 'data_tabs_controller') and hasattr(self.data_tabs_controller, 'set_db_connection'):
                # 传递连接器给数据库标签页控制器（不断开连接，由标签页控制器管理）
                self.data_tabs_controller.set_db_connection(connector, config)
                self.log_message("✅ 数据库连接已建立，数据将按需加载", "SUCCESS")
            else:
                # 兼容旧模式：一次性加载所有数据
                self.log_message("使用兼容模式：一次性加载数据...", "INFO")
                user_id = config.get("user_id")
                db_parser = DatabaseParser(connector, log_callback=self.log_message)
                self.parsed_data = db_parser.parse(user_id)
                
                # 更新UI
                self.update_stats()
                
                # 更新数据选项卡控制器
                if hasattr(self, 'data_tabs_controller'):
                    self.data_tabs_controller.update_data(self.parsed_data)
                elif hasattr(self, 'tree_controller'):
                    self.tree_controller.update_tree(self.parsed_data)
                
                self.log_message("✅ 数据库数据读取成功！", "SUCCESS")
                
                # 断开连接（数据已经读取完成）
                connector.disconnect()
            
        except Exception as e:
            self.log_message(f"❌ 数据库连接失败: {str(e)}", "ERROR")
            messagebox.showerror("连接失败", f"数据库操作失败：\n{str(e)}")
            
            # 确保断开连接
            try:
                connector.disconnect()
            except:
                pass
    
    def show_about(self):
        """显示关于对话框"""
        from ..config import VERSION, APP_NAME, AUTHOR, GITHUB_URL
        about_text = f"""{APP_NAME} v{VERSION}

作者：{AUTHOR}
GitHub：{GITHUB_URL}

最新特性 (v4.0)：
• 🗄️ 数据库直连：支持PostgreSQL直接连接
• 🔄 懒加载机制：按需加载，性能大幅提升
• 📁 分割导出：支持助手/主题/消息三级分割
• 🎯 精准时间戳：导出时间与数据库完全匹配
• 📋 完整数据：从数据库读取完整内容不截断
• 💾 批量加载：支持大数据量分批加载
• 🔃 重载功能：支持刷新选中项数据

核心功能：
• 解析LobeChat导出的JSON数据
• 多种表格视图与树形结构查看
• 全局搜索与定位功能
• 多种Markdown导出模式
• JSON模块自由选择导出
• 表格导出CSV/Excel
• 暗黑/明亮主题切换

开发：基于Python + ttkbootstrap
适用：LobeChat数据迁移与归档
"""
        messagebox.showinfo("关于", about_text)
    
    def center_window(self):
        """窗口居中显示"""
        self.master.update_idletasks()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.master.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def log_message(self, message: str, level: str = "INFO"):
        """记录日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        
        print(log_line.strip())
        
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, log_line, level)
            self.log_text.see(tk.END)
    
    def clear_log(self):
        """清空日志"""
        if hasattr(self, 'log_text'):
            self.log_text.delete(1.0, tk.END)
            self.log_message("日志已清空", "INFO")
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            config_path = get_app_path() / CONFIG_FILE_NAME
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            if ENABLE_DEBUG:
                print(f"DEBUG: 加载配置失败: {e}")
        return {"theme": DEFAULT_THEME}
    
    def save_config(self):
        """保存配置文件"""
        if not ENABLE_AUTO_SAVE:
            return
        try:
            config_path = get_app_path() / CONFIG_FILE_NAME
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            if ENABLE_DEBUG:
                print(f"DEBUG: 保存配置失败: {e}")
    
    def _bind_context_menu(self, tree_widget):
        """
        绑定右键菜单事件到树形视图
        
        Args:
            tree_widget: Treeview控件
        """
        if not tree_widget or not self.context_menu_manager:
            return
        
        # Windows/Linux 右键
        tree_widget.bind("<Button-3>", self.context_menu_manager.show_context_menu)
        
        # macOS 右键（某些配置下）
        tree_widget.bind("<Button-2>", self.context_menu_manager.show_context_menu)
        
        # macOS Control+左键（部分Mac用户习惯）
        if self.is_macos:
            tree_widget.bind("<Control-Button-1>", self.context_menu_manager.show_context_menu)
        
        if ENABLE_DEBUG:
            self.log_message("DEBUG: 右键菜单事件已绑定", "DEBUG")
