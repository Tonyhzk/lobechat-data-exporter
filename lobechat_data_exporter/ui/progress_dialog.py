"""
进度对话框 - 用于显示长时间加载操作的进度
支持暂停/继续和取消功能
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *


class ProgressDialog:
    """进度对话框类"""
    
    def __init__(self, parent, title: str, message: str, total: int):
        """
        初始化进度对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            message: 提示信息
            total: 总数量
        """
        self.parent = parent
        self.total = total
        self.current = 0
        self.is_paused = False
        self.is_cancelled = False
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 500) // 2
        y = (self.dialog.winfo_screenheight() - 200) // 2
        self.dialog.geometry(f"500x200+{x}+{y}")
        
        # 创建UI
        self._create_ui(message)
        
        # 防止直接关闭
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
    
    def _create_ui(self, message: str):
        """创建UI"""
        # 主容器
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # 提示信息
        msg_label = ttk.Label(
            main_frame,
            text=message,
            font=("Arial", 10),
            wraplength=450
        )
        msg_label.pack(pady=(0, 15))
        
        # 进度信息
        self.progress_label = ttk.Label(
            main_frame,
            text=f"进度: 0 / {self.total}",
            font=("Arial", 9)
        )
        self.progress_label.pack(pady=(0, 10))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(
            main_frame,
            length=450,
            mode='determinate',
            maximum=self.total if self.total > 0 else 100,
            bootstyle="success"
        )
        self.progress_bar.pack(pady=(0, 20))
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()
        
        # 暂停/继续按钮
        self.pause_button = ttk.Button(
            button_frame,
            text="⏸ 暂停",
            command=self.toggle_pause,
            bootstyle="warning",
            width=12
        )
        self.pause_button.pack(side=LEFT, padx=5)
        
        # 取消按钮
        self.cancel_button = ttk.Button(
            button_frame,
            text="✕ 取消",
            command=self.cancel,
            bootstyle="danger",
            width=12
        )
        self.cancel_button.pack(side=LEFT, padx=5)
    
    def update_progress(self, current: int, message: str = None):
        """
        更新进度
        
        Args:
            current: 当前进度
            message: 可选的状态消息
        """
        self.current = current
        self.progress_bar['value'] = current
        
        if message:
            self.progress_label.config(text=message)
        else:
            self.progress_label.config(text=f"进度: {current} / {self.total}")
        
        self.dialog.update_idletasks()
    
    def toggle_pause(self):
        """切换暂停/继续状态"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.config(text="▶ 继续")
        else:
            self.pause_button.config(text="⏸ 暂停")
    
    def cancel(self):
        """取消操作"""
        self.is_cancelled = True
        self.close()
    
    def close(self):
        """关闭对话框"""
        try:
            self.dialog.grab_release()
            self.dialog.destroy()
        except:
            pass
    
    def wait_if_paused(self):
        """如果暂停则等待"""
        import time
        while self.is_paused and not self.is_cancelled:
            try:
                self.dialog.update()
            except:
                break
            time.sleep(0.1)
