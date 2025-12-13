"""
全局配置文件
所有应用程序配置常量
"""

# ========== 窗口设置 ==========
WINDOW_TITLE = "LobeChat 数据导出工具"
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 900
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700

# ========== 功能开关 ==========
ENABLE_TRAY = False  # 托盘功能开关
ENABLE_LOG_FILE = False  # 日志文件写入开关
ENABLE_AUTO_SAVE = True  # 自动保存配置开关
ENABLE_DEBUG = True  # DEBUG模式开关

# ========== 主题设置 ==========
DEFAULT_THEME = "darkly"  # 默认主题 (darkly/litera)
THEME_LIGHT = "litera"
THEME_DARK = "darkly"

# ========== 文件设置 ==========
CONFIG_FILE_NAME = "lobechat_data_exporter_config.json"  # 配置文件名
LOG_FILE_NAME = "lobechat_data_exporter.log"  # 日志文件名
LOG_MAX_SIZE = 10 * 1024 * 1024  # 日志文件最大大小（10MB）
LOG_BACKUP_COUNT = 3  # 日志文件备份数量

# ========== UI组件设置 ==========
BUTTON_WIDTH = 15  # 按钮默认宽度
ENTRY_WIDTH = 40  # 输入框默认宽度
LOG_DISPLAY_HEIGHT = 8  # 日志显示框高度（行数）
TREE_ROW_HEIGHT = 25  # Treeview行高

# ========== 数值限制 ==========
MAX_RECENT_FILES = 10  # 最近文件列表最大数量
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*]+'  # 无效文件名字符
MAX_FILENAME_LENGTH = 80  # 最大文件名长度
