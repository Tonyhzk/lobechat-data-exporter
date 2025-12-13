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
from ..exporters.markdown_exporter import MarkdownExporter
from ..exporters.json_exporter import JSONExporter
from ..utils.clipboard import ClipboardManager
from ..utils.file_utils import safe_filename, ensure_unique_name, format_datetime, get_app_path
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
        
        # 初始化剪贴板管理器
        self.clipboard_manager = ClipboardManager(self.master)
    
    def create_main_content(self, parent):
        """创建主内容区域"""
        paned = ttk.PanedWindow(parent, orient=HORIZONTAL)
        paned.grid(row=2, column=0, sticky=(N, S, E, W), pady=(0, 10))
        
        # 左侧：数据选项卡控制器（新版）
        left_frame = ttk.LabelFrame(paned, text="📂 数据结构", padding=10)
        paned.add(left_frame, weight=2)
        
        # 创建数据选项卡控制器
        self.data_tabs_controller = DataTabsController(left_frame, self)
        
        # 获取综合视图的树形控制器（用于右键菜单）
        if "overview" in self.data_tabs_controller.tabs:
            self.tree_controller = self.data_tabs_controller.tabs["overview"]["controller"]
            self.data_tree = self.tree_controller.tree
            
            # 创建右键菜单管理器
            self.context_menu_manager = ContextMenuManager(self.master, self)
            
            # 绑定右键菜单
            self.data_tree.bind("<Button-3>", self.context_menu_manager.show_context_menu)
            self.data_tree.bind("<Button-2>", self.context_menu_manager.show_context_menu)
        
        # 右侧：导出选项
        right_frame = ttk.LabelFrame(paned, text="📤 导出选项", padding=10)
        paned.add(right_frame, weight=1)
        
        self.md_export_mode, self.md_include_metadata, self.md_include_system_prompt, \
        self.json_export_vars = create_export_options(right_frame, self)
    
    def browse_file(self):
        """浏览选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择LobeChat备份文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.log_message(f"已选择文件: {file_path}", "INFO")
    
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
        
        if mode == "directory":
            self.export_markdown_directory()
        elif mode == "single_topic":
            messagebox.showinfo("提示", "请在左侧树形视图中右键点击主题节点进行导出")
        elif mode == "agent_merge":
            messagebox.showinfo("提示", "请在左侧树形视图中右键点击助手节点进行整合导出")
        elif mode == "agent_separate":
            messagebox.showinfo("提示", "请在左侧树形视图中右键点击助手节点进行分离导出")
    
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
                
                # README
                readme_content = exporter.build_agent_readme(group, include_metadata, include_system_prompt)
                (agent_dir / "README.md").write_text(readme_content, encoding='utf-8')
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
                        
                        (agent_dir / f"{filename}.md").write_text(content, encoding='utf-8')
                        file_count += 1
            
            # 写入索引
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
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """LobeChat 数据导出工具 v2.0

功能特性：
• 解析LobeChat导出的JSON数据
• 按目录结构导出Markdown
• 导出单个对话/整合对话
• 自定义JSON模块导出
• 右键菜单批量操作
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
