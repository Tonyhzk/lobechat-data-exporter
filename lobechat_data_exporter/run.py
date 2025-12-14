"""
LobeChat 数据导出工具 - 启动脚本
直接运行此文件启动程序

无论父目录名称如何修改，此脚本都能正常工作
支持 PyInstaller 打包后运行
"""

import sys
from pathlib import Path

# 检测是否在 PyInstaller 打包环境中运行
def is_frozen():
    """判断是否在打包环境中运行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


if is_frozen():
    # PyInstaller 打包环境：直接导入模块（模块已被打包进去）
    from lobechat_data_exporter.main import main
else:
    # 开发环境：动态导入
    # 获取当前脚本所在目录和父目录
    current_dir = Path(__file__).parent
    parent_dir = current_dir.parent

    # 设置统一的 pycache 目录，与项目文件夹并列
    # 这样 __pycache__ 不会散落在各个子目录中
    pycache_dir = parent_dir / ".pycache"
    sys.pycache_prefix = str(pycache_dir)

    import importlib

    # 获取当前目录名（即包名），无论目录叫什么都能用
    package_name = current_dir.name

    # 将父目录添加到 Python 路径，以便正确导入包
    sys.path.insert(0, str(parent_dir))

    def main():
        # 动态导入 main 模块，不依赖硬编码的目录名
        main_module = importlib.import_module(f"{package_name}.main")
        main_module.main()


if __name__ == "__main__":
    main()
