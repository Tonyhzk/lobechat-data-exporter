"""
数据库连接对话框
用于配置和连接 PostgreSQL 数据库
"""

import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import threading
from typing import Dict, Optional, Callable, List

from ..core.db_connector import DBConfig, PostgreSQLConnector, test_connection


class DatabaseConnectionDialog:
    """数据库连接对话框"""
    
    def __init__(self, parent, callback: Callable, log_callback: Callable = None, 
                 initial_config: Dict = None):
        """
        初始化数据库连接对话框
        
        Args:
            parent: 父窗口
            callback: 连接成功后的回调函数，接收 (connector, config) 参数
            log_callback: 日志回调函数
            initial_config: 初始配置
        """
        self.parent = parent
        self.callback = callback
        self.log_callback = log_callback
        self.connector = None
        self.result_config = None
        self.users_list = []  # 用户列表
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🗄️ 连接数据库")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 初始化变量
        self._init_variables(initial_config)
        
        # 创建UI
        self._create_ui()
        
        # 居中显示
        self._center_dialog()
    
    def _init_variables(self, initial_config: Dict = None):
        """初始化变量"""
        config = initial_config or {}
        
        self.host_var = tk.StringVar(value=config.get("host", "localhost"))
        self.port_var = tk.StringVar(value=str(config.get("port", 5432)))
        self.database_var = tk.StringVar(value=config.get("database", "lobechat"))
        self.user_var = tk.StringVar(value=config.get("user", "postgres"))
        self.password_var = tk.StringVar(value=config.get("password", ""))
        self.ssl_var = tk.BooleanVar(value=config.get("ssl", False))
        self.user_id_var = tk.StringVar(value=config.get("user_id", ""))
        self.save_password_var = tk.BooleanVar(value=config.get("save_password", False))
        self.selected_user_var = tk.StringVar(value="")
    
    def _create_ui(self):
        """创建UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="PostgreSQL 数据库连接", 
            font=("", 14, "bold")
        )
        title_label.pack(pady=(0, 15))
        
        # 说明
        info_label = ttk.Label(
            main_frame,
            text="连接到 LobeChat 的 PostgreSQL 数据库以读取数据",
            foreground="gray"
        )
        info_label.pack(pady=(0, 15))
        
        # 连接配置区域
        config_frame = ttk.LabelFrame(main_frame, text="连接配置", padding=10)
        config_frame.pack(fill=X, pady=(0, 10))
        
        # 主机
        host_frame = ttk.Frame(config_frame)
        host_frame.pack(fill=X, pady=2)
        ttk.Label(host_frame, text="主机地址:", width=10).pack(side=LEFT)
        ttk.Entry(host_frame, textvariable=self.host_var).pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))
        
        # 端口
        port_frame = ttk.Frame(config_frame)
        port_frame.pack(fill=X, pady=2)
        ttk.Label(port_frame, text="端口:", width=10).pack(side=LEFT)
        ttk.Entry(port_frame, textvariable=self.port_var, width=10).pack(side=LEFT, padx=(5, 0))
        
        # 数据库名
        db_frame = ttk.Frame(config_frame)
        db_frame.pack(fill=X, pady=2)
        ttk.Label(db_frame, text="数据库名:", width=10).pack(side=LEFT)
        ttk.Entry(db_frame, textvariable=self.database_var).pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))
        
        # 用户名
        user_frame = ttk.Frame(config_frame)
        user_frame.pack(fill=X, pady=2)
        ttk.Label(user_frame, text="用户名:", width=10).pack(side=LEFT)
        ttk.Entry(user_frame, textvariable=self.user_var).pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))
        
        # 密码
        pass_frame = ttk.Frame(config_frame)
        pass_frame.pack(fill=X, pady=2)
        ttk.Label(pass_frame, text="密码:", width=10).pack(side=LEFT)
        ttk.Entry(pass_frame, textvariable=self.password_var, show="*").pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))
        
        # SSL选项和保存密码
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill=X, pady=2)
        ttk.Checkbutton(options_frame, text="使用SSL连接", variable=self.ssl_var).pack(side=LEFT)
        ttk.Checkbutton(options_frame, text="保存密码", variable=self.save_password_var).pack(side=LEFT, padx=(20, 0))
        
        # 用户选择区域
        self.user_select_frame = ttk.LabelFrame(main_frame, text="选择账号", padding=10)
        self.user_select_frame.pack(fill=X, pady=(0, 10))
        
        # 提示文字
        self.user_hint_label = ttk.Label(
            self.user_select_frame,
            text="请先点击「测试连接」获取账号列表",
            foreground="gray"
        )
        self.user_hint_label.pack(pady=5)
        
        # 用户选择下拉框
        user_select_inner = ttk.Frame(self.user_select_frame)
        user_select_inner.pack(fill=X, pady=2)
        ttk.Label(user_select_inner, text="选择账号:", width=10).pack(side=LEFT)
        
        self.user_combo = ttk.Combobox(
            user_select_inner, 
            textvariable=self.selected_user_var,
            state="disabled",
            width=40
        )
        self.user_combo.pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))
        
        # 加载全部用户选项
        self.load_all_var = tk.BooleanVar(value=False)
        self.load_all_check = ttk.Checkbutton(
            self.user_select_frame, 
            text="加载全部用户数据（数据量可能很大）", 
            variable=self.load_all_var,
            command=self._on_load_all_changed
        )
        self.load_all_check.pack(anchor=W, pady=(5, 0))
        
        # 状态显示
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(pady=5)
        
        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        self.test_btn = ttk.Button(
            btn_frame, 
            text="🔍 测试连接", 
            command=self._test_connection,
            bootstyle="info"
        )
        self.test_btn.pack(side=LEFT, padx=(0, 5))
        
        self.connect_btn = ttk.Button(
            btn_frame, 
            text="✅ 连接并读取", 
            command=self._connect_and_load,
            bootstyle="success",
            state="disabled"  # 默认禁用，需要先测试连接
        )
        self.connect_btn.pack(side=LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="取消", 
            command=self.dialog.destroy,
            bootstyle="secondary"
        ).pack(side=RIGHT)
    
    def _on_load_all_changed(self):
        """加载全部选项变化"""
        if self.load_all_var.get():
            self.user_combo.configure(state="disabled")
            self.selected_user_var.set("")
        else:
            if self.users_list:
                self.user_combo.configure(state="readonly")
    
    def _center_dialog(self):
        """居中显示对话框"""
        self.dialog.update_idletasks()
        
        # 获取父窗口位置和大小
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # 获取对话框大小
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _get_config(self) -> DBConfig:
        """获取当前配置"""
        return DBConfig(
            host=self.host_var.get().strip(),
            port=int(self.port_var.get().strip() or "5432"),
            database=self.database_var.get().strip(),
            user=self.user_var.get().strip(),
            password=self.password_var.get(),
            ssl=self.ssl_var.get()
        )
    
    def _validate_config(self) -> bool:
        """验证配置"""
        if not self.host_var.get().strip():
            messagebox.showwarning("警告", "请输入主机地址")
            return False
        if not self.database_var.get().strip():
            messagebox.showwarning("警告", "请输入数据库名")
            return False
        if not self.user_var.get().strip():
            messagebox.showwarning("警告", "请输入用户名")
            return False
        return True
    
    def _set_status(self, text: str, color: str = "gray"):
        """设置状态文本"""
        self.status_var.set(text)
        self.status_label.configure(foreground=color)
    
    def _set_buttons_state(self, state: str):
        """设置按钮状态"""
        self.test_btn.configure(state=state)
        # connect_btn 状态由其他逻辑控制
    
    def _test_connection(self):
        """测试数据库连接并获取用户列表"""
        if not self._validate_config():
            return
        
        config = self._get_config()
        
        self._set_status("正在测试连接...", "blue")
        self._set_buttons_state("disabled")
        self.connect_btn.configure(state="disabled")
        
        def test_thread():
            try:
                # 先测试连接
                connector = PostgreSQLConnector(config, self.log_callback)
                
                if connector.connect():
                    # 连接成功，查询用户列表
                    users = self._query_users(connector)
                    
                    # 在主线程中更新UI
                    self.dialog.after(0, lambda: self._on_test_success(connector, users))
                else:
                    self.dialog.after(0, lambda: self._on_test_failed("连接失败"))
                    
            except Exception as e:
                self.dialog.after(0, lambda: self._on_test_failed(str(e)))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _query_users(self, connector: PostgreSQLConnector) -> List[Dict]:
        """查询用户列表"""
        try:
            query = """
                SELECT u.id, u.email, u.full_name, u.created_at,
                       COUNT(DISTINCT m.id) as message_count
                FROM users u
                LEFT JOIN messages m ON u.id = m.user_id
                GROUP BY u.id
                ORDER BY message_count DESC
            """
            return connector.execute_query(query)
        except Exception as e:
            # 如果users表不存在或查询失败，尝试从messages表获取用户
            try:
                query = """
                    SELECT user_id as id, 
                           user_id as email,
                           '' as full_name,
                           MIN(created_at) as created_at,
                           COUNT(*) as message_count
                    FROM messages
                    WHERE user_id IS NOT NULL
                    GROUP BY user_id
                    ORDER BY message_count DESC
                """
                return connector.execute_query(query)
            except:
                return []
    
    def _on_test_success(self, connector: PostgreSQLConnector, users: List[Dict]):
        """测试成功回调"""
        self._set_buttons_state("normal")
        
        self.users_list = users
        self.connector = connector
        
        if users:
            # 构建用户选项列表
            user_options = []
            for u in users:
                user_id = u.get("id", "")
                email = u.get("email", "")
                name = u.get("full_name", "")
                msg_count = u.get("message_count", 0)
                
                # 构建显示文本
                display = email or user_id[:20]
                if name:
                    display = f"{name} ({display})"
                display = f"{display} - {msg_count}条消息"
                
                user_options.append((user_id, display))
            
            # 更新下拉框
            self.user_combo["values"] = [opt[1] for opt in user_options]
            self.user_combo.configure(state="readonly")
            
            # 存储ID映射
            self.user_id_map = {opt[1]: opt[0] for opt in user_options}
            
            # 默认选中第一个
            if user_options:
                self.user_combo.set(user_options[0][1])
            
            self.user_hint_label.config(text=f"✅ 发现 {len(users)} 个账号，请选择要加载的账号")
            self._set_status(f"✅ 连接成功！发现 {len(users)} 个账号", "green")
            
            # 启用连接按钮
            self.connect_btn.configure(state="normal")
        else:
            self.user_hint_label.config(text="未找到用户数据，将加载全部数据")
            self._set_status("✅ 连接成功！未找到用户数据", "green")
            self.load_all_var.set(True)
            self.connect_btn.configure(state="normal")
    
    def _on_test_failed(self, message: str):
        """测试失败回调"""
        self._set_buttons_state("normal")
        self._set_status(f"❌ {message}", "red")
        self.user_hint_label.config(text="连接失败，请检查配置")
    
    def _connect_and_load(self):
        """连接数据库并加载数据"""
        if not self.connector:
            messagebox.showwarning("警告", "请先测试连接")
            return
        
        # 获取选中的用户ID
        user_id = None
        if not self.load_all_var.get():
            selected_display = self.selected_user_var.get()
            if selected_display and hasattr(self, 'user_id_map'):
                user_id = self.user_id_map.get(selected_display)
            
            if not user_id and self.users_list:
                messagebox.showwarning("警告", "请选择一个账号或勾选「加载全部用户数据」")
                return
        
        config = self._get_config()
        
        # 存储结果
        self.result_config = {
            **config.to_dict(),
            "user_id": user_id,
            "save_password": self.save_password_var.get()
        }
        
        self._set_status("✅ 连接成功，正在加载数据...", "green")
        
        # 调用回调函数
        if self.callback:
            self.callback(self.connector, self.result_config)
        
        # 关闭对话框
        self.dialog.destroy()


def show_db_connection_dialog(parent, callback: Callable, log_callback: Callable = None,
                               initial_config: Dict = None):
    """
    显示数据库连接对话框
    
    Args:
        parent: 父窗口
        callback: 连接成功后的回调函数
        log_callback: 日志回调函数
        initial_config: 初始配置
    """
    dialog = DatabaseConnectionDialog(parent, callback, log_callback, initial_config)
    return dialog
