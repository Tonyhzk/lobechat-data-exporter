"""
剪贴板操作工具
"""

import tkinter as tk


class ClipboardManager:
    """剪贴板管理器"""
    
    def __init__(self, master: tk.Tk):
        """
        初始化剪贴板管理器
        
        Args:
            master: Tkinter主窗口
        """
        self.master = master
    
    def copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        self.master.update()
    
    def copy_text(self, text: str):
        """复制文本到剪贴板（别名方法）"""
        self.copy_to_clipboard(text)
