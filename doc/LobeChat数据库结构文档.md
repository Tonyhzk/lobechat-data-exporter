# LobeChat PostgreSQL 数据库结构文档

## 概述

本文档描述了 LobeChat 数据库版的 PostgreSQL 数据库结构，以及如何使用本工具直接从数据库读取数据。

## 数据库连接功能

### 功能说明

从 v5.0 版本开始，本工具支持直接连接 LobeChat 的 PostgreSQL 数据库读取数据，无需手动导出 JSON 文件。

### 使用方法

1. 点击工具栏的 **「🗄️ 数据库」** 按钮
2. 在弹出的对话框中填写数据库连接信息：
   - **主机地址**：数据库服务器地址（如 `localhost` 或 `192.168.1.100`）
   - **端口**：PostgreSQL 端口（默认 `5432`）
   - **数据库名**：数据库名称（默认 `lobechat`）
   - **用户名**：数据库用户名
   - **密码**：数据库密码
   - **SSL**：是否使用 SSL 连接
3. （可选）填写 **用户ID** 可以只读取指定用户的数据
4. 点击 **「🔍 测试连接」** 验证连接是否正常
5. 点击 **「✅ 连接并读取」** 开始读取数据

### 依赖安装

使用数据库功能需要安装 `psycopg2-binary`：

```bash
pip install psycopg2-binary
```

---

## 数据库表结构

### 核心数据表

#### 1. `messages` - 消息表

存储所有对话消息。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | text | 消息ID（主键）|
| role | varchar(255) | 角色：user/assistant/system/tool |
| content | text | 消息内容 |
| model | text | 使用的模型名称 |
| provider | text | 提供商ID |
| session_id | text | 所属会话ID |
| topic_id | text | 所属主题ID |
| user_id | text | 用户ID |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |
| parent_id | text | 父消息ID |
| tools | jsonb | 工具调用信息 |
| metadata | jsonb | 元数据（如token统计）|
| reasoning | jsonb | 推理过程 |
| search | jsonb | 搜索信息 |

#### 2. `agents` - 助手表

存储助手/Agent 配置。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | text | 助手ID（主键）|
| slug | varchar(100) | 助手标识符 |
| title | varchar(255) | 助手名称 |
| description | varchar(1000) | 助手描述 |
| avatar | text | 头像URL |
| system_role | text | 系统提示词 |
| model | text | 默认模型 |
| provider | text | 默认提供商 |
| plugins | jsonb | 启用的插件列表 |
| tags | jsonb | 标签列表 |
| chat_config | jsonb | 聊天配置 |
| params | jsonb | 模型参数 |
| few_shots | jsonb | Few-shot示例 |
| user_id | text | 用户ID |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

#### 3. `sessions` - 会话表

存储会话信息。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | text | 会话ID（主键）|
| slug | varchar(100) | 会话标识符 |
| title | text | 会话标题 |
| description | text | 会话描述 |
| type | text | 类型：agent |
| user_id | text | 用户ID |
| group_id | text | 分组ID |
| pinned | boolean | 是否置顶 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

#### 4. `topics` - 主题表

存储对话主题。

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | text | 主题ID（主键）|
| title | text | 主题标题 |
| session_id | text | 所属会话ID |
| user_id | text | 用户ID |
| favorite | boolean | 是否收藏 |
| history_summary | text | 历史摘要 |
| metadata | jsonb | 元数据 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

#### 5. `agents_to_sessions` - 助手会话关联表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| agent_id | text | 助手ID |
| session_id | text | 会话ID |
| user_id | text | 用户ID |

### 配置数据表

#### 6. `ai_providers` - AI提供商表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | varchar(64) | 提供商ID（主键）|
| name | text | 提供商名称 |
| enabled | boolean | 是否启用 |
| sort | integer | 排序 |
| key_vaults | text | 加密的API密钥 |
| settings | jsonb | 设置 |
| config | jsonb | 配置 |
| user_id | text | 用户ID |

#### 7. `ai_models` - AI模型表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | varchar(150) | 模型ID（主键）|
| display_name | varchar(200) | 显示名称 |
| provider_id | varchar(64) | 提供商ID |
| type | varchar(20) | 类型：chat |
| enabled | boolean | 是否启用 |
| context_window_tokens | integer | 上下文窗口大小 |
| pricing | jsonb | 定价信息 |
| parameters | jsonb | 参数配置 |
| abilities | jsonb | 能力配置 |
| user_id | text | 用户ID |

### 其他数据表

| 表名 | 说明 |
|------|------|
| `users` | 用户表 |
| `user_settings` | 用户设置 |
| `session_groups` | 会话分组 |
| `message_plugins` | 消息插件数据 |
| `message_translates` | 消息翻译 |
| `message_tts` | TTS数据 |
| `threads` | 对话线程 |
| `files` | 文件表 |
| `knowledge_bases` | 知识库 |
| `embeddings` | 向量嵌入 |

---

## 数据关系图

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   agents    │────▶│  agents_to_sessions  │◀────│  sessions   │
└─────────────┘     └──────────────────────┘     └─────────────┘
                                                       │
                                                       ▼
                                                 ┌─────────────┐
                                                 │   topics    │
                                                 └─────────────┘
                                                       │
                                                       ▼
                                                 ┌─────────────┐
                                                 │  messages   │
                                                 └─────────────┘
```

**关系说明：**
- 一个 `agent`（助手）可以关联多个 `session`（会话）
- 一个 `session` 可以包含多个 `topic`（主题）
- 一个 `topic` 可以包含多个 `message`（消息）
- 消息也可以直接关联到 `session`（默认对话，没有topic）

---

## 常用查询示例

### 查询所有助手

```sql
SELECT id, title, slug, system_role, model, created_at
FROM agents
WHERE user_id = 'your_user_id'
ORDER BY created_at;
```

### 查询助手的所有对话

```sql
SELECT m.id, m.role, m.content, m.model, m.created_at,
       t.title as topic_title
FROM messages m
LEFT JOIN topics t ON m.topic_id = t.id
JOIN agents_to_sessions ats ON m.session_id = ats.session_id
WHERE ats.agent_id = 'agent_id'
ORDER BY m.created_at;
```

### 统计消息数量

```sql
SELECT 
    COUNT(*) as total_messages,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(DISTINCT topic_id) as topics
FROM messages
WHERE user_id = 'your_user_id';
```

### 查询最近的对话

```sql
SELECT m.role, LEFT(m.content, 100) as content_preview, 
       m.model, m.created_at
FROM messages m
WHERE m.user_id = 'your_user_id'
ORDER BY m.created_at DESC
LIMIT 20;
```

---

## 注意事项

1. **安全性**：数据库密码不会保存在本地配置文件中
2. **连接超时**：默认连接超时为 10 秒，请确保网络畅通
3. **防火墙**：确保云服务器的安全组/防火墙已开放 PostgreSQL 端口（默认5432）
4. **用户权限**：建议使用只读用户连接数据库
5. **数据量**：大量数据读取可能需要较长时间，请耐心等待

---

## 版本兼容性

本工具基于 **LobeChat v1.143.1** 数据库结构开发，兼容以下版本：
- LobeChat 数据库版 v1.x
- PostgreSQL 12.0+

如遇到数据结构不兼容的问题，请提交 Issue 反馈。
