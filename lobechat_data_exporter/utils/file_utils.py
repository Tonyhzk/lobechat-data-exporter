"""
文件处理工具函数
包含文件名安全处理、路径操作、日期格式化等
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, Tuple
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


def parse_datetime_str(dt_str: Optional[str]) -> Optional[datetime]:
    """
    解析ISO格式的日期时间字符串为datetime对象
    
    Args:
        dt_str: ISO格式的日期时间字符串
    
    Returns:
        datetime对象，解析失败返回None
    """
    if not dt_str:
        return None
    
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        # 转换为本地时间（去掉时区信息）
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except:
        return None


def set_file_times(file_path: str, created_at: Optional[str] = None, 
                   modified_at: Optional[str] = None) -> bool:
    """
    设置文件的创建时间和修改时间
    
    Args:
        file_path: 文件路径
        created_at: 创建时间（ISO格式字符串）
        modified_at: 修改时间（ISO格式字符串）
    
    Returns:
        是否成功
    """
    if not os.path.exists(file_path):
        return False
    
    # 解析时间
    created_dt = parse_datetime_str(created_at)
    modified_dt = parse_datetime_str(modified_at)
    
    # 如果没有提供修改时间，使用创建时间
    if modified_dt is None and created_dt is not None:
        modified_dt = created_dt
    
    # 如果没有提供创建时间，使用修改时间
    if created_dt is None and modified_dt is not None:
        created_dt = modified_dt
    
    # 如果都没有提供，直接返回
    if created_dt is None and modified_dt is None:
        return False
    
    try:
        # 设置修改时间和访问时间（使用os.utime，跨平台）
        if modified_dt:
            timestamp = modified_dt.timestamp()
            os.utime(file_path, (timestamp, timestamp))
        
        # Windows上设置创建时间
        if sys.platform == 'win32' and created_dt:
            try:
                import pywintypes
                import win32file
                import win32con
                
                # 打开文件
                handle = win32file.CreateFile(
                    file_path,
                    win32con.GENERIC_WRITE,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                    None,
                    win32con.OPEN_EXISTING,
                    win32con.FILE_ATTRIBUTE_NORMAL,
                    None
                )
                
                try:
                    # 设置创建时间
                    created_time = pywintypes.Time(created_dt)
                    modified_time = pywintypes.Time(modified_dt) if modified_dt else created_time
                    win32file.SetFileTime(handle, created_time, modified_time, modified_time)
                finally:
                    handle.Close()
            except ImportError:
                # 没有安装pywin32，跳过创建时间设置
                pass
            except Exception:
                # 设置创建时间失败，忽略
                pass
        
        return True
    except Exception:
        return False


def get_time_range_from_messages(messages: list) -> Tuple[Optional[str], Optional[str]]:
    """
    从消息列表中获取时间范围（最早创建时间和最晚修改时间）
    
    Args:
        messages: 消息列表
    
    Returns:
        (最早创建时间, 最晚修改时间) 元组
    """
    if not messages:
        return None, None
    
    earliest_created = None
    latest_modified = None
    
    for msg in messages:
        created_at = msg.get("createdAt")
        updated_at = msg.get("updatedAt") or created_at
        
        if created_at:
            created_dt = parse_datetime_str(created_at)
            if created_dt:
                if earliest_created is None or created_dt < parse_datetime_str(earliest_created):
                    earliest_created = created_at
        
        if updated_at:
            updated_dt = parse_datetime_str(updated_at)
            if updated_dt:
                if latest_modified is None or updated_dt > parse_datetime_str(latest_modified):
                    latest_modified = updated_at
    
    return earliest_created, latest_modified


def write_file_with_timestamp(file_path: str, content: str, 
                               created_at: Optional[str] = None,
                               modified_at: Optional[str] = None,
                               encoding: str = 'utf-8') -> bool:
    """
    写入文件并设置时间戳
    
    Args:
        file_path: 文件路径
        content: 文件内容
        created_at: 创建时间（ISO格式字符串）
        modified_at: 修改时间（ISO格式字符串）
        encoding: 文件编码
    
    Returns:
        是否成功
    """
    try:
        Path(file_path).write_text(content, encoding=encoding)
        set_file_times(file_path, created_at, modified_at)
        return True
    except Exception:
        return False


def write_json_with_timestamp(file_path: str, data: dict,
                               created_at: Optional[str] = None,
                               modified_at: Optional[str] = None,
                               encoding: str = 'utf-8') -> bool:
    """
    写入JSON文件并设置时间戳
    
    Args:
        file_path: 文件路径
        data: JSON数据
        created_at: 创建时间（ISO格式字符串）
        modified_at: 修改时间（ISO格式字符串）
        encoding: 文件编码
    
    Returns:
        是否成功
    """
    import json
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        set_file_times(file_path, created_at, modified_at)
        return True
    except Exception:
        return False
