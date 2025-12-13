"""
文件处理工具函数
包含文件名安全处理、路径操作、日期格式化等
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Set
from ..config import INVALID_FILENAME_CHARS, MAX_FILENAME_LENGTH


def safe_filename(text: str, fallback: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """
    生成安全的文件名
    
    Args:
        text: 原始文本
        fallback: 备用文件名
        max_length: 最大长度
    
    Returns:
        安全的文件名
    """
    if not text or not text.strip():
        text = fallback
    
    text = text.strip()
    
    # 替换非法字符
    text = re.sub(INVALID_FILENAME_CHARS, ' ', text)
    
    # 压缩多个空格
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text:
        text = fallback
    
    # 限制长度
    if len(text) > max_length:
        text = text[:max_length].strip()
    
    # 替换空格为下划线
    text = text.replace(' ', '_')
    
    return text


def ensure_unique_name(name: str, used_names: Set[str]) -> str:
    """
    确保文件名唯一
    
    Args:
        name: 文件名
        used_names: 已使用的文件名集合
    
    Returns:
        唯一的文件名
    """
    if name not in used_names:
        used_names.add(name)
        return name
    
    counter = 1
    while True:
        new_name = f"{name}_{counter}"
        if new_name not in used_names:
            used_names.add(new_name)
            return new_name
        counter += 1


def format_datetime(dt_str: Optional[str]) -> str:
    """
    格式化日期时间
    
    Args:
        dt_str: ISO格式的日期时间字符串
    
    Returns:
        格式化后的日期时间字符串
    """
    if not dt_str:
        return ""
    
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return ""


def get_app_path() -> Path:
    """
    获取应用程序路径
    
    Returns:
        应用程序路径
    """
    if getattr(sys, 'frozen', False):
        # 打包后的路径
        return Path(sys.executable).parent
    else:
        # 脚本运行路径 - 返回包根目录
        return Path(__file__).parent.parent.parent
