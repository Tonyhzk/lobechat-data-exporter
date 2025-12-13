"""
树形视图控制器
负责管理数据树的显示和更新
"""

from tkinter import ttk
from ttkbootstrap.constants import *
from ..utils.file_utils import format_datetime
from ..config import THEME_DARK, THEME_LIGHT


class TreeViewController:
    """树形视图控制器"""
    
    def __init__(self, parent, app):
        """
        初始化树形视图控制器
        
        Args:
            parent: 父容器
            app: 主应用实例
        """
        self.app = app
        self.sort_column = None
        self.sort_reverse = False
        self.create_tree(parent)
    
    def create_tree(self, parent):
        """创建树形视图"""
        # 树形视图容器
        tree_container = ttk.Frame(parent)
        tree_container.pack(fill=BOTH, expand=YES)
        
        # 滚动条
        tree_scroll_y = ttk.Scrollbar(tree_container, orient=VERTICAL)
        tree_scroll_y.pack(side=RIGHT, fill=Y)
        
        tree_scroll_x = ttk.Scrollbar(tree_container, orient=HORIZONTAL)
        tree_scroll_x.pack(side=BOTTOM, fill=X)
        
        # Treeview
        self.tree = ttk.Treeview(
            tree_container,
            columns=("type", "count", "time", "id"),
            show="tree headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            height=15
        )
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # 配置列和绑定排序事件
        self.tree.heading("#0", text="名称", command=lambda: self.sort_by_column("#0", False))
        self.tree.heading("type", text="类型", command=lambda: self.sort_by_column("type", False))
        self.tree.heading("count", text="数量", command=lambda: self.sort_by_column("count", True))
        self.tree.heading("time", text="时间", command=lambda: self.sort_by_column("time", False))
        self.tree.heading("id", text="ID", command=lambda: self.sort_by_column("id", False))
        
        self.tree.column("#0", width=280)
        self.tree.column("type", width=60)
        self.tree.column("count", width=100)
        self.tree.column("time", width=150)
        self.tree.column("id", width=100)
        
        # 配置样式
        self.configure_style(self.app.current_theme)
    
    def configure_style(self, theme):
        """配置树形视图样式"""
        style = ttk.Style()
        
        if theme == THEME_DARK:
            style.configure("Treeview",
                          background="#2b2b2b",
                          foreground="#ffffff",
                          fieldbackground="#2b2b2b",
                          borderwidth=1,
                          relief="solid")
            style.map("Treeview", background=[("selected", "#4a6fa5")])
        else:
            style.configure("Treeview",
                          background="#ffffff",
                          foreground="#000000",
                          fieldbackground="#ffffff",
                          borderwidth=1,
                          relief="solid")
            style.map("Treeview", background=[("selected", "#0d6efd")])
    
    def update_tree(self, parsed_data):
        """更新树形视图"""
        # 清空树
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        if not parsed_data:
            return
        
        groups = parsed_data["groups"]
        
        for group in groups:
            # 添加助手节点
            agent_label = group["agentLabel"]
            agent_id = group["agentId"]
            
            session_count = len(group["sessions"])
            topic_count = sum(len(s["topics"]) for s in group["sessions"])
            
            agent_node = self.tree.insert(
                "",
                "end",
                text=agent_label,
                values=("助手", f"{session_count}会话 / {topic_count}主题", "", agent_id),
                tags=("agent",)
            )
            
            # 添加会话节点
            for session_group in group["sessions"]:
                session_label = session_group["sessionLabel"]
                session_id = session_group["sessionId"]
                
                topic_count_in_session = len(session_group["topics"])
                msg_count_in_session = sum(len(t["messages"]) for t in session_group["topics"])
                
                session_node = self.tree.insert(
                    agent_node,
                    "end",
                    text=session_label,
                    values=("会话", f"{topic_count_in_session}主题 / {msg_count_in_session}消息", "", session_id),
                    tags=("session",)
                )
                
                # 添加主题节点
                for topic_group in session_group["topics"]:
                    topic_label = topic_group["topicLabel"]
                    topic_id = topic_group["topicId"]
                    msg_count = len(topic_group["messages"])
                    
                    created_at = ""
                    if topic_group["topic"]:
                        created_at = format_datetime(topic_group["topic"].get("createdAt"))
                    
                    topic_node = self.tree.insert(
                        session_node,
                        "end",
                        text=topic_label,
                        values=("主题", f"{msg_count}消息", created_at, topic_id),
                        tags=("topic",)
                    )
                    
                    # 添加消息节点
                    for idx, msg in enumerate(topic_group["messages"], 1):
                        msg_id = msg.get("id", "")
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")
                        
                        # 生成消息预览
                        if isinstance(content, str):
                            preview = content.strip().split('\n')[0]
                            if len(preview) > 40:
                                preview = preview[:40] + "..."
                        else:
                            preview = str(content)[:40] + "..."
                        
                        # 消息显示名称
                        msg_label = f"[{idx}] {role}: {preview}"
                        msg_time = format_datetime(msg.get("createdAt") or msg.get("updatedAt"))
                        
                        self.tree.insert(
                            topic_node,
                            "end",
                            text=msg_label,
                            values=("消息", "", msg_time, msg_id),
                            tags=("message",)
                        )
    
    def sort_by_column(self, col, is_numeric):
        """
        点击表头排序
        
        Args:
            col: 列标识
            is_numeric: 是否为数值列
        """
        # 获取当前父节点的所有子项
        parent = self.tree.focus()
        if not parent:
            parent = ""
        
        # 获取所有子项
        items = [(self.tree.item(child), child) for child in self.tree.get_children(parent)]
        
        if not items:
            return
        
        # 判断是否需要反转排序
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        
        # 排序
        if col == "#0":
            # 按名称排序
            items.sort(key=lambda x: x[0]["text"].lower(), reverse=self.sort_reverse)
        elif is_numeric:
            # 按数值排序（提取数字部分）
            def extract_number(item):
                value = item[0]["values"][self.tree["columns"].index(col)]
                # 尝试提取第一个数字
                import re
                numbers = re.findall(r'\d+', str(value))
                return int(numbers[0]) if numbers else 0
            
            items.sort(key=extract_number, reverse=self.sort_reverse)
        else:
            # 按文本排序
            col_index = self.tree["columns"].index(col)
            items.sort(key=lambda x: str(x[0]["values"][col_index]).lower(), reverse=self.sort_reverse)
        
        # 重新排列
        for index, (item, child_id) in enumerate(items):
            self.tree.move(child_id, parent, index)
        
        # 更新表头显示排序状态
        for column in ["#0"] + list(self.tree["columns"]):
            current_text = self.tree.heading(column)["text"]
            # 移除旧的排序指示符
            current_text = current_text.replace(" ▲", "").replace(" ▼", "")
            
            if column == col:
                # 添加新的排序指示符
                indicator = " ▼" if self.sort_reverse else " ▲"
                self.tree.heading(column, text=current_text + indicator)
            else:
                self.tree.heading(column, text=current_text)
        
        # 记录日志
        sort_direction = "降序" if self.sort_reverse else "升序"
        col_name = self.tree.heading(col)["text"].replace(" ▲", "").replace(" ▼", "")
        self.app.log_message(f"按 '{col_name}' 列{sort_direction}排序", "INFO")
