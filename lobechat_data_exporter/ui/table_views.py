"""
表格视图控制器
负责管理各种数据表格的显示和排序
包括：模型表、提供商表、助手表、话题表、消息表
支持单元格选择、多选和右键复制功能
"""

import tkinter as tk
from tkinter import ttk
from ttkbootstrap.constants import *
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from ..utils.file_utils import format_datetime
from ..config import THEME_DARK, THEME_LIGHT


# 助手名称映射表 - 与parser.py保持一致
AGENT_NAME_MAPPING = {
    "buffalo-under-own-plane": "随便聊聊",
}


def get_agent_display_name(agent: Dict) -> str:
    """获取助手的显示名称"""
    if not agent:
        return "未命名"
    
    # 检查slug是否在名称映射表中
    slug = agent.get("slug", "")
    if slug and slug in AGENT_NAME_MAPPING:
        return AGENT_NAME_MAPPING[slug]
    
    # 检查title
    title = agent.get("title", "")
    if title and title.strip():
        if title.strip() in AGENT_NAME_MAPPING:
            return AGENT_NAME_MAPPING[title.strip()]
        return title.strip()
    
    # 使用slug
    if slug and slug.strip():
        return slug.strip()
    
    return agent.get("id", "未命名")


class CellSelectionManager:
    """单元格选择管理器 - 处理单元格级别的选择、多选和复制"""
    
    def __init__(self, tree: ttk.Treeview, columns: List[tuple], app=None, parent_frame=None):
        """
        初始化单元格选择管理器
        
        Args:
            tree: Treeview组件
            columns: 列配置列表
            app: 主应用实例（用于日志和剪贴板）
            parent_frame: 父容器（用于创建Canvas覆盖层）
        """
        self.tree = tree
        self.columns = columns
        self.app = app
        self.parent_frame = parent_frame
        
        # 选择模式：True=整行选择，False=单元格选择
        self.select_entire_row = True
        
        # 选中的单元格集合：Set[(item_id, col_id)]
        self.selected_cells: Set[Tuple[str, str]] = set()
        
        # 用于SHIFT多选的锚点
        self.anchor_cell: Optional[Tuple[str, str]] = None
        
        # Canvas 覆盖层（用于单元格高亮）
        self.highlight_canvas = None
        self._highlight_rectangles = []
        
        # 绑定事件
        self._bind_events()
        
        # 创建右键菜单
        self._create_context_menu()
    
    def _bind_events(self):
        """绑定鼠标和键盘事件"""
        # 单击选择
        self.tree.bind("<Button-1>", self._on_click)
        # 右键菜单
        self.tree.bind("<Button-3>", self._on_right_click)
        # Ctrl+C 复制
        self.tree.bind("<Control-c>", self._on_copy)
        self.tree.bind("<Control-C>", self._on_copy)
    
    def _create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="📋 复制选中内容", command=self._copy_selected)
        self.context_menu.add_command(label="📋 复制选中行", command=self._copy_selected_rows)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✅ 全选当前列", command=self._select_column)
        self.context_menu.add_command(label="✅ 全选所有", command=self._select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ 清除选择", command=self._clear_selection)
    
    def set_select_entire_row(self, value: bool):
        """设置是否选择整行模式"""
        self.select_entire_row = value
        self._clear_selection()
    
    def _get_cell_at_position(self, x: int, y: int) -> Optional[Tuple[str, str]]:
        """
        获取指定位置的单元格
        
        Args:
            x: X坐标
            y: Y坐标
            
        Returns:
            (item_id, col_id) 或 None
        """
        # 获取行
        item = self.tree.identify_row(y)
        if not item:
            return None
        
        # 获取列
        col = self.tree.identify_column(x)
        if not col:
            return None
        
        # 转换列索引为列ID
        col_index = int(col.replace('#', '')) - 1
        if col_index < 0 or col_index >= len(self.columns):
            return None
        
        col_id = self.columns[col_index][0]
        return (item, col_id)
    
    def _on_click(self, event):
        """处理单击事件"""
        cell = self._get_cell_at_position(event.x, event.y)
        if not cell:
            return
        
        item, col_id = cell
        
        # 获取修饰键状态
        ctrl_pressed = event.state & 0x4  # Control键
        shift_pressed = event.state & 0x1  # Shift键
        
        if self.select_entire_row:
            # 整行选择模式 - 使用默认的Treeview行为
            # 不需要额外处理，让Treeview处理
            pass
        else:
            # 单元格选择模式
            if shift_pressed and self.anchor_cell:
                # Shift多选：选择从锚点到当前单元格的范围
                self._select_range(self.anchor_cell, cell)
            elif ctrl_pressed:
                # Ctrl多选：切换当前单元格的选中状态
                if cell in self.selected_cells:
                    self.selected_cells.discard(cell)
                else:
                    self.selected_cells.add(cell)
                    self.anchor_cell = cell
            else:
                # 普通点击：清除之前的选择，选中当前单元格
                self.selected_cells.clear()
                self.selected_cells.add(cell)
                self.anchor_cell = cell
            
            # 更新视觉高亮
            self._update_highlight()
            
            # 阻止默认的行选择行为
            return "break"
    
    def _select_range(self, start_cell: Tuple[str, str], end_cell: Tuple[str, str]):
        """
        选择从start_cell到end_cell的矩形范围内的所有单元格
        """
        # 获取所有行ID的列表
        all_items = list(self.tree.get_children())
        if not all_items:
            return
        
        try:
            start_row_idx = all_items.index(start_cell[0])
            end_row_idx = all_items.index(end_cell[0])
        except ValueError:
            return
        
        # 获取列索引
        col_ids = [col[0] for col in self.columns]
        try:
            start_col_idx = col_ids.index(start_cell[1])
            end_col_idx = col_ids.index(end_cell[1])
        except ValueError:
            return
        
        # 确保索引范围正确
        min_row, max_row = min(start_row_idx, end_row_idx), max(start_row_idx, end_row_idx)
        min_col, max_col = min(start_col_idx, end_col_idx), max(start_col_idx, end_col_idx)
        
        # 清除之前的选择并选中范围内的所有单元格
        self.selected_cells.clear()
        for row_idx in range(min_row, max_row + 1):
            item = all_items[row_idx]
            for col_idx in range(min_col, max_col + 1):
                col_id = col_ids[col_idx]
                self.selected_cells.add((item, col_id))
    
    def _update_highlight(self):
        """更新选中单元格的视觉高亮"""
        # 清除所有行的选择
        for item in self.tree.get_children():
            self.tree.selection_remove(item)
        
        # 高亮包含选中单元格的行（作为视觉反馈）
        # 注意：tkinter Treeview 只支持行级别高亮，无法实现真正的单元格高亮
        selected_rows = set(cell[0] for cell in self.selected_cells)
        for row in selected_rows:
            self.tree.selection_add(row)
        
        # 同时通过日志提示用户选中的具体单元格信息
        if self.selected_cells and self.app:
            col_ids = [col[0] for col in self.columns]
            selected_cols = set(cell[1] for cell in self.selected_cells)
            
            col_names = []
            for col_id in selected_cols:
                col_name = next((col[1] for col in self.columns if col[0] == col_id), col_id)
                col_names.append(col_name)
            
            if len(self.selected_cells) == 1:
                # 单个单元格：显示具体内容
                cell = list(self.selected_cells)[0]
                item, col_id = cell
                col_idx = col_ids.index(col_id) if col_id in col_ids else 0
                values = self.tree.item(item, "values")
                if col_idx < len(values):
                    value = str(values[col_idx])
                    if len(value) > 50:
                        value = value[:50] + "..."
                    col_name = col_names[0] if col_names else col_id
                    self.app.log_message(f"📌 单元格模式: [{col_name}] = {value}", "INFO")
            else:
                # 多个单元格：显示数量和列名
                cols_str = ", ".join(col_names[:3])
                if len(col_names) > 3:
                    cols_str += f" 等{len(col_names)}列"
                self.app.log_message(f"📌 单元格模式: 已选中 {len(self.selected_cells)} 个单元格 ({cols_str})", "INFO")
    
    def _on_right_click(self, event):
        """处理右键点击事件"""
        # 如果点击位置有单元格，确保它被选中
        cell = self._get_cell_at_position(event.x, event.y)
        
        if not self.select_entire_row and cell:
            # 单元格模式：如果点击的单元格不在选中集合中，则只选中该单元格
            if cell not in self.selected_cells:
                self.selected_cells.clear()
                self.selected_cells.add(cell)
                self.anchor_cell = cell
                self._update_highlight()
        
        # 记录当前右键点击的列（用于"全选当前列"功能）
        if cell:
            self._right_click_col = cell[1]
        else:
            self._right_click_col = None
        
        # 显示右键菜单
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def _on_copy(self, event):
        """处理Ctrl+C复制"""
        self._copy_selected()
        return "break"
    
    def _copy_selected(self):
        """复制选中的单元格内容（Tab分隔）"""
        if self.select_entire_row:
            # 整行模式：复制选中行的所有内容
            self._copy_selected_rows()
            return
        
        if not self.selected_cells:
            if self.app:
                self.app.log_message("没有选中任何单元格", "INFO")
            return
        
        # 按行和列排序选中的单元格
        all_items = list(self.tree.get_children())
        col_ids = [col[0] for col in self.columns]
        
        # 获取选中单元格的行列范围
        selected_rows = sorted(set(cell[0] for cell in self.selected_cells), 
                              key=lambda x: all_items.index(x) if x in all_items else 0)
        selected_cols = sorted(set(cell[1] for cell in self.selected_cells),
                              key=lambda x: col_ids.index(x) if x in col_ids else 0)
        
        # 构建复制内容
        lines = []
        for row in selected_rows:
            row_values = []
            values = self.tree.item(row, "values")
            for col_id in selected_cols:
                if (row, col_id) in self.selected_cells:
                    col_idx = col_ids.index(col_id)
                    if col_idx < len(values):
                        row_values.append(str(values[col_idx]))
                    else:
                        row_values.append("")
            lines.append("\t".join(row_values))
        
        text = "\n".join(lines)
        self._copy_to_clipboard(text)
        
        if self.app:
            self.app.log_message(f"已复制 {len(self.selected_cells)} 个单元格到剪贴板", "SUCCESS")
    
    def _copy_selected_rows(self):
        """复制选中行的所有内容（Tab分隔）"""
        if self.select_entire_row:
            # 整行模式：使用Treeview的选择
            selected_items = self.tree.selection()
        else:
            # 单元格模式：获取包含选中单元格的所有行
            selected_items = list(set(cell[0] for cell in self.selected_cells))
        
        if not selected_items:
            if self.app:
                self.app.log_message("没有选中任何行", "INFO")
            return
        
        # 按行在表格中的顺序排序
        all_items = list(self.tree.get_children())
        selected_items = sorted(selected_items, 
                               key=lambda x: all_items.index(x) if x in all_items else 0)
        
        lines = []
        for item in selected_items:
            values = self.tree.item(item, "values")
            lines.append("\t".join(str(v) for v in values))
        
        text = "\n".join(lines)
        self._copy_to_clipboard(text)
        
        if self.app:
            self.app.log_message(f"已复制 {len(selected_items)} 行到剪贴板", "SUCCESS")
    
    def _select_column(self):
        """全选当前列"""
        if not hasattr(self, '_right_click_col') or not self._right_click_col:
            return
        
        col_id = self._right_click_col
        self.selected_cells.clear()
        
        for item in self.tree.get_children():
            self.selected_cells.add((item, col_id))
        
        if self.selected_cells:
            self.anchor_cell = list(self.selected_cells)[0]
        
        self._update_highlight()
        
        if self.app:
            col_name = next((col[1] for col in self.columns if col[0] == col_id), col_id)
            self.app.log_message(f"已选中 '{col_name}' 列的所有单元格", "INFO")
    
    def _select_all(self):
        """全选所有单元格"""
        self.selected_cells.clear()
        
        for item in self.tree.get_children():
            for col in self.columns:
                self.selected_cells.add((item, col[0]))
        
        if self.selected_cells:
            self.anchor_cell = list(self.selected_cells)[0]
        
        self._update_highlight()
        
        if self.app:
            self.app.log_message(f"已选中所有 {len(self.selected_cells)} 个单元格", "INFO")
    
    def _clear_selection(self):
        """清除选择"""
        self.selected_cells.clear()
        self.anchor_cell = None
        
        # 清除Treeview的行选择
        for item in self.tree.get_children():
            self.tree.selection_remove(item)
        
        if self.app:
            self.app.log_message("已清除选择", "INFO")
    
    def _copy_to_clipboard(self, text: str):
        """复制文本到剪贴板"""
        if self.app and hasattr(self.app, 'clipboard_manager'):
            self.app.clipboard_manager.copy_text(text)
        else:
            # 直接使用tkinter的剪贴板
            self.tree.clipboard_clear()
            self.tree.clipboard_append(text)


class BaseTableViewController:
    """表格视图基类"""
    
    def __init__(self, parent, app, columns: List[tuple]):
        """
        初始化表格视图控制器
        
        Args:
            parent: 父容器
            app: 主应用实例
            columns: 列配置列表 [(列ID, 列标题, 宽度, 是否数值列), ...]
        """
        self.app = app
        self.columns = columns
        self.sort_column = None
        self.sort_reverse = False
        self.data_cache = []  # 缓存原始数据用于排序
        self.create_table(parent)
        
        # 初始化单元格选择管理器
        self.cell_selection_manager = CellSelectionManager(self.tree, columns, app)
    
    def create_table(self, parent):
        """创建表格视图"""
        # 表格容器
        table_container = ttk.Frame(parent)
        table_container.pack(fill=BOTH, expand=YES)
        
        # 滚动条
        scroll_y = ttk.Scrollbar(table_container, orient=VERTICAL)
        scroll_y.pack(side=RIGHT, fill=Y)
        
        scroll_x = ttk.Scrollbar(table_container, orient=HORIZONTAL)
        scroll_x.pack(side=BOTTOM, fill=X)
        
        # 提取列ID列表（不包含#0）
        col_ids = [col[0] for col in self.columns]
        
        # Treeview
        self.tree = ttk.Treeview(
            table_container,
            columns=col_ids,
            show="headings",  # 只显示表头，不显示树形结构
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            height=20
        )
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        
        scroll_y.config(command=self.tree.yview)
        scroll_x.config(command=self.tree.xview)
        
        # 配置列和绑定排序事件
        for col_id, col_title, col_width, is_numeric in self.columns:
            self.tree.heading(
                col_id, 
                text=col_title, 
                command=lambda c=col_id, n=is_numeric: self.sort_by_column(c, n)
            )
            self.tree.column(col_id, width=col_width, anchor=CENTER if is_numeric else W)
        
        # 配置样式
        self.configure_style(self.app.current_theme)
    
    def set_select_entire_row(self, value: bool):
        """设置是否选择整行模式"""
        if hasattr(self, 'cell_selection_manager'):
            self.cell_selection_manager.set_select_entire_row(value)
    
    def configure_style(self, theme):
        """配置表格样式"""
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
    
    def clear_table(self):
        """清空表格"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.data_cache = []
        
        # 清除单元格选择
        if hasattr(self, 'cell_selection_manager'):
            self.cell_selection_manager._clear_selection()
    
    def sort_by_column(self, col, is_numeric):
        """
        点击表头排序
        
        Args:
            col: 列标识
            is_numeric: 是否为数值列
        """
        # 判断是否需要反转排序
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        
        # 获取所有项
        items = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        
        if not items:
            return
        
        # 排序
        if is_numeric:
            # 数值排序
            def extract_number(item):
                value = item[0]
                try:
                    # 尝试提取数字（处理带单位的情况）
                    import re
                    numbers = re.findall(r'[-+]?\d*\.?\d+', str(value))
                    return float(numbers[0]) if numbers else 0
                except:
                    return 0
            
            items.sort(key=extract_number, reverse=self.sort_reverse)
        else:
            # 文本排序
            items.sort(key=lambda x: str(x[0]).lower(), reverse=self.sort_reverse)
        
        # 重新排列
        for index, (value, child_id) in enumerate(items):
            self.tree.move(child_id, '', index)
        
        # 更新表头显示排序状态
        for col_id, col_title, _, _ in self.columns:
            current_text = col_title
            if col_id == col:
                indicator = " ▼" if self.sort_reverse else " ▲"
                self.tree.heading(col_id, text=current_text + indicator)
            else:
                self.tree.heading(col_id, text=current_text)


class ModelsTableViewController(BaseTableViewController):
    """模型表视图控制器"""
    
    # 模型表列配置
    COLUMNS = [
        ("model_name", "模型名称", 200, False),
        ("call_count", "调用次数", 80, True),
        ("total_cost", "总开销", 100, True),
        ("avg_tps", "平均TPS", 80, True),
        ("total_tokens", "总Token", 100, True),
        ("input_tokens", "输入Token", 100, True),
        ("output_tokens", "输出Token", 100, True),
        ("first_call", "初次调用", 150, False),
        ("last_call", "最后调用", 150, False),
        ("usage_days", "使用天数", 80, True),
    ]
    
    def __init__(self, parent, app):
        """初始化模型表视图"""
        super().__init__(parent, app, self.COLUMNS)
    
    def update_table(self, parsed_data: Dict):
        """
        更新模型表数据
        
        Args:
            parsed_data: 解析后的数据
        """
        self.clear_table()
        
        if not parsed_data:
            return
        
        # 获取原始消息数据
        raw_data = parsed_data.get("raw", {})
        messages = raw_data.get("data", {}).get("messages", [])
        
        if not messages:
            return
        
        # 按模型聚合统计
        model_stats = self._aggregate_model_stats(messages)
        
        # 填充表格
        for model_name, stats in model_stats.items():
            self.tree.insert(
                "",
                "end",
                values=(
                    model_name,
                    stats["call_count"],
                    f"${stats['total_cost']:.4f}" if stats['total_cost'] > 0 else "-",
                    f"{stats['avg_tps']:.2f}" if stats['avg_tps'] > 0 else "-",
                    stats["total_tokens"],
                    stats["input_tokens"],
                    stats["output_tokens"],
                    stats["first_call"] or "-",
                    stats["last_call"] or "-",
                    stats["usage_days"]
                )
            )
    
    def _aggregate_model_stats(self, messages: List[Dict]) -> Dict[str, Dict]:
        """
        聚合模型统计数据
        
        Args:
            messages: 消息列表
            
        Returns:
            模型统计字典
        """
        model_stats = defaultdict(lambda: {
            "call_count": 0,
            "total_cost": 0.0,
            "total_tps": 0.0,
            "tps_count": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "first_call_dt": None,
            "last_call_dt": None,
            "first_call": None,
            "last_call": None,
            "usage_days": 0,
            "call_dates": set()
        })
        
        for msg in messages:
            # 只统计assistant角色的消息（有模型调用）
            if msg.get("role") != "assistant":
                continue
            
            model = msg.get("model")
            if not model:
                continue
            
            stats = model_stats[model]
            metadata = msg.get("metadata") or {}
            
            # 调用次数
            stats["call_count"] += 1
            
            # 费用统计
            cost = metadata.get("cost", 0) or 0
            stats["total_cost"] += cost
            
            # TPS统计
            tps = metadata.get("tps", 0) or 0
            if tps > 0:
                stats["total_tps"] += tps
                stats["tps_count"] += 1
            
            # Token统计
            total_tokens = metadata.get("totalTokens", 0) or 0
            input_tokens = metadata.get("totalInputTokens", 0) or metadata.get("inputTextTokens", 0) or 0
            output_tokens = metadata.get("totalOutputTokens", 0) or metadata.get("outputTextTokens", 0) or 0
            
            stats["total_tokens"] += total_tokens
            stats["input_tokens"] += input_tokens
            stats["output_tokens"] += output_tokens
            
            # 时间统计
            created_at = msg.get("createdAt")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                    stats["call_dates"].add(date_str)
                    
                    if stats["first_call_dt"] is None or dt < stats["first_call_dt"]:
                        stats["first_call_dt"] = dt
                        stats["first_call"] = dt.strftime("%Y-%m-%d %H:%M")
                    
                    if stats["last_call_dt"] is None or dt > stats["last_call_dt"]:
                        stats["last_call_dt"] = dt
                        stats["last_call"] = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    pass
        
        # 计算平均TPS和使用天数
        for model, stats in model_stats.items():
            if stats["tps_count"] > 0:
                stats["avg_tps"] = stats["total_tps"] / stats["tps_count"]
            else:
                stats["avg_tps"] = 0
            
            stats["usage_days"] = len(stats["call_dates"])
        
        return dict(model_stats)


class ProvidersTableViewController(BaseTableViewController):
    """提供商表视图控制器"""
    
    # 提供商表列配置 - 增加统计列
    COLUMNS = [
        ("provider_name", "提供商名称", 150, False),
        ("provider_id", "提供商ID", 120, False),
        ("enabled", "启用状态", 80, False),
        ("source", "来源", 80, False),
        ("sdk_type", "SDK类型", 100, False),
        ("model_count", "模型数量", 80, True),
        ("total_cost", "总开销", 100, True),
        ("total_tokens", "总Token", 100, True),
        ("input_tokens", "输入Token", 100, True),
        ("output_tokens", "输出Token", 100, True),
        ("created_at", "创建时间", 150, False),
        ("updated_at", "更新时间", 150, False),
    ]
    
    def __init__(self, parent, app):
        """初始化提供商表视图"""
        super().__init__(parent, app, self.COLUMNS)
    
    def update_table(self, parsed_data: Dict):
        """更新提供商表数据"""
        self.clear_table()
        
        if not parsed_data:
            return
        
        raw_data = parsed_data.get("raw", {})
        providers = raw_data.get("data", {}).get("aiProviders", [])
        models = raw_data.get("data", {}).get("aiModels", [])
        messages = raw_data.get("data", {}).get("messages", [])
        
        # 统计每个提供商的模型数量
        provider_model_count = defaultdict(int)
        for model in models:
            provider_id = model.get("providerId")
            if provider_id:
                provider_model_count[provider_id] += 1
        
        # 统计每个提供商的消息统计（通过消息中的provider字段）
        provider_stats = defaultdict(lambda: {
            "total_cost": 0.0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0
        })
        
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            
            provider = msg.get("provider")
            if not provider:
                continue
            
            metadata = msg.get("metadata") or {}
            stats = provider_stats[provider]
            
            stats["total_cost"] += metadata.get("cost", 0) or 0
            stats["total_tokens"] += metadata.get("totalTokens", 0) or 0
            stats["input_tokens"] += metadata.get("totalInputTokens", 0) or metadata.get("inputTextTokens", 0) or 0
            stats["output_tokens"] += metadata.get("totalOutputTokens", 0) or metadata.get("outputTextTokens", 0) or 0
        
        for provider in providers:
            provider_id = provider.get("id", "")
            settings = provider.get("settings", {}) or {}
            stats = provider_stats.get(provider_id, {})
            
            self.tree.insert(
                "",
                "end",
                values=(
                    provider.get("name", "") or provider_id,
                    provider_id,
                    "✓ 启用" if provider.get("enabled") else "✗ 禁用",
                    provider.get("source", "-"),
                    settings.get("sdkType", "-"),
                    provider_model_count.get(provider_id, 0),
                    f"${stats.get('total_cost', 0):.4f}" if stats.get('total_cost', 0) > 0 else "-",
                    stats.get("total_tokens", 0) if stats.get("total_tokens", 0) > 0 else "-",
                    stats.get("input_tokens", 0) if stats.get("input_tokens", 0) > 0 else "-",
                    stats.get("output_tokens", 0) if stats.get("output_tokens", 0) > 0 else "-",
                    format_datetime(provider.get("createdAt")) or "-",
                    format_datetime(provider.get("updatedAt")) or "-",
                )
            )


class AgentsTableViewController(BaseTableViewController):
    """助手表视图控制器"""
    
    # 助手表列配置 - 增加统计列
    COLUMNS = [
        ("agent_name", "助手名称", 180, False),
        ("agent_id", "助手ID", 150, False),
        ("model", "使用模型", 200, False),
        ("provider", "提供商", 100, False),
        ("topic_count", "话题数", 80, True),
        ("msg_count", "消息数", 80, True),
        ("total_cost", "总开销", 100, True),
        ("total_tokens", "总Token", 100, True),
        ("input_tokens", "输入Token", 100, True),
        ("output_tokens", "输出Token", 100, True),
        ("usage_days", "使用天数", 80, True),
        ("created_at", "创建时间", 150, False),
        ("accessed_at", "最后访问", 150, False),
    ]
    
    def __init__(self, parent, app):
        """初始化助手表视图"""
        super().__init__(parent, app, self.COLUMNS)
    
    def update_table(self, parsed_data: Dict):
        """更新助手表数据"""
        self.clear_table()
        
        if not parsed_data:
            return
        
        raw_data = parsed_data.get("raw", {})
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        messages = raw_data.get("data", {}).get("messages", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
        # 建立助手到会话的映射
        agent_sessions = defaultdict(set)
        session_to_agent = {}  # 会话ID到助手ID的映射
        for rel in agents_to_sessions:
            agent_id = rel.get("agentId")
            session_id = rel.get("sessionId")
            if agent_id and session_id:
                agent_sessions[agent_id].add(session_id)
                session_to_agent[session_id] = agent_id
        
        # 统计每个会话的话题
        session_topics = defaultdict(set)
        for topic in topics:
            session_id = topic.get("sessionId")
            if session_id:
                session_topics[session_id].add(topic.get("id"))
        
        # 找出没有sessionId的孤立话题，它们属于默认助手（buffalo-under-own-plane）
        orphan_topic_ids = set()
        for topic in topics:
            if not topic.get("sessionId"):
                orphan_topic_ids.add(topic.get("id"))
        
        # 找到默认助手（slug为buffalo-under-own-plane的助手）
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        # 统计每个助手的消息统计
        agent_stats = defaultdict(lambda: {
            "msg_count": 0,
            "topic_count": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "call_dates": set()
        })
        
        for msg in messages:
            session_id = msg.get("sessionId")
            topic_id = msg.get("topicId")
            
            # 确定消息所属的助手
            agent_id = None
            if session_id and session_id in session_to_agent:
                agent_id = session_to_agent[session_id]
            elif topic_id and topic_id in orphan_topic_ids:
                # 孤立话题的消息属于默认助手
                agent_id = default_agent_id
            elif not session_id and not topic_id:
                # 没有session和topic的消息也归属默认助手
                agent_id = default_agent_id
            
            if not agent_id:
                continue
            
            stats = agent_stats[agent_id]
            stats["msg_count"] += 1
            
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
        
        # 计算每个助手的话题数
        for agent in agents:
            agent_id = agent.get("id")
            stats = agent_stats[agent_id]
            
            # 计算话题数
            topic_count = 0
            for session_id in agent_sessions.get(agent_id, set()):
                topic_count += len(session_topics.get(session_id, set()))
            
            # 如果是默认助手，加上孤立话题数
            if agent_id == default_agent_id:
                topic_count += len(orphan_topic_ids)
            
            stats["topic_count"] = topic_count
        
        for agent in agents:
            agent_id = agent.get("id", "")
            stats = agent_stats[agent_id]
            
            self.tree.insert(
                "",
                "end",
                values=(
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
            )


class TopicsTableViewController(BaseTableViewController):
    """话题表视图控制器"""
    
    # 话题表列配置 - 增加统计列
    COLUMNS = [
        ("topic_title", "话题标题", 250, False),
        ("agent_name", "所属助手", 120, False),
        ("topic_id", "话题ID", 150, False),
        ("session_id", "会话ID", 150, False),
        ("msg_count", "消息数", 80, True),
        ("total_tokens", "总Token", 100, True),
        ("input_tokens", "输入Token", 100, True),
        ("output_tokens", "输出Token", 100, True),
        ("total_cost", "总开销", 100, True),
        ("usage_days", "使用天数", 80, True),
        ("favorite", "收藏", 60, False),
        ("created_at", "创建时间", 150, False),
        ("updated_at", "更新时间", 150, False),
    ]
    
    def __init__(self, parent, app):
        """初始化话题表视图"""
        super().__init__(parent, app, self.COLUMNS)
    
    def update_table(self, parsed_data: Dict):
        """更新话题表数据"""
        self.clear_table()
        
        if not parsed_data:
            return
        
        raw_data = parsed_data.get("raw", {})
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        messages = raw_data.get("data", {}).get("messages", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
        # 建立助手字典
        agents_dict = {agent.get("id"): agent for agent in agents}
        
        # 建立会话到助手的映射
        session_to_agent = {}
        for rel in agents_to_sessions:
            agent_id = rel.get("agentId")
            session_id = rel.get("sessionId")
            if agent_id and session_id:
                session_to_agent[session_id] = agent_id
        
        # 找到默认助手（slug为buffalo-under-own-plane的助手）
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        # 统计每个话题的消息统计
        topic_stats = defaultdict(lambda: {
            "msg_count": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "call_dates": set()
        })
        
        for msg in messages:
            topic_id = msg.get("topicId")
            if not topic_id:
                continue
            
            stats = topic_stats[topic_id]
            stats["msg_count"] += 1
            
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
        
        for topic in topics:
            topic_id = topic.get("id", "")
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
            
            stats = topic_stats.get(topic_id, {})
            
            self.tree.insert(
                "",
                "end",
                values=(
                    title or "未命名话题",
                    agent_name,
                    topic_id,
                    session_id or "-",
                    stats.get("msg_count", 0),
                    stats.get("total_tokens", 0) if stats.get("total_tokens", 0) > 0 else "-",
                    stats.get("input_tokens", 0) if stats.get("input_tokens", 0) > 0 else "-",
                    stats.get("output_tokens", 0) if stats.get("output_tokens", 0) > 0 else "-",
                    f"${stats.get('total_cost', 0):.4f}" if stats.get('total_cost', 0) > 0 else "-",
                    len(stats.get("call_dates", set())),
                    "★" if topic.get("favorite") else "",
                    format_datetime(topic.get("createdAt")) or "-",
                    format_datetime(topic.get("updatedAt")) or "-",
                )
            )


class MessagesTableViewController(BaseTableViewController):
    """消息表视图控制器"""
    
    # 消息表列配置 - 增加所属助手和所属话题列
    COLUMNS = [
        ("role", "角色", 80, False),
        ("content_preview", "内容预览", 250, False),
        ("agent_name", "所属助手", 120, False),
        ("topic_title", "所属话题", 150, False),
        ("model", "模型", 150, False),
        ("tokens", "Token数", 80, True),
        ("cost", "费用", 80, True),
        ("tps", "TPS", 60, True),
        ("topic_id", "话题ID", 150, False),
        ("created_at", "创建时间", 150, False),
    ]
    
    def __init__(self, parent, app):
        """初始化消息表视图"""
        super().__init__(parent, app, self.COLUMNS)
    
    def update_table(self, parsed_data: Dict):
        """更新消息表数据"""
        self.clear_table()
        
        if not parsed_data:
            return
        
        raw_data = parsed_data.get("raw", {})
        agents = raw_data.get("data", {}).get("agents", [])
        topics = raw_data.get("data", {}).get("topics", [])
        messages = raw_data.get("data", {}).get("messages", [])
        agents_to_sessions = raw_data.get("data", {}).get("agentsToSessions", [])
        
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
        
        # 找到默认助手（slug为buffalo-under-own-plane的助手）
        default_agent_id = None
        for agent in agents:
            if agent.get("slug") == "buffalo-under-own-plane" or not agent.get("title"):
                default_agent_id = agent.get("id")
                break
        
        for msg in messages:
            content = msg.get("content", "")
            # 生成内容预览
            if isinstance(content, str):
                preview = content.strip().replace("\n", " ")[:60]
                if len(content) > 60:
                    preview += "..."
            else:
                preview = str(content)[:60] + "..."
            
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
                # 孤立话题的消息属于默认助手
                if default_agent_id:
                    agent = agents_dict.get(default_agent_id)
                    if agent:
                        agent_name = get_agent_display_name(agent)
            elif not session_id and not topic_id:
                # 没有session和topic的消息也归属默认助手
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
            
            metadata = msg.get("metadata") or {}
            total_tokens = metadata.get("totalTokens", 0) or 0
            cost = metadata.get("cost", 0) or 0
            tps = metadata.get("tps", 0) or 0
            
            self.tree.insert(
                "",
                "end",
                values=(
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
            )
