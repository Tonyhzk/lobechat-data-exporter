"""
LobeChat 数据导出工具 - 程序入口
"""

from .ui.main_window import LobeChatDataExporter
from .utils.drag_drop import create_root_window


def main():
    """主函数"""
    # 创建根窗口（支持拖拽）
    root = create_root_window()
    
    # 创建应用实例
    app = LobeChatDataExporter(root)
    
    # 启动主循环
    root.mainloop()


if __name__ == "__main__":
    main()
