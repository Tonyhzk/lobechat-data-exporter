"""
JSON 编辑器组件
提供JSON数据的查看、编辑、格式化和验证功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import json
from typing import Any, Optional, Callable


class JSONEditor(ttk.Frame):
    """JSON编辑器组件"""
    
    def __init__(self, parent, module_name: str, module_label: str, 
                 is_required: bool = True, on_change: Optional[Callable] = None):
        """
        初始化JSON编辑器
        
        Args:
            parent: 父组件
            module_name: 模块键名（如 userSettings）
            module_label: 模块显示名称
            is_required: 是否必需模块
            on_change: 数据变更回调函数
        """
        super().__init__(parent)
        
        self.module_name = module_name
        self.module_label = module_label
        self.is_required = is_required
        self.on_change = on_change
        self.original_data = None  # 原始数据
        
        self._create_ui()
    
    def _create_ui(self):
        """创建UI组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, padx=5, pady=5)
        
        # 模块信息
        info_frame = ttk.Frame(toolbar)
        info_frame.pack(side=LEFT, fill=X, expand=YES)
        
        ttk.Label(
            info_frame, 
            text=f"📝 {self.module_label}",
            font=("", 10, "bold")
        ).pack(side=LEFT, padx=5)
        
        if self.is_required:
            ttk.Label(
                info_frame,
                text="[必需]",
                foreground="#dc3545",
                font=("", 9)
            ).pack(side=LEFT)
        
        # 工具按钮
        btn_frame = ttk.Frame(toolbar)
        btn_frame.pack(side=RIGHT)
        
        ttk.Button(
            btn_frame,
            text="格式化",
            command=self.format_json,
            bootstyle="info-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="验证",
            command=self.validate_json,
            bootstyle="success-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="重置",
            command=self.reset_data,
            bootstyle="warning-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        # 统计信息
        self.stats_label = ttk.Label(
            toolbar,
            text="",
            font=("", 9),
            foreground="gray"
        )
        self.stats_label.pack(side=RIGHT, padx=10)
        
        # 编辑器容器
        editor_container = ttk.Frame(self)
        editor_container.pack(fill=BOTH, expand=YES, padx=5, pady=(0, 5))
        
        # 滚动条
        y_scroll = ttk.Scrollbar(editor_container, orient=VERTICAL)
        y_scroll.pack(side=RIGHT, fill=Y)
        
        x_scroll = ttk.Scrollbar(editor_container, orient=HORIZONTAL)
        x_scroll.pack(side=BOTTOM, fill=X)
        
        # JSON文本编辑器
        self.text = tk.Text(
            editor_container,
            wrap=tk.NONE,
            font=("Consolas", 10),
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
            bg="#1e1e1e",
            fg="#e0e0e0",
            insertbackground="white",
            selectbackground="#264f78",
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.text.pack(side=LEFT, fill=BOTH, expand=YES)
        
        y_scroll.config(command=self.text.yview)
        x_scroll.config(command=self.text.xview)
        
        # 绑定修改事件
        self.text.bind("<<Modified>>", self._on_text_modified)
        
        # 底部状态栏
        self.status_bar = ttk.Label(
            self,
            text="就绪",
            relief=tk.SUNKEN,
            anchor=W,
            font=("", 9)
        )
        self.status_bar.pack(fill=X, padx=5, pady=(0, 5))
    
    def set_data(self, data: Any):
        """
        设置JSON数据
        
        Args:
            data: 要设置的数据（通常是list或dict）
        """
        self.original_data = data
        self.text.delete(1.0, tk.END)
        
        if data is None or (isinstance(data, list) and len(data) == 0):
            self.text.insert(1.0, "[]")
            self._update_stats(0)
        else:
            try:
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                self.text.insert(1.0, json_str)
                
                # 更新统计
                if isinstance(data, list):
                    self._update_stats(len(data))
                elif isinstance(data, dict):
                    self._update_stats(1)
                
            except Exception as e:
                self.text.insert(1.0, f"# 数据序列化失败: {str(e)}")
                self.status_bar.config(text=f"❌ 错误: {str(e)}")
        
        # 重置修改标记
        self.text.edit_modified(False)
        self.status_bar.config(text="✅ 数据已加载")
    
    def get_data(self) -> Any:
        """
        获取编辑后的JSON数据
        
        Returns:
            解析后的数据
        """
        content = self.text.get(1.0, tk.END).strip()
        
        if not content:
            return []
        
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON格式错误: {str(e)}")
    
    def format_json(self):
        """格式化JSON"""
        try:
            data = self.get_data()
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            
            self.text.delete(1.0, tk.END)
            self.text.insert(1.0, json_str)
            
            self.status_bar.config(text="✅ JSON已格式化")
            
        except Exception as e:
            messagebox.showerror("格式化失败", f"无法格式化JSON:\n{str(e)}")
            self.status_bar.config(text=f"❌ 格式化失败: {str(e)}")
    
    def validate_json(self):
        """验证JSON格式"""
        try:
            data = self.get_data()
            
            # 统计信息
            if isinstance(data, list):
                count = len(data)
                msg = f"✅ JSON格式正确\n\n数据类型: 数组\n项目数量: {count}"
            elif isinstance(data, dict):
                count = len(data.keys())
                msg = f"✅ JSON格式正确\n\n数据类型: 对象\n字段数量: {count}"
            else:
                msg = f"✅ JSON格式正确\n\n数据类型: {type(data).__name__}"
            
            messagebox.showinfo("验证成功", msg)
            self.status_bar.config(text="✅ JSON格式正确")
            
        except Exception as e:
            messagebox.showerror("验证失败", f"JSON格式错误:\n{str(e)}")
            self.status_bar.config(text=f"❌ 验证失败: {str(e)}")
    
    def reset_data(self):
        """重置为原始数据"""
        if self.original_data is None:
            messagebox.showinfo("提示", "没有可重置的原始数据")
            return
        
        if messagebox.askyesno("确认重置", "确定要重置为原始数据吗？\n当前的修改将丢失。"):
            self.set_data(self.original_data)
            self.status_bar.config(text="✅ 已重置为原始数据")
    
    def is_modified(self) -> bool:
        """检查数据是否被修改"""
        return self.text.edit_modified()
    
    def configure_theme(self, theme: str):
        """
        配置主题
        
        Args:
            theme: 主题名称（dark/light）
        """
        if theme == "darkly" or theme == "cyborg":
            self.text.config(
                bg="#1e1e1e",
                fg="#e0e0e0",
                insertbackground="white",
                selectbackground="#264f78"
            )
        else:
            self.text.config(
                bg="#ffffff",
                fg="#000000",
                insertbackground="black",
                selectbackground="#b3d7ff"
            )
    
    def _update_stats(self, count: int):
        """更新统计信息"""
        if count == 0:
            self.stats_label.config(text="空数据")
        else:
            self.stats_label.config(text=f"共 {count} 项")
    
    def _on_text_modified(self, event):
        """文本修改事件处理"""
        if self.text.edit_modified():
            self.status_bar.config(text="⚠️ 已修改（未保存）")
            
            if self.on_change:
                self.on_change(self.module_name)
            
            # 重置修改标记，避免重复触发
            self.text.edit_modified(False)


class ReadOnlyJSONViewer(ttk.Frame):
    """只读JSON查看器（用于某些不可编辑的数据）"""
    
    def __init__(self, parent, title: str = "数据查看"):
        super().__init__(parent)
        
        # 标题
        ttk.Label(
            self,
            text=f"📄 {title}",
            font=("", 10, "bold")
        ).pack(anchor=W, padx=5, pady=5)
        
        # 查看器容器
        viewer_container = ttk.Frame(self)
        viewer_container.pack(fill=BOTH, expand=YES, padx=5, pady=(0, 5))
        
        # 滚动条
        y_scroll = ttk.Scrollbar(viewer_container, orient=VERTICAL)
        y_scroll.pack(side=RIGHT, fill=Y)
        
        # JSON文本查看器
        self.text = tk.Text(
            viewer_container,
            wrap=tk.NONE,
            font=("Consolas", 10),
            yscrollcommand=y_scroll.set,
            bg="#f5f5f5",
            fg="#000000",
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.text.pack(side=LEFT, fill=BOTH, expand=YES)
        
        y_scroll.config(command=self.text.yview)
    
    def set_data(self, data: Any):
        """设置数据"""
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        
        if data is None or (isinstance(data, list) and len(data) == 0):
            self.text.insert(1.0, "# 无数据")
        else:
            try:
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                self.text.insert(1.0, json_str)
            except Exception as e:
                self.text.insert(1.0, f"# 数据序列化失败: {str(e)}")
        
        self.text.config(state=tk.DISABLED)
