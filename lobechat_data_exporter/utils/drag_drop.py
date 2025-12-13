"""
拖拽功能模块
支持不同平台的文件拖拽
"""

import os
import platform
from typing import List, Callable, Optional

# 条件导入拖拽库
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_SUPPORT = True
except ImportError:
    DND_SUPPORT = False
    TkinterDnD = None


class DragDropManager:
    """拖拽功能管理器"""
    
    def __init__(self, log_callback: Optional[Callable] = None):
        """
        初始化拖拽管理器
        
        Args:
            log_callback: 日志回调函数
        """
        self.log_callback = log_callback
        self.is_macos = platform.system() == 'Darwin'
    
    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
    
    def setup_drag_and_drop(self):
        """设置拖拽功能"""
        try:
            # 为文件路径输入框注册拖拽功能
            self.file_entry.drop_target_register(DND_FILES)
            self.file_entry.dnd_bind('<<Drop>>', self._handle_entry_drop)
            
            # 同时在整个窗口上注册拖拽（备用）
            self.master.drop_target_register(DND_FILES)
            self.master.dnd_bind('<<Drop>>', self._handle_window_drop)
            
            if ENABLE_DEBUG:
                self.log_message("DEBUG: 拖拽功能已启用（支持拖入文件到输入框或窗口）", "DEBUG")
        except Exception as e:
            if ENABLE_DEBUG:
                self.log_message(f"DEBUG: 拖拽功能注册失败: {e}", "DEBUG")
    
    def parse_drop_data(self, data: str) -> List[str]:
        """
        解析拖拽数据（根据平台）
        
        Args:
            data: 拖拽事件数据
        
        Returns:
            文件路径列表
        """
        if self.is_macos:
            return self._parse_macos_drop_data(data)
        else:
            return self._parse_windows_linux_drop_data(data)
    
    def _parse_macos_drop_data(self, data: str) -> List[str]:
        """解析macOS拖拽数据"""
        import urllib.parse
        
        files = []
        for item in data.split():
            # 移除file://前缀
            if item.startswith('file://'):
                item = item[7:]
            
            # URL解码
            item = urllib.parse.unquote(item)
            
            # 处理空格转义
            item = item.replace('\\ ', ' ')
            
            # 移除花括号
            item = item.strip('{}')
            
            if os.path.exists(item):
                files.append(item)
        
        return files


def _parse_windows_linux_drop_data(data: str) -> List[str]:
    """解析Windows/Linux拖拽数据"""
    files = []
    
    # Windows下拖拽的文件路径可能被花括号包裹
    data = data.strip()
    
    # 如果整个字符串被花括号包裹，移除它们
    if data.startswith('{') and data.endswith('}'):
        data = data[1:-1]
    
    # 尝试将其作为单个路径处理
    if os.path.exists(data):
        files.append(data)
    else:
        # 如果不是单个路径，尝试按空格分割
        parts = data.split()
        for part in parts:
            part = part.strip('{}')
            if os.path.exists(part):
                files.append(part)
    
    return files


def setup_drag_drop(master, file_entry, file_drop_callback):
    """
    设置拖拽功能
    
    Args:
        master: 主窗口
        file_entry: 文件输入框
        file_drop_callback: 文件拖放回调函数
    """
    if not DND_SUPPORT:
        return
    
    is_macos = platform.system() == 'Darwin'
    
    def handle_drop(event):
        """处理拖拽事件"""
        try:
            # 解析路径
            if is_macos:
                files = _parse_macos_drop_data(event.data)
            else:
                files = _parse_windows_linux_drop_data(event.data)
            
            if files and files[0]:
                file_drop_callback(files[0])
            
            return event.action
        except Exception as e:
            print(f"拖拽处理失败: {e}")
    
    try:
        # 为文件路径输入框注册拖拽功能
        file_entry.drop_target_register(DND_FILES)
        file_entry.dnd_bind('<<Drop>>', handle_drop)
        
        # 同时在整个窗口上注册拖拽（备用）
        master.drop_target_register(DND_FILES)
        master.dnd_bind('<<Drop>>', handle_drop)
    except Exception as e:
        print(f"拖拽功能注册失败: {e}")


def _parse_macos_drop_data(data: str) -> List[str]:
    """解析macOS拖拽数据"""
    import urllib.parse
    
    files = []
    for item in data.split():
        # 移除file://前缀
        if item.startswith('file://'):
            item = item[7:]
        
        # URL解码
        item = urllib.parse.unquote(item)
        
        # 处理空格转义
        item = item.replace('\\ ', ' ')
        
        # 移除花括号
        item = item.strip('{}')
        
        if os.path.exists(item):
            files.append(item)
    
    return files


def create_root_window():
    """
    创建根窗口（支持拖拽）
    
    Returns:
        Tkinter根窗口
    """
    import ttkbootstrap as ttk_boot
    from ..config import DEFAULT_THEME
    
    if DND_SUPPORT:
        root = TkinterDnD.Tk()
        ttk_boot.Style(DEFAULT_THEME)
    else:
        root = ttk_boot.Window(themename=DEFAULT_THEME)
    
    return root
