"""
数据选项卡控制器
管理所有数据模块的选项卡展示和数据导出
采用二级标签页结构：主要数据一览 + 其他数据
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttk_boot
from ttkbootstrap.constants import *
import json
import re
from typing import Dict, List, Any, Optional
from pathlib import Path

from .json_editor import JSONEditor
from .tree_view import TreeViewController
from .table_views import (
    ModelsTableViewController,
    ProvidersTableViewController,
    AgentsTableViewController,
    TopicsTableViewController,
    MessagesTableViewController
)
from .search_toolbar import (
    SearchToolbar,
    SearchResultsTable,
    export_table_to_csv,
    export_table_to_excel,
    export_all_tables_to_excel
)


# LobeChat 数据模块配置
# category: "main" 表示主要数据（全部对话），"other" 表示其他数据模块
MODULES_CONFIG = [
    {"key": "overview", "label": "全部对话", "type": "tree", "required": False, "order": 0, "in_export": False, "category": "main"},
    {"key": "userSettings", "label": "用户设置", "type": "json", "required": True, "order": 1, "in_export": True, "category": "other"},
    {"key": "aiProviders", "label": "AI提供商", "type": "json", "required": True, "order": 2, "in_export": True, "category": "other"},
    {"key": "aiModels", "label": "AI模型", "type": "json", "required": True, "order": 3, "in_export": True, "category": "other"},
    {"key": "agents", "label": "助手配置", "type": "json", "required": True, "order": 4, "in_export": True, "category": "other"},
    {"key": "sessions", "label": "会话列表", "type": "json", "required": True, "order": 5, "in_export": True, "category": "other"},
    {"key": "sessionGroups", "label": "会话分组", "type": "json", "required": False, "order": 6, "in_export": True, "category": "other"},
    {"key": "topics", "label": "主题列表", "type": "json", "required": True, "order": 7, "in_export": True, "category": "other"},
    {"key": "messages", "label": "消息记录", "type": "json", "required": True, "order": 8, "in_export": True, "category": "other"},
    {"key": "messageChunks", "label": "消息块", "type": "json", "required": False, "order": 9, "in_export": True, "category": "other"},
    {"key": "messagePlugins", "label": "消息插件", "type": "json", "required": False, "order": 10, "in_export": True, "category": "other"},
    {"key": "messageTranslates", "label": "消息翻译", "type": "json", "required": False, "order": 11, "in_export": True, "category": "other"},
    {"key": "threads", "label": "对话线程", "type": "json", "required": False, "order": 12, "in_export": True, "category": "other"},
    {"key": "agentsToSessions", "label": "助手会话关联", "type": "json", "required": True, "order": 13, "in_export": True, "category": "other"},
    {"key": "userInstalledPlugins", "label": "用户插件", "type": "json", "required": False, "order": 14, "in_export": True, "category": "other"},
]

# 数据一览子标签页配置
MAIN_TAB_CONFIG = [
    {"key": "overview", "label": "💬 全部对话", "type": "tree"},
    {"key": "models_view", "label": "🤖 全部模型", "type": "table"},
    {"key": "providers_view", "label": "🏢 提供商", "type": "table"},
    {"key": "agents_view", "label": "🧑‍💼 助手表", "type": "table"},
    {"key": "topics_view", "label": "📝 话题表", "type": "table"},
    {"key": "messages_view", "label": "💭 消息表", "type": "table"},
    {"key": "search_results", "label": "🔍 搜索结果", "type": "search_results"},
]


class DataTabsController:
    """数据选项卡控制器"""
    
    def __init__(self, parent, app):
        """
        初始化选项卡控制器
        
        Args:
            parent: 父组件
            app: 主应用实例
        """
        self.parent = parent
        self.app = app
        self.parsed_data = None
        self.original_mode = "postgres"
        self.original_schema_hash = ""
        
        # 选项卡组件字典
        self.tabs = {}
        # 模块启用状态
        self.module_vars = {}
        # 模块配置字典
        self.modules_dict = {m["key"]: m for m in MODULES_CONFIG}
        
        # 搜索结果缓存
        self.search_results = []
        
        self._create_ui()
    
    def _create_ui(self):
        """创建UI - 采用二级标签页结构"""
        # 主容器
        main_container = ttk.Frame(self.parent)
        main_container.pack(fill=BOTH, expand=YES)
        
        # 顶级Notebook（主要数据一览 + 其他数据）
        self.main_notebook = ttk.Notebook(main_container)
        self.main_notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # 创建二级标签页结构
        self._create_main_tab()      # 主要数据一览（全部对话）
        self._create_other_tabs()    # 其他数据模块
        self._create_export_tab()    # 全部导出标签页
        
        # 保持兼容性：notebook指向主notebook
        self.notebook = self.main_notebook
    
    def _create_main_tab(self):
        """创建数据一览标签页（包含全部对话子标签页）"""
        # 数据一览容器
        main_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(main_tab_frame, text="📊 数据一览")
        
        # 搜索工具栏
        self.search_toolbar = SearchToolbar(
            main_tab_frame,
            self.app,
            on_search=self._on_search,
            on_export=self._on_export,
            on_search_all=self._on_search_all,
            on_prev=self._on_search_prev,
            on_next=self._on_search_next
        )
        self.search_toolbar.pack(fill=X, padx=5, pady=5)
        
        # 第二排按钮栏（导出和视图控制）
        action_toolbar = ttk.Frame(main_tab_frame)
        action_toolbar.pack(fill=X, padx=5, pady=(0, 5))
        
        # 导出按钮
        ttk.Button(
            action_toolbar,
            text="📥 导出CSV",
            command=lambda: self._on_export("csv"),
            bootstyle="info-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            action_toolbar,
            text="📊 导出Excel",
            command=lambda: self._on_export("excel"),
            bootstyle="info-outline",
            width=11
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            action_toolbar,
            text="📦 导出全部",
            command=lambda: self._on_export("all_excel"),
            bootstyle="success-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Separator(action_toolbar, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=10)
        
        # 表格适配按钮
        ttk.Button(
            action_toolbar,
            text="🔄 表格适配",
            command=self._reset_current_view,
            bootstyle="secondary-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Separator(action_toolbar, orient=VERTICAL).pack(side=LEFT, fill=Y, padx=10)
        
        # 选中整行开关
        self.select_entire_row_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            action_toolbar,
            text="选中整行",
            variable=self.select_entire_row_var,
            command=self._on_select_entire_row_changed,
            bootstyle="primary-round-toggle"
        ).pack(side=LEFT, padx=5)
        
        # 全部对话专用按钮（右侧）
        self.tree_action_frame = ttk.Frame(action_toolbar)
        self.tree_action_frame.pack(side=RIGHT, padx=2)
        
        ttk.Button(
            self.tree_action_frame,
            text="📂 全部展开",
            command=self._expand_all_tree,
            bootstyle="primary-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        ttk.Button(
            self.tree_action_frame,
            text="📁 全部收缩",
            command=self._collapse_all_tree,
            bootstyle="primary-outline",
            width=10
        ).pack(side=LEFT, padx=2)
        
        # 搜索结果缓存（用于上一个/下一个导航）
        self.search_results_cache = []
        self.search_result_index = -1
        
        # 树形视图搜索结果缓存（独立于表格搜索）
        self.tree_search_results = []
        self.tree_search_index = -1
        
        # 当前搜索的标签页类型
        self.current_search_tab_type = None
        
        # 在数据一览标签页中创建二级Notebook
        self.main_sub_notebook = ttk.Notebook(main_tab_frame)
        self.main_sub_notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # 绑定标签页切换事件
        self.main_sub_notebook.bind("<<NotebookTabChanged>>", self._on_sub_tab_changed)
        
        # 创建"全部对话"子标签页
        overview_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(overview_frame, text="💬 全部对话")
        
        # 在全部对话子标签页中创建树形视图
        tree_controller = TreeViewController(overview_frame, self.app)
        
        self.tabs["overview"] = {
            "type": "tree",
            "controller": tree_controller,
            "frame": overview_frame,
            "columns": [("#0", "名称", 280), ("type", "类型", 60), ("topics", "主题数", 70), ("messages", "消息数", 70), ("time", "时间", 150), ("id", "ID", 100)]
        }
        
        # 创建"全部模型"子标签页
        models_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(models_frame, text="🤖 全部模型")
        models_controller = ModelsTableViewController(models_frame, self.app)
        self.tabs["models_view"] = {
            "type": "table",
            "controller": models_controller,
            "frame": models_frame,
            "columns": models_controller.COLUMNS
        }
        
        # 创建"提供商"子标签页
        providers_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(providers_frame, text="🏢 提供商")
        providers_controller = ProvidersTableViewController(providers_frame, self.app)
        self.tabs["providers_view"] = {
            "type": "table",
            "controller": providers_controller,
            "frame": providers_frame,
            "columns": providers_controller.COLUMNS
        }
        
        # 创建"助手表"子标签页
        agents_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(agents_frame, text="🧑‍💼 助手表")
        agents_controller = AgentsTableViewController(agents_frame, self.app)
        self.tabs["agents_view"] = {
            "type": "table",
            "controller": agents_controller,
            "frame": agents_frame,
            "columns": agents_controller.COLUMNS
        }
        
        # 创建"主题表"子标签页
        topics_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(topics_frame, text="📝 主题表")
        topics_controller = TopicsTableViewController(topics_frame, self.app)
        self.tabs["topics_view"] = {
            "type": "table",
            "controller": topics_controller,
            "frame": topics_frame,
            "columns": topics_controller.COLUMNS
        }
        
        # 创建"消息表"子标签页
        messages_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(messages_frame, text="💭 消息表")
        messages_controller = MessagesTableViewController(messages_frame, self.app)
        self.tabs["messages_view"] = {
            "type": "table",
            "controller": messages_controller,
            "frame": messages_frame,
            "columns": messages_controller.COLUMNS
        }
        
        # 创建"搜索结果"子标签页
        search_frame = ttk.Frame(self.main_sub_notebook)
        self.main_sub_notebook.add(search_frame, text="🔍 搜索结果")
        self.search_results_table = SearchResultsTable(search_frame, self.app)
        self.search_results_table.pack(fill=BOTH, expand=YES)
        self.tabs["search_results"] = {
            "type": "search_results",
            "controller": self.search_results_table,
            "frame": search_frame,
            "columns": [("source", "来源表", 100), ("column", "匹配列", 100), ("match", "匹配内容", 200), ("context", "上下文", 400)]
        }
    
    def _on_sub_tab_changed(self, event):
        """子标签页切换事件"""
        try:
            tab_index = self.main_sub_notebook.index(self.main_sub_notebook.select())
            tab_keys = ["overview", "models_view", "providers_view", "agents_view", "topics_view", "messages_view", "search_results"]
            
            if tab_index < len(tab_keys):
                current_key = tab_keys[tab_index]
                tab_info = self.tabs.get(current_key, {})
                columns = tab_info.get("columns", [])
                
                # 更新搜索工具栏的列选项
                if columns:
                    col_names = [col[1] for col in columns if col[0] != "#0"]
                    self.search_toolbar.update_columns(col_names)
        except:
            pass
    
    def _on_select_entire_row_changed(self):
        """选中整行开关变化回调"""
        select_entire_row = self.select_entire_row_var.get()
        
        # 表格视图列表（不包含全部对话树形框）
        table_keys = ["models_view", "providers_view", "agents_view", "topics_view", "messages_view"]
        
        for key in table_keys:
            if key in self.tabs:
                tab_info = self.tabs[key]
                if tab_info["type"] == "table":
                    controller = tab_info["controller"]
                    controller.set_select_entire_row(select_entire_row)
        
        mode_text = "整行选择" if select_entire_row else "单元格选择"
        self.app.log_message(f"已切换到{mode_text}模式", "INFO")
    
    def _on_search(self, keyword: str, columns: List[str], full_text: bool):
        """
        搜索回调（定位功能）- 在当前视图中定位到第一个匹配项
        
        Args:
            keyword: 搜索关键词
            columns: 选中的列列表（支持多选）
            full_text: 是否搜索全部对话文本
        """
        if not keyword:
            self.app.log_message("请输入搜索关键词", "INFO")
            return
        
        columns_str = ", ".join(columns) if columns else "全部列"
        self.app.log_message(f"定位: {keyword}, 列: {columns_str}, 全文: {full_text}", "INFO")
        
        # 获取当前标签页
        try:
            tab_index = self.main_sub_notebook.index(self.main_sub_notebook.select())
            tab_keys = ["overview", "models_view", "providers_view", "agents_view", "topics_view", "messages_view", "search_results"]
            current_key = tab_keys[tab_index] if tab_index < len(tab_keys) else None
        except:
            current_key = None
        
        # 全部对话搜索 - 在树形视图中定位
        if current_key == "overview":
            self._search_tree_view_and_cache(keyword, full_text)
            self.current_search_tab_type = "tree"
            return
        
        # 表格搜索 - 在当前表格中定位第一个匹配项
        if current_key and current_key in self.tabs:
            tab_info = self.tabs[current_key]
            if tab_info["type"] == "table":
                tree = tab_info["controller"].tree
                
                # 如果是主题表且勾选了全文搜索，使用全文搜索并在主题表中定位
                if current_key == "topics_view" and full_text:
                    results = self._search_topics_full_text_for_locate(keyword)
                # 如果是助手表且勾选了全文搜索，搜索该助手下所有消息的内容
                elif current_key == "agents_view" and full_text:
                    results = self._search_agents_full_text_for_locate(keyword)
                else:
                    results = self._search_table(
                        tree,
                        tab_info["columns"],
                        keyword,
                        columns,
                        current_key
                    )
                
                if results:
                    # 缓存搜索结果用于导航
                    self.search_results_cache = results
                    self.search_result_index = 0
                    self.current_search_tab_type = "table"
                    self._current_search_tab_key = current_key
                    
                    # 在当前表格中定位到第一个匹配项
                    first_item_id = results[0].get("item_id", "")
                    if first_item_id:
                        # 对于主题表全文搜索，需要在表格中找到对应的 Treeview item
                        if current_key == "topics_view" and full_text:
                            # 通过 topic_id 在表格中查找对应行
                            for item in tree.get_children():
                                values = tree.item(item, "values")
                                # 第3列是 topic_id
                                if len(values) > 2 and values[2] == first_item_id:
                                    tree.selection_set(item)
                                    tree.focus(item)
                                    tree.see(item)
                                    break
                        # 对于助手表全文搜索，需要在表格中找到对应的 Treeview item
                        elif current_key == "agents_view" and full_text:
                            # 通过 agent_id 在表格中查找对应行
                            for item in tree.get_children():
                                values = tree.item(item, "values")
                                # 第2列是 agent_id
                                if len(values) > 1 and values[1] == first_item_id:
                                    tree.selection_set(item)
                                    tree.focus(item)
                                    tree.see(item)
                                    break
                        else:
                            tree.selection_set(first_item_id)
                            tree.focus(first_item_id)
                            tree.see(first_item_id)
                    
                    self.app.log_message(f"找到 {len(results)} 条匹配，已定位到第1条", "SUCCESS")
                else:
                    self.search_results_cache = []
                    self.search_result_index = -1
                    self.app.log_message("未找到匹配结果", "INFO")
    
    def _search_tree_view(self, keyword: str, full_text: bool):
        """
        搜索树形视图并定位（兼容旧接口）
        """
        self._search_tree_view_and_cache(keyword, full_text)
    
    def _search_tree_view_and_cache(self, keyword: str, full_text: bool):
        """
        搜索树形视图并定位，同时缓存所有匹配项用于导航
        
        Args:
            keyword: 搜索关键词
            full_text: 是否搜索全部对话文本（包括未展开的消息内容）
        """
        if "overview" not in self.tabs:
            return
        
        tree = self.tabs["overview"]["controller"].tree
        keyword_lower = keyword.lower()
        
        # 收集所有匹配项
        matched_items = []
        
        # 遍历所有项目查找匹配（包括未展开的子项）
        def search_items(parent=''):
            for item in tree.get_children(parent):
                # 获取项目文本和值
                text = tree.item(item, "text").lower()
                values = tree.item(item, "values")
                
                # 检查是否匹配
                matched = keyword_lower in text
                if not matched and values:
                    for val in values:
                        if keyword_lower in str(val).lower():
                            matched = True
                            break
                
                if matched:
                    matched_items.append(item)
                
                # 递归搜索子项（即使未展开也要搜索）
                search_items(item)
        
        search_items()
        
        # 缓存搜索结果
        self.tree_search_results = matched_items
        self.tree_search_index = 0 if matched_items else -1
        
        if matched_items:
            # 定位到第一个匹配项
            first_item = matched_items[0]
            self._expand_to_item(tree, first_item)
            tree.selection_set(first_item)
            tree.focus(first_item)
            tree.see(first_item)
            self.app.log_message(f"找到 {len(matched_items)} 条匹配，已定位到: {tree.item(first_item, 'text')}", "SUCCESS")
        else:
            # 如果勾选了全文搜索，再搜索原始消息数据
            if full_text and self.parsed_data:
                found_in_messages = self._search_tree_full_text(keyword_lower)
                if found_in_messages:
                    return
            self.app.log_message("在全部对话中未找到匹配项", "INFO")
    
    def _search_tree_full_text(self, keyword_lower: str) -> bool:
        """
        搜索树形视图的全部文本内容（包括原始消息数据）
        
        Args:
            keyword_lower: 小写的搜索关键词
            
        Returns:
            是否找到匹配项
        """
        if not self.parsed_data:
            return False
        
        raw_data = self.parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        topics = raw_data.get("data", {}).get("topics", [])
        
        # 建立话题字典
        topics_dict = {topic.get("id"): topic for topic in topics}
        
        # 搜索消息内容
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and keyword_lower in content.lower():
                topic_id = msg.get("topicId")
                
                # 尝试在树形视图中定位到对应的话题或消息
                if topic_id:
                    topic = topics_dict.get(topic_id)
                    if topic:
                        topic_title = topic.get("title", "")
                        # 在树形视图中搜索这个话题
                        if self._locate_topic_in_tree(topic_id, topic_title):
                            self.app.log_message(f"在消息内容中找到匹配，已定位到话题: {topic_title}", "SUCCESS")
                            return True
        
        return False
    
    def _locate_topic_in_tree(self, topic_id: str, topic_title: str) -> bool:
        """
        在树形视图中定位到指定话题
        
        Args:
            topic_id: 话题ID
            topic_title: 话题标题
            
        Returns:
            是否成功定位
        """
        if "overview" not in self.tabs:
            return False
        
        tree = self.tabs["overview"]["controller"].tree
        
        def find_topic(parent=''):
            for item in tree.get_children(parent):
                values = tree.item(item, "values")
                text = tree.item(item, "text")
                
                # 检查是否是目标话题
                if values and len(values) > 3:
                    item_id = values[3] if len(values) > 3 else ""
                    if item_id == topic_id or (topic_title and topic_title in text):
                        self._expand_to_item(tree, item)
                        tree.selection_set(item)
                        tree.focus(item)
                        tree.see(item)
                        return True
                
                # 递归搜索子项
                if find_topic(item):
                    return True
            
            return False
        
        return find_topic()
    
    def _expand_to_item(self, tree, item):
        """展开到指定项目的所有父节点"""
        parent = tree.parent(item)
        if parent:
            self._expand_to_item(tree, parent)
            tree.item(parent, open=True)
    
    def _search_table(self, tree, columns, keyword: str, selected_columns: List[str], source: str) -> List[Dict]:
        """
        搜索表格（支持多列搜索）
        
        Args:
            tree: Treeview组件
            columns: 列配置列表
            keyword: 搜索关键词
            selected_columns: 选中的列名列表
            source: 来源表名
            
        Returns:
            搜索结果列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        # 获取列索引
        col_indices = []
        if "全部列" in selected_columns or not selected_columns:
            col_indices = list(range(len(columns)))
        else:
            for i, col in enumerate(columns):
                if col[1] in selected_columns:
                    col_indices.append(i)
        
        # 遍历所有行
        for item in tree.get_children():
            values = tree.item(item, "values")
            
            matched = False
            for col_idx in col_indices:
                if col_idx < len(values):
                    value = str(values[col_idx])
                    if keyword_lower in value.lower():
                        matched = True
                        break
            
            if matched:
                results.append({
                    "source": source,
                    "values": values,
                    "item_id": item
                })
        
        return results
    
    def _search_messages_full_text(self, keyword: str, selected_columns: List[str], source_columns: List[tuple]) -> List[Dict]:
        """
        搜索消息的全部文本内容（不仅是预览）
        
        Args:
            keyword: 搜索关键词
            selected_columns: 选中的列名列表
            source_columns: 源表列配置
            
        Returns:
            搜索结果列表
        """
        results = []
        keyword_lower = keyword.lower()
        
        if not self.parsed_data:
            return results
        
        raw_data = self.parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
        from .table_views import get_agent_display_name
        from ..utils.file_utils import format_datetime
        
        # 建立助手字典
        agents_dict = {agent.get("id"): agent for agent in agents}
        
        # 建立话题字典
        topics_dict = {topic.get("id"): topic for topic in topics}
        
        # 建立会话到助手的映射
        session_to_agent = {}
        for rel in agents_to_sessions:
            agent_id = rel.get("agentId")
            session_id = rel.get("sessionId")
            if agent_id and session_id:
                session_to_agent[session_id] = agent_id
        
        # 找出没有sessionId的孤立话题
        orphan_topic_ids = set()
        for topic in topics:
            if not topic.get("sessionId"):
                orphan_topic_ids.add(topic.get("id"))
        
        # 找到默认助手
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        for msg in messages:
            content = msg.get("content", "")
            
            # 搜索全部内容
            if isinstance(content, str) and keyword_lower in content.lower():
                session_id = msg.get("sessionId")
                topic_id = msg.get("topicId")
                
                # 确定所属助手
                agent_name = "-"
                if session_id and session_id in session_to_agent:
                    agent_id = session_to_agent[session_id]
                    agent = agents_dict.get(agent_id)
                    if agent:
                        agent_name = get_agent_display_name(agent)
                elif topic_id and topic_id in orphan_topic_ids:
                    if default_agent_id:
                        agent = agents_dict.get(default_agent_id)
                        if agent:
                            agent_name = get_agent_display_name(agent)
                
                # 确定所属话题
                topic_title = "-"
                if topic_id and topic_id in topics_dict:
                    topic = topics_dict[topic_id]
                    title = topic.get("title", "")
                    if len(title) > 30:
                        title = title[:30] + "..."
                    topic_title = title or "未命名话题"
                
                # 生成内容预览
                preview = content.strip().replace("\n", " ")[:60]
                if len(content) > 60:
                    preview += "..."
                
                metadata = msg.get("metadata") or {}
                total_tokens = metadata.get("totalTokens", 0) or 0
                cost = metadata.get("cost", 0) or 0
                tps = metadata.get("tps", 0) or 0
                
                # 构建与消息表相同的值列表
                values = (
                    msg.get("role", "-"),
                    preview or "(空)",
                    agent_name,
                    topic_title,
                    msg.get("model", "-"),
                    total_tokens if total_tokens > 0 else "-",
                    f"${cost:.4f}" if cost > 0 else "-",
                    f"{tps:.1f}" if tps > 0 else "-",
                    topic_id or "-",
                    format_datetime(msg.get("createdAt")) or "-",
                )
                
                results.append({
                    "source": "messages_view",
                    "values": values,
                    "item_id": msg.get("id", "")
                })
        
        return results
    
    def _search_topics_full_text(self, keyword: str, selected_columns: List[str], source_columns: List[tuple]) -> List[Dict]:
        """
        搜索主题表的全文内容（搜索该主题下所有消息的内容）
        
        Args:
            keyword: 搜索关键词
            selected_columns: 选中的列名列表
            source_columns: 源表列配置
            
        Returns:
            搜索结果列表（包含匹配消息的主题）
        """
        results = []
        keyword_lower = keyword.lower()
        
        if not self.parsed_data:
            return results
        
        raw_data = self.parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
        from .table_views import get_agent_display_name
        from ..utils.file_utils import format_datetime
        from datetime import datetime
        
        # 建立助手字典
        agents_dict = {agent.get("id"): agent for agent in agents}
        
        # 建立话题字典
        topics_dict = {topic.get("id"): topic for topic in topics}
        
        # 建立会话到助手的映射
        session_to_agent = {}
        for rel in agents_to_sessions:
            agent_id = rel.get("agentId")
            session_id = rel.get("sessionId")
            if agent_id and session_id:
                session_to_agent[session_id] = agent_id
        
        # 找出没有sessionId的孤立话题
        orphan_topic_ids = set()
        for topic in topics:
            if not topic.get("sessionId"):
                orphan_topic_ids.add(topic.get("id"))
        
        # 找到默认助手
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        # 统计每个话题下匹配的消息数和总消息数、Token等统计
        topic_stats = {}
        
        for msg in messages:
            topic_id = msg.get("topicId")
            if not topic_id or topic_id not in topics_dict:
                continue
            
            if topic_id not in topic_stats:
                topic_stats[topic_id] = {
                    "msg_count": 0,
                    "matched_count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "call_dates": set()
                }
            
            stats = topic_stats[topic_id]
            stats["msg_count"] += 1
            
            # 检查消息内容是否匹配
            content = msg.get("content", "")
            if isinstance(content, str) and keyword_lower in content.lower():
                stats["matched_count"] += 1
            
            # 统计 Token 和费用
            if msg.get("role") == "assistant":
                metadata = msg.get("metadata") or {}
                stats["total_cost"] += metadata.get("cost", 0) or 0
                stats["total_tokens"] += metadata.get("totalTokens", 0) or 0
                stats["input_tokens"] += metadata.get("totalInputTokens", 0) or metadata.get("inputTextTokens", 0) or 0
                stats["output_tokens"] += metadata.get("totalOutputTokens", 0) or metadata.get("outputTextTokens", 0) or 0
                
                created_at = msg.get("createdAt")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        stats["call_dates"].add(dt.strftime("%Y-%m-%d"))
                    except:
                        pass
        
        # 构建包含匹配消息的主题结果列表
        for topic in topics:
            topic_id = topic.get("id", "")
            stats = topic_stats.get(topic_id)
            
            # 只返回包含匹配消息的主题
            if not stats or stats["matched_count"] == 0:
                continue
            
            session_id = topic.get("sessionId")
            title = topic.get("title", "")
            
            # 截断过长的标题
            if len(title) > 50:
                title = title[:50] + "..."
            
            # 确定所属助手
            agent_name = "-"
            if session_id and session_id in session_to_agent:
                agent_id = session_to_agent[session_id]
                agent = agents_dict.get(agent_id)
                if agent:
                    agent_name = get_agent_display_name(agent)
            elif not session_id:
                # 没有sessionId的话题属于默认助手
                if default_agent_id:
                    agent = agents_dict.get(default_agent_id)
                    if agent:
                        agent_name = get_agent_display_name(agent)
            
            # 构建与主题表相同的值列表
            values = (
                title or "未命名话题",
                agent_name,
                topic_id,
                session_id or "-",
                stats["msg_count"],
                stats["total_tokens"] if stats["total_tokens"] > 0 else "-",
                stats["input_tokens"] if stats["input_tokens"] > 0 else "-",
                stats["output_tokens"] if stats["output_tokens"] > 0 else "-",
                f"${stats['total_cost']:.4f}" if stats['total_cost'] > 0 else "-",
                len(stats["call_dates"]),
                "★" if topic.get("favorite") else "",
                format_datetime(topic.get("createdAt")) or "-",
                format_datetime(topic.get("updatedAt")) or "-",
            )
            
            results.append({
                "source": "topics_view",
                "values": values,
                "item_id": topic_id
            })
        
        return results
    
    def _search_agents_full_text(self, keyword: str, selected_columns: List[str], source_columns: List[tuple]) -> List[Dict]:
        """
        搜索助手表的全文内容（搜索该助手下所有消息的内容）
        
        Args:
            keyword: 搜索关键词
            selected_columns: 选中的列名列表
            source_columns: 源表列配置
            
        Returns:
            搜索结果列表（包含匹配消息的助手）
        """
        results = []
        keyword_lower = keyword.lower()
        
        if not self.parsed_data:
            return results
        
        raw_data = self.parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
        from .table_views import get_agent_display_name
        from ..utils.file_utils import format_datetime
        from datetime import datetime
        
        # 建立助手字典
        agents_dict = {agent.get("id"): agent for agent in agents}
        
        # 建立会话到助手的映射
        session_to_agent = {}
        agent_sessions = {}  # agent_id -> set of session_ids
        for rel in agents_to_sessions:
            agent_id = rel.get("agentId")
            session_id = rel.get("sessionId")
            if agent_id and session_id:
                session_to_agent[session_id] = agent_id
                if agent_id not in agent_sessions:
                    agent_sessions[agent_id] = set()
                agent_sessions[agent_id].add(session_id)
        
        # 找出没有sessionId的孤立话题
        orphan_topic_ids = set()
        for topic in topics:
            if not topic.get("sessionId"):
                orphan_topic_ids.add(topic.get("id"))
        
        # 找到默认助手
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        # 统计每个助手下的消息统计
        agent_stats = {}
        
        for msg in messages:
            session_id = msg.get("sessionId")
            topic_id = msg.get("topicId")
            
            # 确定消息所属的助手
            agent_id = None
            if session_id and session_id in session_to_agent:
                agent_id = session_to_agent[session_id]
            elif topic_id and topic_id in orphan_topic_ids:
                agent_id = default_agent_id
            elif not session_id and not topic_id:
                agent_id = default_agent_id
            
            if not agent_id:
                continue
            
            if agent_id not in agent_stats:
                agent_stats[agent_id] = {
                    "msg_count": 0,
                    "matched_count": 0,
                    "topic_count": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "call_dates": set()
                }
            
            stats = agent_stats[agent_id]
            stats["msg_count"] += 1
            
            # 检查消息内容是否匹配
            content = msg.get("content", "")
            if isinstance(content, str) and keyword_lower in content.lower():
                stats["matched_count"] += 1
            
            # 统计 Token 和费用
            if msg.get("role") == "assistant":
                metadata = msg.get("metadata") or {}
                stats["total_cost"] += metadata.get("cost", 0) or 0
                stats["total_tokens"] += metadata.get("totalTokens", 0) or 0
                stats["input_tokens"] += metadata.get("totalInputTokens", 0) or metadata.get("inputTextTokens", 0) or 0
                stats["output_tokens"] += metadata.get("totalOutputTokens", 0) or metadata.get("outputTextTokens", 0) or 0
                
                created_at = msg.get("createdAt")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        stats["call_dates"].add(dt.strftime("%Y-%m-%d"))
                    except:
                        pass
        
        # 统计每个会话的话题数
        session_topics = {}
        for topic in topics:
            session_id = topic.get("sessionId")
            if session_id:
                if session_id not in session_topics:
                    session_topics[session_id] = 0
                session_topics[session_id] += 1
        
        # 计算每个助手的话题数
        for agent_id, stats in agent_stats.items():
            topic_count = 0
            for session_id in agent_sessions.get(agent_id, set()):
                topic_count += session_topics.get(session_id, 0)
            if agent_id == default_agent_id:
                topic_count += len(orphan_topic_ids)
            stats["topic_count"] = topic_count
        
        # 构建包含匹配消息的助手结果列表
        for agent in agents:
            agent_id = agent.get("id", "")
            stats = agent_stats.get(agent_id)
            
            # 只返回包含匹配消息的助手
            if not stats or stats["matched_count"] == 0:
                continue
            
            # 构建与助手表相同的值列表
            values = (
                get_agent_display_name(agent),
                agent_id,
                agent.get("model", "-"),
                agent.get("provider", "-"),
                stats["topic_count"],
                stats["msg_count"],
                f"${stats['total_cost']:.4f}" if stats['total_cost'] > 0 else "-",
                stats["total_tokens"] if stats["total_tokens"] > 0 else "-",
                stats["input_tokens"] if stats["input_tokens"] > 0 else "-",
                stats["output_tokens"] if stats["output_tokens"] > 0 else "-",
                len(stats["call_dates"]),
                format_datetime(agent.get("createdAt")) or "-",
                format_datetime(agent.get("accessedAt")) or "-",
            )
            
            results.append({
                "source": "agents_view",
                "values": values,
                "item_id": agent_id
            })
        
        return results
    
    def _search_agents_full_text_for_locate(self, keyword: str) -> List[Dict]:
        """
        搜索助手表的全文内容用于定位（搜索该助手下所有消息的内容）
        返回 agent_id 作为 item_id，用于在助手表中定位
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表（包含匹配消息的助手，item_id 为 agent_id）
        """
        results = []
        keyword_lower = keyword.lower()
        
        if not self.parsed_data:
            return results
        
        raw_data = self.parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
        # 建立会话到助手的映射
        session_to_agent = {}
        for rel in agents_to_sessions:
            agent_id = rel.get("agentId")
            session_id = rel.get("sessionId")
            if agent_id and session_id:
                session_to_agent[session_id] = agent_id
        
        # 找出没有sessionId的孤立话题
        orphan_topic_ids = set()
        for topic in topics:
            if not topic.get("sessionId"):
                orphan_topic_ids.add(topic.get("id"))
        
        # 找到默认助手
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        # 找出包含匹配消息的助手ID
        matched_agent_ids = set()
        
        for msg in messages:
            session_id = msg.get("sessionId")
            topic_id = msg.get("topicId")
            
            # 确定消息所属的助手
            agent_id = None
            if session_id and session_id in session_to_agent:
                agent_id = session_to_agent[session_id]
            elif topic_id and topic_id in orphan_topic_ids:
                agent_id = default_agent_id
            elif not session_id and not topic_id:
                agent_id = default_agent_id
            
            if not agent_id:
                continue
            
            # 检查消息内容是否匹配
            content = msg.get("content", "")
            if isinstance(content, str) and keyword_lower in content.lower():
                matched_agent_ids.add(agent_id)
        
        # 为每个匹配的助手创建结果
        for agent in agents:
            agent_id = agent.get("id", "")
            if agent_id not in matched_agent_ids:
                continue
            
            results.append({
                "source": "agents_view",
                "values": (),  # 定位功能不需要 values
                "item_id": agent_id  # 使用 agent_id 作为 item_id
            })
        
        return results
    
    def _search_topics_full_text_for_locate(self, keyword: str) -> List[Dict]:
        """
        搜索主题表的全文内容用于定位（搜索该主题下所有消息的内容）
        返回 topic_id 作为 item_id，用于在主题表中定位
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            搜索结果列表（包含匹配消息的主题，item_id 为 topic_id）
        """
        results = []
        keyword_lower = keyword.lower()
        
        if not self.parsed_data:
            return results
        
        raw_data = self.parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        topics = raw_data.get("data", {}).get("topics", [])
        
        # 建立话题字典
        topics_dict = {topic.get("id"): topic for topic in topics}
        
        # 找出包含匹配消息的主题ID
        matched_topic_ids = set()
        
        for msg in messages:
            topic_id = msg.get("topicId")
            if not topic_id or topic_id not in topics_dict:
                continue
            
            # 检查消息内容是否匹配
            content = msg.get("content", "")
            if isinstance(content, str) and keyword_lower in content.lower():
                matched_topic_ids.add(topic_id)
        
        # 为每个匹配的主题创建结果
        for topic in topics:
            topic_id = topic.get("id", "")
            if topic_id not in matched_topic_ids:
                continue
            
            results.append({
                "source": "topics_view",
                "values": (),  # 定位功能不需要 values
                "item_id": topic_id  # 使用 topic_id 作为 item_id
            })
        
        return results
    
    def _on_export(self, export_type: str):
        """导出回调"""
        if not self.parsed_data:
            messagebox.showwarning("警告", "请先加载数据！")
            return
        
        # 获取当前标签页
        try:
            tab_index = self.main_sub_notebook.index(self.main_sub_notebook.select())
            tab_keys = ["overview", "models_view", "providers_view", "agents_view", "topics_view", "messages_view", "search_results"]
            current_key = tab_keys[tab_index] if tab_index < len(tab_keys) else None
        except:
            current_key = None
        
        if export_type == "csv":
            self._export_current_table_csv(current_key)
        elif export_type == "excel":
            self._export_current_table_excel(current_key)
        elif export_type == "all_excel":
            self._export_all_tables_excel()
    
    def _export_current_table_csv(self, current_key: str):
        """导出当前表格为CSV"""
        if not current_key or current_key not in self.tabs:
            messagebox.showwarning("警告", "请选择一个表格！")
            return
        
        tab_info = self.tabs[current_key]
        if tab_info["type"] not in ["table", "search_results"]:
            messagebox.showwarning("警告", "当前视图不支持CSV导出！")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="导出CSV",
            defaultextension=".csv",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")],
            initialfile=f"{current_key}.csv"
        )
        
        if not file_path:
            return
        
        try:
            tree = tab_info["controller"].tree if tab_info["type"] == "table" else tab_info["controller"].tree
            columns = tab_info["columns"]
            export_table_to_csv(tree, columns, file_path)
            self.app.log_message(f"✅ CSV导出成功: {file_path}", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出到:\n{file_path}")
        except Exception as e:
            self.app.log_message(f"CSV导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def _export_current_table_excel(self, current_key: str):
        """导出当前表格为Excel"""
        if not current_key or current_key not in self.tabs:
            messagebox.showwarning("警告", "请选择一个表格！")
            return
        
        tab_info = self.tabs[current_key]
        if tab_info["type"] not in ["table", "search_results"]:
            messagebox.showwarning("警告", "当前视图不支持Excel导出！")
            return
        
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="导出Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile=f"{current_key}.xlsx"
        )
        
        if not file_path:
            return
        
        try:
            tree = tab_info["controller"].tree if tab_info["type"] == "table" else tab_info["controller"].tree
            columns = tab_info["columns"]
            export_table_to_excel(tree, columns, file_path, current_key)
            self.app.log_message(f"✅ Excel导出成功: {file_path}", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出到:\n{file_path}")
        except ImportError:
            messagebox.showerror("导出失败", "需要安装openpyxl库:\npip install openpyxl")
        except Exception as e:
            self.app.log_message(f"Excel导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def _export_all_tables_excel(self):
        """导出所有表格为Excel（包含搜索结果）"""
        # 选择保存路径
        file_path = filedialog.asksaveasfilename(
            title="导出所有表格",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            initialfile="lobechat_all_tables.xlsx"
        )
        
        if not file_path:
            return
        
        try:
            # 收集所有表格数据
            tables_data = {}
            table_names = {
                "models_view": "全部模型",
                "providers_view": "提供商",
                "agents_view": "助手表",
                "topics_view": "主题表",
                "messages_view": "消息表"
            }
            
            for key, name in table_names.items():
                if key in self.tabs:
                    tab_info = self.tabs[key]
                    if tab_info["type"] == "table":
                        tables_data[name] = {
                            "tree": tab_info["controller"].tree,
                            "columns": tab_info["columns"]
                        }
            
            # 添加搜索结果表（如果有数据）
            if "search_results" in self.tabs:
                search_tab_info = self.tabs["search_results"]
                search_tree = search_tab_info["controller"].tree
                # 只在搜索结果表有数据时添加
                if search_tree.get_children():
                    tables_data["搜索结果"] = {
                        "tree": search_tree,
                        "columns": search_tab_info["columns"]
                    }
            
            export_all_tables_to_excel(tables_data, file_path)
            self.app.log_message(f"✅ 所有表格导出成功: {file_path}", "SUCCESS")
            messagebox.showinfo("导出成功", f"已导出 {len(tables_data)} 个表格到:\n{file_path}")
        except ImportError:
            messagebox.showerror("导出失败", "需要安装openpyxl库:\npip install openpyxl")
        except Exception as e:
            self.app.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def _create_other_tabs(self):
        """创建其他数据模块标签页（包含所有JSON编辑器）"""
        # 其他数据容器
        other_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(other_tab_frame, text="📂 其他数据")
        
        # 在其他数据标签页中创建二级Notebook
        self.other_notebook = ttk.Notebook(other_tab_frame)
        self.other_notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # 创建所有JSON编辑器选项卡
        for module in MODULES_CONFIG:
            if module["category"] == "other":
                self._create_json_tab(
                    module["key"],
                    module["label"],
                    module["required"]
                )
    
    def _create_json_tab(self, module_key: str, module_label: str, is_required: bool):
        """创建JSON编辑器选项卡（在二级标签页中）"""
        tab_frame = ttk.Frame(self.other_notebook)
        
        # 图标选择
        icon = "⚙️" if is_required else "📦"
        self.other_notebook.add(tab_frame, text=f"{icon} {module_label}")
        
        # 创建JSON编辑器
        editor = JSONEditor(
            tab_frame,
            module_key,
            module_label,
            is_required,
            on_change=self._on_module_changed
        )
        editor.pack(fill=BOTH, expand=YES)
        
        self.tabs[module_key] = {
            "type": "json",
            "editor": editor,
            "frame": tab_frame
        }
    
    def _create_export_tab(self):
        """创建全部导出标签页（包含Markdown导出和JSON导出子标签页）"""
        # 全部导出容器
        export_tab_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(export_tab_frame, text="📦 全部导出")
        
        # 创建二级Notebook
        self.export_notebook = ttk.Notebook(export_tab_frame)
        self.export_notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # 创建Markdown导出子标签页
        self._create_markdown_export_tab()
        
        # 创建JSON导出子标签页
        self._create_json_export_tab()
    
    def _create_markdown_export_tab(self):
        """创建Markdown导出子标签页"""
        md_frame = ttk.Frame(self.export_notebook)
        self.export_notebook.add(md_frame, text="📝 Markdown导出")
        
        # 导出模式选择
        mode_frame = ttk.LabelFrame(md_frame, text="导出模式", padding=15)
        mode_frame.pack(fill=X, padx=20, pady=10)
        
        self.md_export_mode = tk.StringVar(value="topic_file")
        
        modes = [
            ("single_file", "📑 全部为一个文件", "all.md - 所有对话合并为一个文件"),
            ("agent_file", "📚 每个助手一个文件", "助手.md - 每个助手的所有对话合并为一个文件"),
            ("topic_file", "📄 每个主题一个文件", "助手/主题.md - 每个主题的所有对话合并为一个文件"),
            ("message_file", "📝 每个对话一个文件", "助手/主题/对话.md - 每条对话单独一个文件（三级目录）"),
        ]
        
        for value, label, desc in modes:
            frame = ttk.Frame(mode_frame)
            frame.pack(fill=X, pady=2)
            
            rb = ttk.Radiobutton(
                frame,
                text=label,
                variable=self.md_export_mode,
                value=value,
                bootstyle="primary"
            )
            rb.pack(side=LEFT)
            
            ttk.Label(frame, text=f"  - {desc}", foreground="gray").pack(side=LEFT)
        
        # 导出选项
        options_frame = ttk.LabelFrame(md_frame, text="导出选项", padding=15)
        options_frame.pack(fill=X, padx=20, pady=10)
        
        self.md_include_metadata = tk.BooleanVar(value=True)
        self.md_include_system_prompt = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(
            options_frame,
            text="包含元数据（时间、模型、Token等）",
            variable=self.md_include_metadata,
            bootstyle="primary-round-toggle"
        ).pack(anchor=W, pady=2)
        
        ttk.Checkbutton(
            options_frame,
            text="包含系统提示词",
            variable=self.md_include_system_prompt,
            bootstyle="primary-round-toggle"
        ).pack(anchor=W, pady=2)
        
        # 导出按钮
        btn_frame = ttk.Frame(md_frame)
        btn_frame.pack(fill=X, padx=20, pady=20)
        
        ttk.Button(
            btn_frame,
            text="📝 导出Markdown",
            command=self._export_markdown,
            bootstyle="success",
            width=20
        ).pack(side=LEFT, padx=10)
    
    def _create_json_export_tab(self):
        """创建JSON导出子标签页"""
        json_frame = ttk.Frame(self.export_notebook)
        self.export_notebook.add(json_frame, text="📦 JSON导出")
        
        # 标题
        ttk.Label(
            json_frame,
            text="📦 导出为JSON格式",
            font=("", 14, "bold")
        ).pack(pady=(20, 10))
        
        # 说明
        ttk.Label(
            json_frame,
            text="选择要导出的数据模块，导出为可重新导入LobeChat的JSON格式",
            font=("", 10)
        ).pack(pady=(0, 20))
        
        # 模块选择区域
        modules_frame = ttk.LabelFrame(json_frame, text="📋 选择导出模块", padding=15)
        modules_frame.pack(fill=BOTH, expand=YES, padx=20, pady=10)
        
        # 创建多列布局的复选框
        row_frame = None
        col_count = 0
        max_cols = 3
        
        for module in sorted([m for m in MODULES_CONFIG if m["in_export"]], key=lambda x: x["order"]):
            module_key = module["key"]
            module_label = module["label"]
            is_required = module["required"]
            
            # 每3个一行
            if col_count % max_cols == 0:
                row_frame = ttk.Frame(modules_frame)
                row_frame.pack(fill=X, pady=5)
            
            # 创建启用变量（默认全选）
            var = tk.BooleanVar(value=True)
            self.module_vars[module_key] = var
            
            # 复选框 - 所有都可以点击
            label_text = f"{module_label}" + (" ⭐" if is_required else "")
            cb = ttk.Checkbutton(
                row_frame,
                text=label_text,
                variable=var,
                bootstyle="primary-round-toggle"
            )
            cb.pack(side=LEFT, padx=15)
            
            col_count += 1
        
        # 快捷按钮区域
        quick_btn_frame = ttk.Frame(modules_frame)
        quick_btn_frame.pack(fill=X, pady=(15, 0))
        
        ttk.Button(
            quick_btn_frame,
            text="✅ 全选",
            command=self._select_all_modules,
            bootstyle="info-outline",
            width=12
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            quick_btn_frame,
            text="❌ 全不选",
            command=self._deselect_all_modules,
            bootstyle="info-outline",
            width=12
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            quick_btn_frame,
            text="⭐ 仅必需",
            command=self._select_required_only,
            bootstyle="info-outline",
            width=12
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            quick_btn_frame,
            text="🔧 仅配置",
            command=self._select_config_only,
            bootstyle="info-outline",
            width=12
        ).pack(side=LEFT, padx=5)
        
        # 导出按钮区域
        export_btn_frame = ttk.Frame(json_frame)
        export_btn_frame.pack(fill=X, padx=20, pady=20)
        
        ttk.Button(
            export_btn_frame,
            text="🚀 导出完整JSON",
            command=self.export_full_json,
            bootstyle="success",
            width=20
        ).pack(side=LEFT, padx=10)
        
        ttk.Button(
            export_btn_frame,
            text="📋 复制当前选项卡JSON",
            command=self.copy_current_tab,
            bootstyle="info",
            width=20
        ).pack(side=LEFT, padx=10)
    
    def _export_markdown(self):
        """导出Markdown"""
        if self.app:
            self.app.export_markdown()
    
    def _select_config_only(self):
        """仅选择配置相关模块"""
        config_modules = {"userSettings", "aiProviders", "aiModels", "agents"}
        for module_key, var in self.module_vars.items():
            var.set(module_key in config_modules)
        self.app.log_message("已选择配置相关模块", "INFO")
    
    def update_data(self, parsed_data: Dict):
        """
        更新所有选项卡数据
        
        Args:
            parsed_data: 解析后的数据
        """
        self.parsed_data = parsed_data
        
        # 保存原始元数据
        raw_data = parsed_data.get("raw", {})
        self.original_mode = raw_data.get("mode", "postgres")
        self.original_schema_hash = raw_data.get("schemaHash", "")
        
        original_data = raw_data.get("data", {})
        
        # 更新综合视图
        if "overview" in self.tabs:
            tree_controller = self.tabs["overview"]["controller"]
            tree_controller.update_tree(parsed_data)
        
        # 更新各模块JSON编辑器
        for module_key, tab_info in self.tabs.items():
            if tab_info["type"] == "json":
                editor = tab_info["editor"]
                module_data = original_data.get(module_key, [])
                editor.set_data(module_data)
        
        # 更新表格视图
        for module_key, tab_info in self.tabs.items():
            if tab_info["type"] == "table":
                controller = tab_info["controller"]
                controller.update_table(parsed_data)
        
        # 解析完成后自动重置所有视图列宽
        self.parent.after(100, self._reset_all_views)
        
        self.app.log_message("✅ 所有选项卡数据已更新", "SUCCESS")
    
    def get_export_data(self) -> Dict:
        """
        获取导出数据（按选中模块和顺序）
        
        Returns:
            导出的完整JSON数据
        """
        export_data = {}
        
        # 按order顺序遍历模块
        for module in sorted([m for m in MODULES_CONFIG if m["in_export"]], key=lambda x: x["order"]):
            module_key = module["key"]
            
            # 检查是否启用
            if module_key not in self.module_vars:
                continue
            
            if not self.module_vars[module_key].get():
                continue
            
            # 获取模块数据
            try:
                module_data = self._get_module_data(module_key)
                if module_data is not None:
                    export_data[module_key] = module_data
            except Exception as e:
                self.app.log_message(f"获取 {module_key} 数据失败: {str(e)}", "ERROR")
                raise
        
        return {
            "mode": self.original_mode,
            "schemaHash": self.original_schema_hash,
            "data": export_data
        }
    
    def _get_module_data(self, module_key: str) -> Any:
        """获取单个模块的数据"""
        if module_key not in self.tabs:
            return None
        
        tab_info = self.tabs[module_key]
        
        if tab_info["type"] == "json":
            editor = tab_info["editor"]
            return editor.get_data()
        
        return None
    
    def export_full_json(self):
        """导出完整JSON文件"""
        if not self.parsed_data:
            messagebox.showwarning("警告", "请先解析JSON文件！")
            return
        
        # 检查是否至少选择一个模块
        selected_count = sum(1 for var in self.module_vars.values() if var.get())
        if selected_count == 0:
            messagebox.showwarning("警告", "请至少选择一个模块！")
            return
        
        # 选择保存文件
        source_filename = self.parsed_data.get("sourceFileName", "lobechat_backup")
        default_filename = source_filename.replace(".json", "") + "_export.json"
        
        file_path = filedialog.asksaveasfilename(
            title="保存JSON文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile=default_filename
        )
        
        if not file_path:
            return
        
        self.app.log_message(f"开始导出JSON，已选择 {selected_count} 个模块...", "INFO")
        
        try:
            # 验证所有模块数据
            self._validate_all_modules()
            
            # 获取导出数据
            export_data = self.get_export_data()
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            # 统计信息
            data_stats = export_data.get("data", {})
            stats_msg = "\n".join([
                f"- {self.modules_dict.get(k, {}).get('label', k)}: {len(v) if isinstance(v, list) else 1} 项"
                for k, v in data_stats.items()
            ])
            
            self.app.log_message(f"✅ JSON导出成功: {file_path}", "SUCCESS")
            messagebox.showinfo(
                "导出成功",
                f"已导出包含 {len(data_stats)} 个模块的JSON文件\n\n{stats_msg}\n\n文件路径:\n{file_path}"
            )
            
        except ValueError as e:
            self.app.log_message(f"数据验证失败: {str(e)}", "ERROR")
            messagebox.showerror("验证失败", f"数据格式错误:\n{str(e)}\n\n请检查并修复后重试。")
        except Exception as e:
            self.app.log_message(f"导出失败: {str(e)}", "ERROR")
            messagebox.showerror("导出失败", str(e))
    
    def copy_current_tab(self):
        """复制当前选项卡的JSON数据到剪贴板"""
        # 检查当前是在主标签页还是其他数据标签页
        main_tab_index = self.main_notebook.index(self.main_notebook.select())
        
        if main_tab_index == 0:
            # 在"全部对话"标签页
            self.app.log_message("全部对话视图不支持复制，请使用右键菜单功能", "INFO")
            return
        
        # 在"其他数据"标签页，获取二级标签页的当前选项
        if not hasattr(self, 'other_notebook'):
            return
        
        try:
            other_tab_index = self.other_notebook.index(self.other_notebook.select())
            # 获取其他数据模块列表（按order排序）
            other_modules = [m for m in MODULES_CONFIG if m["category"] == "other"]
            other_modules.sort(key=lambda x: x["order"])
            
            if other_tab_index >= len(other_modules):
                return
            
            current_module = other_modules[other_tab_index]
            module_key = current_module["key"]
            
            if module_key not in self.tabs:
                return
            
            tab_info = self.tabs[module_key]
            
            if tab_info["type"] == "json":
                editor = tab_info["editor"]
                data = editor.get_data()
                json_str = json.dumps(data, indent=2, ensure_ascii=False)
                
                self.app.clipboard_manager.copy_text(json_str)
                self.app.log_message(f"✅ 已复制 {current_module['label']} 的JSON数据", "SUCCESS")
                
        except Exception as e:
            self.app.log_message(f"复制失败: {str(e)}", "ERROR")
            messagebox.showerror("复制失败", str(e))
    
    def _validate_all_modules(self):
        """验证所有启用模块的数据格式"""
        for module_key, var in self.module_vars.items():
            if not var.get():
                continue
            
            if module_key in self.tabs:
                tab_info = self.tabs[module_key]
                if tab_info["type"] == "json":
                    editor = tab_info["editor"]
                    try:
                        # 尝试获取数据，会自动验证JSON格式
                        editor.get_data()
                    except ValueError as e:
                        module_label = self.modules_dict[module_key]["label"]
                        raise ValueError(f"{module_label}: {str(e)}")
    
    def _select_all_modules(self):
        """全选所有模块"""
        for module_key, var in self.module_vars.items():
            var.set(True)
        self.app.log_message("已全选所有模块", "INFO")
    
    def _deselect_all_modules(self):
        """取消选择所有模块"""
        for module_key, var in self.module_vars.items():
            var.set(False)
        self.app.log_message("已取消选择所有模块", "INFO")
    
    def _select_required_only(self):
        """仅选择必需模块"""
        for module_key, var in self.module_vars.items():
            module = self.modules_dict.get(module_key, {})
            is_required = module.get("required", False)
            var.set(is_required)
        self.app.log_message("已选择仅必需模块", "INFO")
    
    def _on_module_changed(self, module_key: str):
        """模块数据变更回调"""
        module_label = self.modules_dict.get(module_key, {}).get("label", module_key)
        # 可以在这里添加自动保存等功能
        pass
    
    def _on_search_all(self, keyword: str, columns: List[str], full_text: bool):
        """
        搜索全部回调 - 搜索所有匹配项并显示在搜索结果表格中
        
        Args:
            keyword: 搜索关键词
            columns: 选中的列列表
            full_text: 是否搜索全部对话文本
        """
        if not keyword:
            self.app.log_message("请输入搜索关键词", "INFO")
            return
        
        # 获取当前标签页
        try:
            tab_index = self.main_sub_notebook.index(self.main_sub_notebook.select())
            tab_keys = ["overview", "models_view", "providers_view", "agents_view", "topics_view", "messages_view", "search_results"]
            current_key = tab_keys[tab_index] if tab_index < len(tab_keys) else None
        except:
            current_key = None
        
        # 全部对话不支持搜索全部
        if current_key == "overview":
            self.app.log_message("全部对话视图不支持搜索全部，请使用定位功能", "INFO")
            return
        
        results = []
        source_columns = []
        
        # 表格搜索
        if current_key and current_key in self.tabs:
            tab_info = self.tabs[current_key]
            if tab_info["type"] == "table":
                source_columns = tab_info["columns"]
                
                # 如果是消息表且勾选了全文搜索，搜索原始消息内容
                if current_key == "messages_view" and full_text:
                    results = self._search_messages_full_text(keyword, columns, source_columns)
                # 如果是主题表且勾选了全文搜索，搜索该主题下所有消息的内容
                elif current_key == "topics_view" and full_text:
                    results = self._search_topics_full_text(keyword, columns, source_columns)
                # 如果是助手表且勾选了全文搜索，搜索该助手下所有消息的内容
                elif current_key == "agents_view" and full_text:
                    results = self._search_agents_full_text(keyword, columns, source_columns)
                else:
                    results = self._search_table(
                        tab_info["controller"].tree,
                        tab_info["columns"],
                        keyword,
                        columns,
                        current_key
                    )
        
        # 缓存搜索结果用于导航
        self.search_results_cache = results
        self.search_result_index = 0 if results else -1
        
        # 显示搜索结果
        if results:
            self.search_results_table.show_results(results, keyword, source_columns)
            # 切换到搜索结果标签页
            self.main_sub_notebook.select(6)
            self.app.log_message(f"找到 {len(results)} 条匹配结果", "SUCCESS")
        else:
            self.app.log_message("未找到匹配结果", "INFO")
    
    def _on_search_prev(self):
        """上一个搜索结果 - 根据当前搜索类型在相应视图中导航"""
        # 检查是否是树形视图搜索
        if self.current_search_tab_type == "tree" and self.tree_search_results:
            self._navigate_tree_prev()
            return
        
        # 表格搜索导航
        if not self.search_results_cache:
            self.app.log_message("没有搜索结果，请先进行搜索", "INFO")
            return
        
        if self.search_result_index > 0:
            self.search_result_index -= 1
        else:
            self.search_result_index = len(self.search_results_cache) - 1
        
        self._navigate_to_table_result(self.search_result_index)
    
    def _on_search_next(self):
        """下一个搜索结果 - 根据当前搜索类型在相应视图中导航"""
        # 检查是否是树形视图搜索
        if self.current_search_tab_type == "tree" and self.tree_search_results:
            self._navigate_tree_next()
            return
        
        # 表格搜索导航
        if not self.search_results_cache:
            self.app.log_message("没有搜索结果，请先进行搜索", "INFO")
            return
        
        if self.search_result_index < len(self.search_results_cache) - 1:
            self.search_result_index += 1
        else:
            self.search_result_index = 0
        
        self._navigate_to_table_result(self.search_result_index)
    
    def _navigate_tree_prev(self):
        """在树形视图中导航到上一个匹配项"""
        if not self.tree_search_results:
            return
        
        if self.tree_search_index > 0:
            self.tree_search_index -= 1
        else:
            self.tree_search_index = len(self.tree_search_results) - 1
        
        self._navigate_to_tree_item(self.tree_search_index)
    
    def _navigate_tree_next(self):
        """在树形视图中导航到下一个匹配项"""
        if not self.tree_search_results:
            return
        
        if self.tree_search_index < len(self.tree_search_results) - 1:
            self.tree_search_index += 1
        else:
            self.tree_search_index = 0
        
        self._navigate_to_tree_item(self.tree_search_index)
    
    def _navigate_to_tree_item(self, index: int):
        """
        在树形视图中导航到指定索引的匹配项
        
        Args:
            index: 结果索引
        """
        if index < 0 or index >= len(self.tree_search_results):
            return
        
        if "overview" not in self.tabs:
            return
        
        tree = self.tabs["overview"]["controller"].tree
        item = self.tree_search_results[index]
        
        # 展开父节点并定位
        self._expand_to_item(tree, item)
        tree.selection_set(item)
        tree.focus(item)
        tree.see(item)
        
        self.app.log_message(f"第 {index + 1}/{len(self.tree_search_results)} 条: {tree.item(item, 'text')}", "INFO")
    
    def _navigate_to_table_result(self, index: int):
        """
        在表格中导航到指定索引的搜索结果
        
        Args:
            index: 结果索引
        """
        if index < 0 or index >= len(self.search_results_cache):
            return
        
        result = self.search_results_cache[index]
        source = result.get("source", "")
        item_id = result.get("item_id", "")
        
        # 如果有当前搜索的表格key，在该表格中定位
        if hasattr(self, '_current_search_tab_key') and self._current_search_tab_key in self.tabs:
            tab_info = self.tabs[self._current_search_tab_key]
            if tab_info["type"] == "table":
                tree = tab_info["controller"].tree
                if item_id:
                    # 对于主题表全文搜索，item_id 是 topic_id，需要在表格中查找对应行
                    if self._current_search_tab_key == "topics_view" and item_id.startswith("tpc_"):
                        for item in tree.get_children():
                            values = tree.item(item, "values")
                            # 第3列是 topic_id
                            if len(values) > 2 and values[2] == item_id:
                                tree.selection_set(item)
                                tree.focus(item)
                                tree.see(item)
                                break
                    # 对于助手表全文搜索，item_id 是 agent_id，需要在表格中查找对应行
                    elif self._current_search_tab_key == "agents_view":
                        found = False
                        for item in tree.get_children():
                            values = tree.item(item, "values")
                            # 第2列是 agent_id
                            if len(values) > 1 and values[1] == item_id:
                                tree.selection_set(item)
                                tree.focus(item)
                                tree.see(item)
                                found = True
                                break
                        if found:
                            pass  # 已找到
                        else:
                            # 尝试直接使用 item_id
                            try:
                                tree.selection_set(item_id)
                                tree.focus(item_id)
                                tree.see(item_id)
                            except:
                                pass
                    else:
                        try:
                            tree.selection_set(item_id)
                            tree.focus(item_id)
                            tree.see(item_id)
                        except:
                            pass
        
        self.app.log_message(f"第 {index + 1}/{len(self.search_results_cache)} 条结果", "INFO")
    
    def _navigate_to_search_result(self, index: int):
        """
        导航到指定索引的搜索结果（兼容旧接口）
        """
        self._navigate_to_table_result(index)
    
    def _reset_all_views(self):
        """重置所有视图的列宽（解析数据后自动调用）"""
        try:
            # 获取可用宽度
            self.parent.update_idletasks()
            available_width = self.parent.winfo_width() - 60  # 减去边距
            if available_width < 400:
                available_width = 800  # 默认宽度
            
            tab_keys = ["overview", "models_view", "providers_view", "agents_view", "topics_view", "messages_view"]
            
            for current_key in tab_keys:
                if current_key not in self.tabs:
                    continue
                
                tab_info = self.tabs[current_key]
                columns = tab_info.get("columns", [])
                
                if not columns:
                    continue
                
                if tab_info["type"] == "tree":
                    tree = tab_info["controller"].tree
                    total_weight = sum(col[2] for col in columns)
                    if total_weight > 0:
                        for col in columns:
                            col_id = col[0]
                            col_width = int(available_width * col[2] / total_weight)
                            tree.column(col_id, width=col_width)
                
                elif tab_info["type"] == "table":
                    tree = tab_info["controller"].tree
                    total_weight = sum(col[2] for col in columns if len(col) > 2)
                    if total_weight > 0:
                        for col in columns:
                            col_id = col[0]
                            col_width = int(available_width * col[2] / total_weight) if len(col) > 2 else 100
                            tree.column(col_id, width=col_width)
            
            self.app.log_message("已重置所有视图列宽", "INFO")
            
        except Exception as e:
            self.app.log_message(f"重置所有视图失败: {str(e)}", "ERROR")
    
    def _reset_current_view(self):
        """重置当前视图的列宽"""
        try:
            tab_index = self.main_sub_notebook.index(self.main_sub_notebook.select())
            tab_keys = ["overview", "models_view", "providers_view", "agents_view", "topics_view", "messages_view", "search_results"]
            
            if tab_index >= len(tab_keys):
                return
            
            current_key = tab_keys[tab_index]
            tab_info = self.tabs.get(current_key, {})
            
            # 获取当前标签页的可用宽度
            frame = tab_info.get("frame")
            if frame:
                frame.update_idletasks()
                available_width = frame.winfo_width() - 30  # 减去滚动条和边距
            else:
                available_width = 800
            
            if tab_info["type"] == "tree":
                # 树形视图：重置列宽
                tree = tab_info["controller"].tree
                columns = tab_info.get("columns", [])
                
                # 按比例分配列宽
                total_weight = sum(col[2] for col in columns)
                for col in columns:
                    col_id = col[0]
                    col_width = int(available_width * col[2] / total_weight)
                    if col_id == "#0":
                        tree.column(col_id, width=col_width)
                    else:
                        tree.column(col_id, width=col_width)
                
                self.app.log_message("已重置全部对话视图列宽", "INFO")
                
            elif tab_info["type"] == "table":
                # 表格视图：重置列宽
                tree = tab_info["controller"].tree
                columns = tab_info.get("columns", [])
                
                # 按比例分配列宽
                total_weight = sum(col[2] for col in columns if len(col) > 2)
                if total_weight > 0:
                    for col in columns:
                        col_id = col[0]
                        col_width = int(available_width * col[2] / total_weight) if len(col) > 2 else 100
                        tree.column(col_id, width=col_width)
                
                self.app.log_message(f"已重置{MAIN_TAB_CONFIG[tab_index]['label']}列宽", "INFO")
                
            elif tab_info["type"] == "search_results":
                # 搜索结果表格：重置列宽
                controller = tab_info["controller"]
                tree = controller.tree
                columns = controller.current_columns  # 使用动态创建的列配置
                
                if columns:
                    # 按比例分配列宽
                    total_weight = sum(col[2] for col in columns if len(col) > 2)
                    if total_weight > 0:
                        for col in columns:
                            col_id = col[0]
                            col_width = int(available_width * col[2] / total_weight) if len(col) > 2 else 100
                            tree.column(col_id, width=col_width)
                
                self.app.log_message("已重置搜索结果表格列宽", "INFO")
                
        except Exception as e:
            self.app.log_message(f"表格适配失败: {str(e)}", "ERROR")
    
    def _expand_all_tree(self):
        """全部展开树形视图"""
        if "overview" not in self.tabs:
            return
        
        tree = self.tabs["overview"]["controller"].tree
        
        def expand_all(parent=''):
            for item in tree.get_children(parent):
                tree.item(item, open=True)
                expand_all(item)
        
        expand_all()
        self.app.log_message("已全部展开", "INFO")
    
    def _collapse_all_tree(self):
        """全部收缩树形视图"""
        if "overview" not in self.tabs:
            return
        
        tree = self.tabs["overview"]["controller"].tree
        
        def collapse_all(parent=''):
            for item in tree.get_children(parent):
                tree.item(item, open=False)
                collapse_all(item)
        
        collapse_all()
        self.app.log_message("已全部收缩", "INFO")
    
    def configure_theme(self, theme: str):
        """
        配置主题
        
        Args:
            theme: 主题名称
        """
        for tab_info in self.tabs.values():
            if tab_info["type"] == "json":
                editor = tab_info["editor"]
                editor.configure_theme(theme)
            elif tab_info["type"] == "tree":
                controller = tab_info["controller"]
                controller.configure_style(theme)
            elif tab_info["type"] == "table":
                controller = tab_info["controller"]
                controller.configure_style(theme)
