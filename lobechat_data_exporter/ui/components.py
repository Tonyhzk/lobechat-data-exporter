"""
UI 组件工厂函数
负责创建各种UI组件
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *

from ..config import *


def create_toolbar(master, app):
    """创建顶部工具栏"""
    import webbrowser
    from ..config import GITHUB_URL
    
    toolbar = ttk.Frame(master)
    toolbar.pack(fill=X, padx=10, pady=5)
    
    # 数据库连接按钮
    db_btn = ttk.Button(
        toolbar,
        text="🗄️ 数据库",
        command=app.show_db_connection_dialog,
        bootstyle="warning-outline",
        width=BUTTON_WIDTH
    )
    db_btn.pack(side=LEFT, padx=5)
    
    # 主题切换按钮
    theme_btn = ttk.Button(
        toolbar,
        text="🌓 切换主题",
        command=app.toggle_theme,
        bootstyle="secondary-outline",
        width=BUTTON_WIDTH
    )
    theme_btn.pack(side=LEFT, padx=5)
    
    # 刷新按钮
    refresh_btn = ttk.Button(
        toolbar,
        text="🔄 重新加载",
        command=app.reload_data,
        bootstyle="info-outline",
        width=BUTTON_WIDTH
    )
    refresh_btn.pack(side=LEFT, padx=5)
    
    # 关于按钮
    about_btn = ttk.Button(
        toolbar,
        text="ℹ️ 关于",
        command=app.show_about,
        bootstyle="secondary-outline",
        width=BUTTON_WIDTH
    )
    about_btn.pack(side=RIGHT, padx=5)
    
    # GitHub按钮
    github_btn = ttk.Button(
        toolbar,
        text="🌐 GitHub",
        command=lambda: webbrowser.open(GITHUB_URL),
        bootstyle="primary-outline",
        width=BUTTON_WIDTH
    )
    github_btn.pack(side=RIGHT, padx=5)
    
    return toolbar


def create_file_selector(parent, app):
    """创建文件选择区域"""
    try:
        from ..utils.drag_drop import DND_SUPPORT
        has_dnd = DND_SUPPORT
    except:
        has_dnd = False
    
    frame_title = "📁 选择LobeChat备份文件（支持拖入JSON文件）" if has_dnd else "📁 选择LobeChat备份文件"
    file_frame = ttk.LabelFrame(parent, text=frame_title, padding=10)
    file_frame.grid(row=0, column=0, sticky=(W, E), pady=(0, 10))
    
    # 文件路径输入框
    file_path_var = tk.StringVar()
    file_entry = ttk.Entry(file_frame, textvariable=file_path_var, width=ENTRY_WIDTH)
    file_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
    
    # 浏览按钮
    browse_btn = ttk.Button(
        file_frame,
        text="浏览...",
        command=app.browse_file,
        bootstyle="primary",
        width=12
    )
    browse_btn.pack(side=LEFT, padx=2)
    
    # 解析按钮
    parse_btn = ttk.Button(
        file_frame,
        text="解析数据",
        command=app.parse_json_file,
        bootstyle="success",
        width=12
    )
    parse_btn.pack(side=LEFT, padx=2)
    
    return file_path_var, file_entry


def create_stats_area(parent):
    """创建统计信息区域"""
    stats_frame = ttk.LabelFrame(parent, text="📊 数据统计", padding=10)
    stats_frame.grid(row=1, column=0, sticky=(W, E), pady=(0, 10))
    
    # 创建统计标签
    stats_container = ttk.Frame(stats_frame)
    stats_container.pack(fill=X)
    
    stat_labels = {}
    # 注：移除会话数量统计，因为一个助手只有一个会话，会话与助手数量相同
    stat_items = [
        ("助手数量", "agentCount"),
        ("主题数量", "topicCount"),
        ("消息数量", "messageCount")
    ]
    
    for idx, (label, key) in enumerate(stat_items):
        frame = ttk.Frame(stats_container)
        frame.pack(side=LEFT, fill=X, expand=YES, padx=10)
        
        ttk.Label(frame, text=label + ":", font=("", 10)).pack(anchor=W)
        value_label = ttk.Label(frame, text="0", font=("", 14, "bold"), bootstyle="info")
        value_label.pack(anchor=W)
        stat_labels[key] = value_label
    
    return stat_labels


def create_export_options(parent, app):
    """创建导出选项区域"""
    # 创建Notebook标签页
    notebook = ttk.Notebook(parent)
    notebook.pack(fill=BOTH, expand=YES)
    
    # Markdown导出标签页
    md_tab = ttk.Frame(notebook, padding=10)
    notebook.add(md_tab, text="Markdown导出")
    md_mode, md_metadata, md_prompt = create_markdown_export_tab(md_tab, app)
    
    # JSON导出标签页
    json_tab = ttk.Frame(notebook, padding=10)
    notebook.add(json_tab, text="JSON导出")
    json_vars = create_json_export_tab(json_tab, app)
    
    return md_mode, md_metadata, md_prompt, json_vars


def create_markdown_export_tab(parent, app):
    """创建Markdown导出标签页"""
    # 导出模式选择
    mode_frame = ttk.LabelFrame(parent, text="导出模式", padding=10)
    mode_frame.pack(fill=X, pady=(0, 10))
    
    md_export_mode = tk.StringVar(value="directory")
    
    modes = [
        ("按目录结构导出", "directory", "助手/会话/主题层级结构"),
        ("单个对话导出", "single_topic", "右键点击主题节点导出"),
        ("助手对话整合", "agent_merge", "右键点击助手节点导出整合文件"),
        ("助手对话分离", "agent_separate", "右键点击助手节点导出多个文件")
    ]
    
    for text, value, desc in modes:
        rb = ttk.Radiobutton(
            mode_frame,
            text=text,
            variable=md_export_mode,
            value=value,
            bootstyle="primary"
        )
        rb.pack(anchor=W, pady=2)
        ttk.Label(mode_frame, text=f"  └─ {desc}", font=("", 9), foreground="gray").pack(anchor=W, padx=20)
    
    # 导出选项
    options_frame = ttk.LabelFrame(parent, text="导出选项", padding=10)
    options_frame.pack(fill=X, pady=(0, 10))
    
    md_include_metadata = tk.BooleanVar(value=True)
    md_include_system_prompt = tk.BooleanVar(value=True)
    
    ttk.Checkbutton(
        options_frame,
        text="包含元数据（时间、ID等）",
        variable=md_include_metadata,
        bootstyle="primary-round-toggle"
    ).pack(anchor=W, pady=3)
    
    ttk.Checkbutton(
        options_frame,
        text="包含系统提示词",
        variable=md_include_system_prompt,
        bootstyle="primary-round-toggle"
    ).pack(anchor=W, pady=3)
    
    # 导出按钮
    export_btn = ttk.Button(
        parent,
        text="🚀 开始导出 Markdown",
        command=app.export_markdown,
        bootstyle="success",
        width=25
    )
    export_btn.pack(pady=10)
    
    return md_export_mode, md_include_metadata, md_include_system_prompt


def create_json_export_tab(parent, app):
    """创建JSON导出标签页"""
    # 说明
    info_label = ttk.Label(
        parent,
        text="选择需要导出的数据模块：",
        font=("", 9),
        wraplength=300
    )
    info_label.pack(anchor=W, pady=(0, 10))
    
    # 模块选择区域
    modules_frame = ttk.LabelFrame(parent, text="数据模块选择", padding=10)
    modules_frame.pack(fill=BOTH, expand=YES, pady=(0, 10))
    
    # 创建滚动区域
    canvas = tk.Canvas(modules_frame, height=180)
    scrollbar = ttk.Scrollbar(modules_frame, orient=VERTICAL, command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side=LEFT, fill=BOTH, expand=YES)
    scrollbar.pack(side=RIGHT, fill=Y)
    
    # 模块复选框
    json_export_vars = {}
    
    modules = [
        ("userSettings", "用户设置", True),
        ("aiProviders", "AI提供商配置", True),
        ("aiModels", "AI模型列表", True),
        ("agents", "助手配置", True),
        ("sessions", "会话列表", True),
        ("topics", "主题列表", True),
        ("messages", "消息记录", True),
        ("agentsToSessions", "助手-会话关联", True),
        ("messageChunks", "消息块", False),
        ("messagePlugins", "消息插件", False),
        ("messageTranslates", "消息翻译", False),
        ("sessionGroups", "会话分组", False),
        ("threads", "对话线程", False),
        ("userInstalledPlugins", "用户插件", False),
    ]
    
    for module_key, module_name, default_val in modules:
        var = tk.BooleanVar(value=default_val)
        json_export_vars[module_key] = var
        
        cb = ttk.Checkbutton(
            scrollable_frame,
            text=f"{module_name} ({module_key})",
            variable=var,
            bootstyle="primary-round-toggle"
        )
        cb.pack(anchor=W, pady=2)
    
    # 快捷按钮
    quick_btns_frame = ttk.Frame(parent)
    quick_btns_frame.pack(fill=X, pady=(0, 10))
    
    ttk.Button(
        quick_btns_frame,
        text="全选",
        command=lambda: app.toggle_all_json_modules(True),
        bootstyle="info-outline",
        width=10
    ).pack(side=LEFT, padx=2)
    
    ttk.Button(
        quick_btns_frame,
        text="全不选",
        command=lambda: app.toggle_all_json_modules(False),
        bootstyle="info-outline",
        width=10
    ).pack(side=LEFT, padx=2)
    
    ttk.Button(
        quick_btns_frame,
        text="仅配置",
        command=app.select_config_only,
        bootstyle="info-outline",
        width=10
    ).pack(side=LEFT, padx=2)
    
    # 导出按钮
    export_btn = ttk.Button(
        parent,
        text="🚀 导出自定义 JSON",
        command=app.export_custom_json,
        bootstyle="success",
        width=25
    )
    export_btn.pack(pady=5)
    
    return json_export_vars


def create_log_area(parent, current_theme):
    """创建日志显示区域"""
    log_frame = ttk.LabelFrame(parent, text="📋 操作日志", padding=10)
    log_frame.grid(row=3, column=0, sticky=(W, E), pady=(0, 5))
    
    # 日志文本框
    log_container = ttk.Frame(log_frame)
    log_container.pack(fill=BOTH, expand=YES)
    
    log_scroll = ttk.Scrollbar(log_container, orient=VERTICAL)
    log_scroll.pack(side=RIGHT, fill=Y)
    
    log_text = tk.Text(
        log_container,
        height=LOG_DISPLAY_HEIGHT,
        wrap=tk.WORD,
        yscrollcommand=log_scroll.set,
        font=("Consolas", 9),
        bg="#1e1e1e" if current_theme == THEME_DARK else "#ffffff",
        fg="#e0e0e0" if current_theme == THEME_DARK else "#000000"
    )
    log_text.pack(side=LEFT, fill=BOTH, expand=YES)
    
    log_scroll.config(command=log_text.yview)
    
    # 配置日志颜色标签
    log_text.tag_config("INFO", foreground="#17a2b8")
    log_text.tag_config("SUCCESS", foreground="#28a745")
    log_text.tag_config("WARNING", foreground="#ffc107")
    log_text.tag_config("ERROR", foreground="#dc3545")
    log_text.tag_config("DEBUG", foreground="#6c757d")
    
    return log_text
