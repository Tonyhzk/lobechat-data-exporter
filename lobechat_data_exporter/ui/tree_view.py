"""
树形视图控制器
负责管理数据树的显示和更新
"""

import re
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
        
        # Treeview - 增加主题数和消息数两列
        self.tree = ttk.Treeview(
            tree_container,
            columns=("type", "topics", "messages", "time", "id"),
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
        self.tree.heading("topics", text="主题数", command=lambda: self.sort_by_column("topics", True))
        self.tree.heading("messages", text="消息数", command=lambda: self.sort_by_column("messages", True))
        self.tree.heading("time", text="时间", command=lambda: self.sort_by_column("time", False))
        self.tree.heading("id", text="ID", command=lambda: self.sort_by_column("id", False))
        
        self.tree.column("#0", width=280)
        self.tree.column("type", width=60)
        self.tree.column("topics", width=70)
        self.tree.column("messages", width=70)
        self.tree.column("time", width=150)
        self.tree.column("id", width=100)
        
        # 配置样式
        self.configure_style(self.app.current_theme)
        
        # 绑定批量选择事件
        self.tree.bind("<Control-Button-1>", self.on_ctrl_click)
        self.tree.bind("<Shift-Button-1>", self.on_shift_click)
    
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
            
            # 统计主题和消息数量（由于一个助手只有一个会话，直接统计所有主题）
            topic_count = sum(len(s["topics"]) for s in group["sessions"])
            msg_count = sum(len(t["messages"]) for s in group["sessions"] for t in s["topics"])
            
            agent_node = self.tree.insert(
                "",
                "end",
                text=agent_label,
                values=("助手", topic_count, msg_count, "", agent_id),
                tags=("agent",)
            )
            
            # 直接添加主题节点到助手下（跳过会话层级，因为一个助手只有一个会话）
            for session_group in group["sessions"]:
                # 添加主题节点
                for topic_group in session_group["topics"]:
                    topic_label = topic_group["topicLabel"]
                    topic_id = topic_group["topicId"]
                    msg_count_in_topic = len(topic_group["messages"])
                    
                    created_at = ""
                    if topic_group["topic"]:
                        created_at = format_datetime(topic_group["topic"].get("createdAt"))
                    
                    topic_node = self.tree.insert(
                        agent_node,
                        "end",
                        text=topic_label,
                        values=("主题", "", msg_count_in_topic, created_at, topic_id),
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
                            values=("消息", "", "", msg_time, msg_id),
                            tags=("message",)
                        )
    
    def sort_by_column(self, col, is_numeric):
        """
        点击表头排序 - 根据用户选中的节点决定排序哪一级
        
        Args:
            col: 列标识
            is_numeric: 是否为数值列
        """
        # 获取用户当前选中的项
        selection = self.tree.selection()
        
        if selection:
            # 有选中项：获取该项的父节点，排序同级兄弟节点
            selected_item = selection[0]
            parent = self.tree.parent(selected_item)
        else:
            # 没有选中项：排序根级别节点
            parent = ""
        
        # 获取该父节点下的所有子项
        items = [(self.tree.item(child), child) for child in self.tree.get_children(parent)]
        
        if not items:
            self.app.log_message("没有可排序的项目", "INFO")
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
            # 按数值排序
            def extract_number(item):
                col_index = list(self.tree["columns"]).index(col)
                value = item[0]["values"][col_index]
                # 尝试提取数字
                if isinstance(value, (int, float)):
                    return value
                numbers = re.findall(r'\d+', str(value))
                return int(numbers[0]) if numbers else 0
            
            items.sort(key=extract_number, reverse=self.sort_reverse)
        else:
            # 按文本排序
            col_index = list(self.tree["columns"]).index(col)
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
        
        # 记录日志，显示排序的级别
        sort_direction = "降序" if self.sort_reverse else "升序"
        col_name = self.tree.heading(col)["text"].replace(" ▲", "").replace(" ▼", "")
        
        if parent == "":
            level_name = "根级别（助手）"
        else:
            parent_type = self.tree.item(parent, "values")[0] if self.tree.item(parent, "values") else ""
            if parent_type == "助手":
                level_name = "主题级别"
            elif parent_type == "主题":
                level_name = "消息级别"
            else:
                level_name = "当前级别"
        
        self.app.log_message(f"按 '{col_name}' 列{sort_direction}排序 ({level_name}，共{len(items)}项)", "INFO")
    
    def on_ctrl_click(self, event):
        """Ctrl+点击多选"""
        item = self.tree.identify_row(event.y)
        if not item:
            return "break"
        
        # 获取当前选中项
        current_selection = self.tree.selection()
        
        if item in current_selection:
            # 如果已选中，则取消选中
            self.tree.selection_remove(item)
        else:
            # 添加到选中列表
            self.tree.selection_add(item)
        
        return "break"
    
    def on_shift_click(self, event):
        """Shift+点击连续选择"""
        item = self.tree.identify_row(event.y)
        if not item:
            return "break"
        
        # 获取当前选中项
        current_selection = self.tree.selection()
        
        if not current_selection:
            # 如果没有选中项，直接选中
            self.tree.selection_set(item)
            return "break"
        
        # 获取第一个选中项
        first_item = current_selection[0]
        
        # 获取所有项目
        all_items = self.get_all_items()
        
        try:
            first_index = all_items.index(first_item)
            last_index = all_items.index(item)
            
            # 确保顺序正确
            if first_index > last_index:
                first_index, last_index = last_index, first_index
            
            # 选中范围内的所有项目
            for i in range(first_index, last_index + 1):
                self.tree.selection_add(all_items[i])
        except ValueError:
            pass
        
        return "break"
    
    def get_all_items(self):
        """获取所有树项目（扁平列表）"""
        items = []
        
        def traverse(item=''):
            children = self.tree.get_children(item)
            for child in children:
                items.append(child)
                traverse(child)
        
        traverse()
        return items
