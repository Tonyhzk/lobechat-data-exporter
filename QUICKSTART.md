# 快速开始指南 🚀

## 5分钟上手 LobeChat 数据导出工具

### 第一步：安装

```bash
# 1. 克隆项目
git clone https://github.com/Tonyhzk/lobechat-data-exporter.git
cd lobechat-data-exporter

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python run.py
```

### 第二步：导入数据

1. 从 LobeChat 导出你的数据（设置 → 数据 → 导出所有数据）
2. 在页面点击「浏览」或直接拖拽 JSON 文件
3. 点击「解析数据」

### 第三步：查看数据

- **综合视图**：查看完整的数据树形结构
- **模块选项卡**：查看和编辑各个数据模块

### 第四步：导出数据

#### 导出为 Markdown（用于归档）

1. 在右侧选择「Markdown导出」
2. 选择导出模式：
   - 📁 按目录结构导出（推荐）
   - 📄 单个对话导出
3. 点击「开始导出 Markdown」

#### 导出为 JSON（用于迁移）

1. 在左侧底部勾选需要的模块
2. 点击「导出完整 JSON」
3. 导出的文件可以直接导入回 LobeChat

---

## 常见用途

### 📝 备份对话

```
导入 → 综合视图查看 → Markdown导出（按目录结构）
```

### 🔄 数据迁移

```
导入 → 编辑数据（可选）→ JSON导出 → 导入到新设备
```

### ✂️ 精简数据

```
导入 → 勾选需要的模块 → JSON导出
```

### 🔍 查找内容

```
导入 → 综合视图 → 使用Ctrl+F搜索
```

---

## 快捷操作

| 操作 | 方法 |
|------|------|
| 导入文件 | 拖拽 JSON 文件到输入框 |
| 复制数据 | 右键点击节点 → 复制JSON |
| 导出对话 | 右键点击主题 → 导出Markdown |
| 切换主题 | 顶部工具栏 → 切换主题 |
| 重新加载 | 顶部工具栏 → 重新加载 |

---

## 故障排除

### 问题：无法拖拽文件

**解决**：安装 tkinterdnd2
```bash
pip install tkinterdnd2
```

### 问题：导出的JSON无法导入LobeChat

**解决**：确保勾选了所有必需模块（带锁图标的模块）

### 问题：程序无法启动

**解决**：
```bash
# 检查Python版本（需要3.8+）
python --version

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

---

## 更多帮助

- 📖 [完整文档](README.md)
- 🐛 [问题反馈](https://github.com/Tonyhzk/lobechat-data-exporter/issues)
- 💬 [讨论区](https://github.com/Tonyhzk/lobechat-data-exporter/discussions)

---

**提示**：首次使用建议先用小型测试数据熟悉功能 🎯
