"""
数据选项卡控制器
管理所有数据模块的选项卡展示和数据导出
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .json_editor import JSONEditor
from .tree_view import TreeViewController


# LobeChat 数据模块配置
MODULES_CONFIG = [
    {"key": "overview", "label": "综合视图", "type": "tree", "required": False, "order": 0, "in_export": False},
    {"key": "userSettings", "label": "用户设置", "type": "json", "required": True, "order": 1, "in_export": True},
    {"key": "aiProviders", "label": "AI提供商", "type": "json", "required": True, "order": 2, "in_export": True},
    {"key": "aiModels", "label": "AI模型", "type": "json", "required": True, "order": 3, "in_export": True},
    {"key": "agents", "label": "助手配置", "type": "json", "required": True, "order": 4, "in_export": True},
    {"key": "sessions", "label": "会话列表", "type": "json", "required": True, "order": 5, "in_export": True},
    {"key": "sessionGroups", "label": "会话分组", "type": "json", "required": False, "order": 6, "in_export": True},
    {"key": "topics", "label": "主题列表", "type": "json", "required": True, "order": 7, "in_export": True},
    {"key": "messages", "label": "消息记录", "type": "json", "required": True, "order": 8, "in_export": True},
    {"key": "messageChunks", "label": "消息块", "type": "json", "required": False, "order": 9, "in_export": True},
    {"key": "messagePlugins", "label": "消息插件", "type": "json", "required": False, "order": 10, "in_export": True},
    {"key": "messageTranslates", "label": "消息翻译", "type": "json", "required": False, "order": 11, "in_export": True},
    {"key": "threads", "label": "对话线程", "type": "json", "required": False, "order": 12, "in_export": True},
    {"key": "agentsToSessions", "label": "助手会话关联", "type": "json", "required": True, "order": 13, "in_export": True},
    {"key": "userInstalledPlugins", "label": "用户插件", "type": "json", "required": False, "order": 14, "in_export": True},
]


class DataTabsController:
    """数据选项卡控制器"""
    
    def __init__(self, parent, app):
        """
        初始化选项卡控制器
        
        Args:
            parent: 父组件
            app: 主应用实例
        """
        self.parent = parent
        self.app = app
        self.parsed_data = None
        self.original_mode = "postgres"
        self.original_schema_hash = ""
        
        # 选项卡组件字典
        self.tabs = {}
        # 模块启用状态
        self.module_vars = {}
        # 模块配置字典
        self.modules_dict = {m["key"]: m for m in MODULES_CONFIG}
        
        self._create_ui()
    
    def _create_ui(self):
        """创建UI"""
        # 主容器
        main_container = ttk.Frame(self.parent)
        main_container.pack(fill=BOTH, expand=YES)
        
        # Notebook（选项卡容器）
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # 创建所有选项卡
        self._create_all_tabs()
        
        # 底部控制栏
        self._create_bottom_controls(main_container)
    
    def _create_all_tabs(self):
        """创建所有选项卡"""
        for module in MODULES_CONFIG:
            module_key = module["key"]
            module_label = module["label"]
            module_type = module["type"]
            is_required = module["required"]
            
            if module_type == "tree" and module_key == "overview":
                # 综合视图 - 树形结构
                self._create_overview_tab(module_key, module_label)
            else:
                # JSON编辑器
                self._create_json_tab(module_key, module_label, is_required)
    
    def _create_overview_tab(self, module_key: str, module_label: str):
        """创建综合视图选项卡（树形结构）"""
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=f"🌲 {module_label}")
        
        # 创建树形视图控制器
        tree_controller = TreeViewController(tab_frame, self.app)
        
        self.tabs[module_key] = {
            "type": "tree",
            "controller": tree_controller,
            "frame": tab_frame
        }
    
    def _create_json_tab(self, module_key: str, module_label: str, is_required: bool):
        """创建JSON编辑器选项卡"""
        tab_frame = ttk.Frame(self.notebook)
        
        # 图标选择
        icon = "⚙️" if is_required else "📦"
        self.notebook.add(tab_frame, text=f"{icon} {module_label}")
        
        # 创建JSON编辑器
        editor = JSONEditor(
            tab_frame,
            module_key,
            module_label,
            is_required,
            on_change=self._on_module_changed
        )
        editor.pack(fill=BOTH, expand=YES)
        
        self.tabs[module_key] = {
            "type": "json",
            "editor": editor,
            "frame": tab_frame
        }
    
    def _create_bottom_controls(self, parent):
        """创建底部控制栏"""
        control_frame = ttk.LabelFrame(parent, text="📤 导出控制", padding=10)
        control_frame.pack(fill=X, padx=5, pady=(0, 5))
        
        # 模块选择区域
        modules_frame = ttk.Frame(control_frame)
        modules_frame.pack(fill=BOTH, expand=YES, pady=(0, 10))
        
        # 创建多列布局的复选框
        row_frame = None
        col_count = 0
        max_cols = 3
        
        for module in sorted([m for m in MODULES_CONFIG if m["in_export"]], key=lambda x: x["order"]):
            module_key = module["key"]
            module_label = module["label"]
            is_required = module["required"]
            
            # 每3个一行
            if col_count % max_cols == 0:
                row_frame = ttk.Frame(modules_frame)
                row_frame.pack(fill=X, pady=2)
            
            # 创建启用变量
            var = tk.BooleanVar(value=is_required)
            self.module_vars[module_key] = var
            
            # 复选框
            cb = ttk.Checkbutton(
                row_frame,
                text=f"{module_label}",
                variable=var,
                bootstyle="primary-round-toggle"
            )
            cb.pack(side=LEFT, padx=10)
            
            # 必需模块禁用取消选择
            if is_required:
                cb.config(state=tk.DISABLED)
            
            col_count += 1
        
        # 按钮区域
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=X)
        
        # 快捷按钮
        ttk.Button(
            btn_frame,
            text="全选",
            command=self._select_all_modules,
            bootstyle="info-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="全不选",
            command=self._deselect_all_modules,
            bootstyle="info-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="仅必需",
            command=self._select_required_only,
            bootstyle="info-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        # 导出按钮
        ttk.Button(
            btn_frame,
            text="🚀 导出完整JSON",
            command=self.export_full_json,
            bootstyle="success",
            width=20
        ).pack(side=RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="📋 复制当前选项卡",
            command=self.copy_current_tab,
            bootstyle="info",
            width=20
        ).pack(side=RIGHT, padx=5)
    
    def update_data(self, parsed_data: Dict):
        """
        更新所有选项卡数据
        
        Args:
            parsed_data: 解析后的数据
        """
        self.parsed_data = parsed_data
        
        # 保存原始元数据
        raw_data = parsed_data.get("raw", {})
        self.original_mode = raw_data.get("mode", "postgres")
        self.original_schema_hash = raw_data.get("schemaHash", "")
        
        original_data = raw_data.get("data", {})
        
        # 更新综合视图
        if "overview" in self.tabs:
            tree_controller = self.tabs["overview"]["controller"]
            tree_controller.update_tree(parsed_data)
        
        # 更新各模块JSON编辑器
        for module_key, tab_info in self.tabs.items():
            if tab_info["type"] == "json":
                editor = tab_info["editor"]
                module_data = original_data.get(module_key, [])
                editor.set_data(module_data)
        
        self.app.log_message("✅ 所有选项卡数据已更新", "SUCCESS")
    
    def get_export_data(self) -> Dict:
        """
        获取导出数据（按选中模块和顺序）
        
        Returns:
            导出的完整JSON数据
        """
        export_data = {}
        
        # 按order顺序遍历模块
        for module in sorted([m for m in MODULES_CONFIG if m["in_export"]], key=lambda x: x["order"]):
            module_key = module["key"]
            
            # 检查是否启用
            if module_key not in self.module_vars:
                continue
            
            if not self.module_vars[module_key].get():
                continue
            
            # 获取模块数据
            try:
                module_data = self._get_module_data(module_key)
                if module_data is not None:
                    export_data[module_key] = module_data
            except Exception as e:
                self.app.log_message(f"获取 {module_key} 数据失败: {str(e)}", "ERROR")
                raise
        
        return {
            "mode": self.original_mode,
            "schemaHash": self.original_schema_hash,
            "data": export_data
        }
    
    def _get_module_data(self, module_key: str) -> Any:
        """获取单个模块的数据"""
        if module_key not in self.tabs:
            return None
        
        tab_info = self.tabs[module_key]
        
        if tab_info["type"] == "json":
            editor = tab_info["editor"]
            return editor.get_data()
        
        return None
    
    def export_full_json(self):
        """导出完整JSON文件"""
        if not self.parsed_data:
            messagebox.showwarning("警告", "请先解析JSON文件！")
            return
        
        # 检查是否至少选择一个模块
        selected_count = sum(1 for var in self.module_vars.values() if var.get())
        if selected_count == 0:
            messagebox.showwarning("警告", "请至少选择一个模块！")
            return
        
        # 选择保存文件
        source_filename = self.parsed_data.get("sourceFileName", "lobechat_backup")
        default_filename = source_filename.replace(".json", "") + "_export.json"
        
        file_path = filedialog.asksaveasfilename(
            title="保存JSON文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile=default_filename
        )
        
        if not file_path:
            return
        
        self.app.log_message(f"开始导出JSON，已选择 {selected_count} 个模块...", "INFO")
        
        try:
            # 验证所有模块数据
            self._validate_all_modules()
            
            # 获取导出数据
            export_data = self.get_export_data()
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            # 统计信息
            data_stats = export_data.get("data", {})
            stats_msg = "\n".join([
                f"- {self.modules_dict.get(k, {}).get('label', k)}: {len(v) if isinstance(v, list) else 1} 项"
                for k, v in data_stats.items()
            ])
            
            self.app.log_message(f"✅ JSON导出成功: {file_path}", "SUCCESS")
            messagebox.showinfo(
                "导出成功",
                f"已导出包含 {len(data_stats)} 个模块的JSON文件\n\n{stats_msg}\n\n文件路径:\n{file_path}"
            )
            
        except ValueError as e:
            self.app.log_message(f"数据验证失败: {str(e)}", "ERROR")
            messagebox.showerror("验证失败", f"数据格式错误:\n{str(e)}\n\n请检查并修复后重试。")
        except Exception as e:
            self.app.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def copy_current_tab(self):
        """复制当前选项卡的JSON数据到剪贴板"""
        current_tab_index = self.notebook.index(self.notebook.select())
        current_module = MODULES_CONFIG[current_tab_index]
        module_key = current_module["key"]
        
        if module_key not in self.tabs:
            return
        
        tab_info = self.tabs[module_key]
        
        try:
            if tab_info["type"] == "json":
                editor = tab_info["editor"]
                data = editor.get_data()
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                
                self.app.clipboard_manager.copy_text(json_str)
                self.app.log_message(f"✅ 已复制 {current_module['label']} 的JSON数据", "SUCCESS")
                
            elif tab_info["type"] == "tree":
                self.app.log_message("综合视图不支持复制，请使用右键菜单功能", "INFO")
                
        except Exception as e:
            self.app.log_message(f"复制失败: {str(e)}", "ERROR")
            messagebox.showerror("复制失败", str(e))
    
    def _validate_all_modules(self):
        """验证所有启用模块的数据格式"""
        for module_key, var in self.module_vars.items():
            if not var.get():
                continue
            
            if module_key in self.tabs:
                tab_info = self.tabs[module_key]
                if tab_info["type"] == "json":
                    editor = tab_info["editor"]
                    try:
                        # 尝试获取数据，会自动验证JSON格式
                        editor.get_data()
                    except ValueError as e:
                        module_label = self.modules_dict[module_key]["label"]
                        raise ValueError(f"{module_label}: {str(e)}")
    
    def _select_all_modules(self):
        """全选所有模块"""
        for module_key, var in self.module_vars.items():
            module = self.modules_dict.get(module_key, {})
            if not module.get("required", False):  # 不影响已锁定的必需模块
                var.set(True)
        self.app.log_message("已全选所有可选模块", "INFO")
    
    def _deselect_all_modules(self):
        """取消选择所有可选模块"""
        for module_key, var in self.module_vars.items():
            module = self.modules_dict.get(module_key, {})
            if not module.get("required", False):
                var.set(False)
        self.app.log_message("已取消选择所有可选模块", "INFO")
    
    def _select_required_only(self):
        """仅选择必需模块"""
        for module_key, var in self.module_vars.items():
            module = self.modules_dict.get(module_key, {})
            var.set(module.get("required", False))
        self.app.log_message("已选择仅必需模块", "INFO")
    
    def _on_module_changed(self, module_key: str):
        """模块数据变更回调"""
        module_label = self.modules_dict.get(module_key, {}).get("label", module_key)
        # 可以在这里添加自动保存等功能
        pass
    
    def configure_theme(self, theme: str):
        """
        配置主题
        
        Args:
            theme: 主题名称
        """
        for tab_info in self.tabs.values():
            if tab_info["type"] == "json":
                editor = tab_info["editor"]
                editor.configure_theme(theme)
            elif tab_info["type"] == "tree":
                controller = tab_info["controller"]
                controller.configure_style(theme)
