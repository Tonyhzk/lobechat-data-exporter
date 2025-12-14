# LobeChat 数据结构完整文档

## 文档概述
本文档详细描述了 LobeChat 导出数据的 JSON 结构，用于数据分析、迁移和 AI 交互提示词构建。

---

## 一、顶层结构

```json
{
  "data": { ... },           // 核心数据容器
  "mode": "postgres",        // 存储模式
  "schemaHash": "..."        // 数据架构哈希值
}
```

---

## 二、data 核心数据结构

### 2.1 userSettings（用户设置）

**数组类型**，存储用户的全局配置信息。

#### 字段说明：
```json
{
  "id": "uuid",                    // 用户唯一标识
  "tts": {},                       // 文本转语音设置
  "hotkey": {},                    // 快捷键配置
  "keyVaults": null,               // 密钥保险库
  "general": {},                   // 通用设置
  "languageModel": {},             // 语言模型配置
  "systemAgent": {                 // 系统代理配置
    "topic": {                     // 主题生成模型
      "model": "model-name",
      "provider": "provider-name"
    },
    "agentMeta": {},               // 代理元数据
    "translation": {},             // 翻译模型
    "queryRewrite": {},            // 查询重写模型
    "generationTopic": {},         // 话题生成
    "historyCompress": {}          // 历史压缩
  },
  "defaultAgent": {},              // 默认代理设置
  "tool": {},                      // 工具配置
  "image": {}                      // 图像设置
}
```

---

### 2.2 agents（助手/代理配置）

**数组类型**，存储所有创建的 AI 助手配置。

#### 核心字段：
```json
{
  "id": "agt_xxxxx",              // 助手唯一ID
  "slug": "string",               // URL友好标识
  "title": "string",              // 助手名称
  "description": "string",        // 描述
  "tags": ["tag1", "tag2"],       // 标签数组
  "avatar": "emoji",              // 头像（emoji或URL）
  "backgroundColor": "rgba(...)", // 背景色
  "plugins": [],                  // 插件列表
  "clientId": null,               // 客户端ID
  
  "chatConfig": {                 // 聊天配置
    "searchMode": "off|on",       // 搜索模式
    "displayMode": "chat|docs",   // 显示模式
    "historyCount": 20,           // 历史消息数量
    "searchFCModel": {            // 搜索功能调用模型
      "model": "string",
      "provider": "string"
    },
    "enableReasoning": false,     // 启用推理
    "enableStreaming": true,      // 启用流式输出
    "enableHistoryCount": true,   // 启用历史计数
    "reasoningBudgetToken": 1024, // 推理token预算
    "enableAutoCreateTopic": true,// 自动创建主题
    "enableCompressHistory": true,// 压缩历史
    "autoCreateTopicThreshold": 2 // 自动创建主题阈值
  },
  
  "fewShots": null,               // 少样本示例
  "model": "model-name",          // 使用的模型
  "params": {                     // 模型参数
    "top_p": 1,
    "temperature": 1,
    "presence_penalty": 0,
    "frequency_penalty": 0
  },
  "provider": "provider-name",    // 提供商
  "systemRole": "string",         // 系统角色/提示词
  
  "tts": {                        // 语音设置
    "voice": {
      "openai": "alloy"
    },
    "sttLocale": "auto",
    "ttsService": "openai",
    "showAllLocaleVoice": false
  },
  
  "virtual": false,               // 是否虚拟助手
  "openingMessage": null,         // 开场白
  "openingQuestions": [],         // 开场问题列表
  
  "accessedAt": "ISO8601",        // 最后访问时间
  "createdAt": "ISO8601",         // 创建时间
  "updatedAt": "ISO8601"          // 更新时间
}
```

---

### 2.3 aiModels（AI模型列表）

**数组类型**，存储所有可用的 AI 模型信息。

#### 模型字段说明：
```json
{
  "id": "model-id",               // 模型唯一标识
  "displayName": "string",        // 显示名称
  "description": "string",        // 模型描述
  "organization": null,           // 组织名称
  "enabled": true|false,          // 是否启用
  "providerId": "provider-id",    // 提供商ID
  "type": "chat|image|embedding|tts|stt|realtime", // 模型类型
  "sort": null,                   // 排序值
  "pricing": null,                // 定价信息
  
  "parameters": {                 // 模型参数配置
    "size": {                     // 尺寸参数（图像模型）
      "enum": ["1024x1024", ...],
      "default": "1024x1024"
    },
    "cfg": {                      // 配置强度（图像模型）
      "max": 10,
      "min": 1,
      "step": 0.1,
      "default": 5.5
    },
    "seed": { "default": null },  // 随机种子
    "prompt": { "default": "" }   // 提示词
  },
  
  "config": null,                 // 额外配置
  
  "abilities": {                  // 模型能力
    "video": false,               // 视频处理
    "search": true,               // 搜索功能
    "vision": true,               // 视觉识别
    "reasoning": true,            // 推理能力
    "imageOutput": false,         // 图像输出
    "functionCall": true          // 函数调用
  },
  
  "contextWindowTokens": 128000,  // 上下文窗口大小
  "source": "remote|local",       // 模型来源
  "releasedAt": "ISO8601",        // 发布日期
  "accessedAt": "ISO8601",        // 访问时间
  "createdAt": "ISO8601",         // 创建时间
  "updatedAt": "ISO8601"          // 更新时间
}
```

**模型类型说明：**
- `chat`: 对话模型
- `image`: 图像生成模型
- `embedding`: 向量化模型
- `tts`: 文本转语音
- `stt`: 语音转文本
- `realtime`: 实时交互模型

---

### 2.4 aiProviders（AI提供商配置）

**数组类型**，存储 AI 服务提供商的配置信息。

#### 字段说明：
```json
{
  "id": "provider-id",            // 提供商唯一标识
  "name": "string",               // 提供商名称
  "sort": null,                   // 排序
  "enabled": true|false,          // 是否启用
  "fetchOnClient": null,          // 客户端获取
  "checkModel": null,             // 检查模型
  "logo": null,                   // Logo URL
  "description": null,            // 描述
  "keyVaults": "encrypted",       // 加密的密钥
  "source": "builtin|custom",     // 来源类型
  
  "settings": {                   // 提供商设置
    "sdkType": "openai"           // SDK类型
  },
  
  "config": {},                   // 配置信息
  "accessedAt": "ISO8601",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

---

### 2.5 messages（消息列表）

**数组类型**，存储所有的对话消息。

#### 消息结构：
```json
{
  "id": "msg_xxxxx",              // 消息唯一ID
  "role": "user|assistant|system",// 角色
  "content": "string",            // 消息内容
  "reasoning": null,              // 推理过程
  "search": null,                 // 搜索结果
  
  "metadata": {                   // 元数据（助手消息）
    "tps": 65.98,                 // Token每秒
    "cost": 0.002244,             // 费用
    "ttft": 3472,                 // 首字时间(ms)
    "latency": 5624,              // 延迟(ms)
    "duration": 2152,             // 持续时间(ms)
    "totalTokens": 180,           // 总token数
    "inputTextTokens": 38,        // 输入文本token
    "outputTextTokens": 142,      // 输出文本token
    "totalInputTokens": 38,       // 总输入token
    "totalOutputTokens": 142      // 总输出token
  },
  
  "model": "model-name",          // 使用的模型
  "provider": "provider-name",    // 提供商
  "favorite": false,              // 是否收藏
  "error": null,                  // 错误信息
  "tools": null,                  // 使用的工具
  "traceId": null,                // 跟踪ID
  "observationId": null,          // 观察ID
  "clientId": null,               // 客户端ID
  
  "sessionId": "ssn_xxxxx",       // 所属会话
  "topicId": "tpc_xxxxx",         // 所属主题
  "threadId": null,               // 所属线程
  "parentId": "msg_xxxxx",        // 父消息ID
  "quotaId": null,                // 配额ID
  "agentId": null,                // 助手ID
  "groupId": null,                // 组ID
  "targetId": null,               // 目标ID
  "messageGroupId": null,         // 消息组ID
  
  "accessedAt": "ISO8601",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

**角色类型：**
- `user`: 用户消息
- `assistant`: AI助手回复
- `system`: 系统消息

---

### 2.6 sessions（会话列表）

**数组类型**，存储所有的聊天会话。

#### 会话结构：
```json
{
  "id": "ssn_xxxxx",              // 会话唯一ID
  "slug": "string",               // URL友好标识
  "title": null,                  // 会话标题
  "description": null,            // 描述
  "avatar": null,                 // 头像
  "backgroundColor": null,        // 背景色
  "type": "agent|group",          // 会话类型
  "groupId": null,                // 所属组ID
  "clientId": null,               // 客户端ID
  "pinned": false,                // 是否置顶
  "accessedAt": "ISO8601",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

---

### 2.7 topics（主题列表）

**数组类型**，存储会话中的对话主题。

#### 主题结构：
```json
{
  "id": "tpc_xxxxx",              // 主题唯一ID
  "title": "string",              // 主题标题
  "favorite": false,              // 是否收藏
  "sessionId": "ssn_xxxxx",       // 所属会话
  "groupId": null,                // 所属组
  "clientId": null,               // 客户端ID
  "historySummary": null,         // 历史摘要
  "metadata": null,               // 元数据
  "accessedAt": "ISO8601",
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```

---

### 2.8 agentsToSessions（助手会话关联）

**数组类型**，关联助手和会话的多对多关系表。

#### 关联结构：
```json
{
  "agentId": "agt_xxxxx",         // 助手ID
  "sessionId": "ssn_xxxxx",       // 会话ID
  "userId": "uuid"                // 用户ID
}
```

---

### 2.9 其他数据集合

以下集合在示例数据中为空数组，但也是重要的数据结构：

- **userInstalledPlugins**: 用户安装的插件列表
- **messageChunks**: 消息块（用于长消息分块）
- **messagePlugins**: 消息插件数据
- **messageTranslates**: 消息翻译数据
- **sessionGroups**: 会话分组
- **threads**: 对话线程

---

## 三、数据关系图

```
用户 (userSettings)
  ↓
会话 (sessions) ← → 助手 (agents) [通过 agentsToSessions]
  ↓
主题 (topics)
  ↓
消息 (messages)
  ↓
消息块/翻译/插件 (messageChunks/Translates/Plugins)

AI提供商 (aiProviders)
  ↓
AI模型 (aiModels)
```

---

## 四、时间戳字段说明

所有主要实体都包含三个时间戳字段：

- **createdAt**: 创建时间（ISO 8601格式）
- **updatedAt**: 最后更新时间
- **accessedAt**: 最后访问时间

示例：`"2025-12-13T10:56:06.270Z"`

---

## 五、ID命名规范

LobeChat 使用前缀标识不同实体类型：

- `agt_`: Agent（助手）
- `ssn_`: Session（会话）
- `tpc_`: Topic（主题）
- `msg_`: Message（消息）
- `deeaed85-...`: User ID（UUID格式）

---

## 六、常用查询场景

### 6.1 获取某个会话的所有消息
```javascript
const sessionMessages = data.messages.filter(
  msg => msg.sessionId === "ssn_xxxxx"
);
```

### 6.2 获取某个主题的对话
```javascript
const topicMessages = data.messages.filter(
  msg => msg.topicId === "tpc_xxxxx"
);
```

### 6.3 获取会话关联的助手
```javascript
const sessionAgent = data.agentsToSessions.find(
  rel => rel.sessionId === "ssn_xxxxx"
);
const agent = data.agents.find(
  a => a.id === sessionAgent.agentId
);
```

### 6.4 获取启用的AI模型
```javascript
const enabledModels = data.aiModels.filter(
  model => model.enabled === true
);
```

### 6.5 计算消息统计
```javascript
const stats = data.messages.reduce((acc, msg) => {
  if (msg.metadata) {
    acc.totalCost += msg.metadata.cost || 0;
    acc.totalTokens += msg.metadata.totalTokens || 0;
  }
  return acc;
}, { totalCost: 0, totalTokens: 0 });
```

---

## 七、给大模型的提示词模板

### 7.1 数据分析提示词

```
我有一个 LobeChat 的数据导出文件，JSON 结构如下：

核心数据集合：
- data.agents: 助手配置列表
- data.sessions: 会话列表
- data.topics: 主题列表
- data.messages: 消息列表
- data.aiModels: AI模型列表
- data.aiProviders: AI提供商配置

请帮我分析：
1. [具体分析需求]
2. [统计需求]
3. [数据关系需求]

数据文件：[粘贴JSON数据]
```

### 7.2 数据迁移提示词

```
我需要将 LobeChat 数据迁移到 [目标系统]。

源数据结构：
- 助手配置 (agents): 包含 systemRole, model, chatConfig 等
- 消息记录 (messages): 包含 role, content, metadata 等
- 会话信息 (sessions): 包含 title, type 等

请帮我：
1. 设计目标系统的数据映射方案
2. 编写转换脚本
3. 处理特殊字段的转换逻辑

源数据示例：[粘贴部分JSON]
```

### 7.3 数据清洗提示词

```
我有 LobeChat 导出的数据，需要进行以下清洗：

数据集：
- messages: 共 X 条消息
- sessions: 共 Y 个会话
- topics: 共 Z 个主题

清洗需求：
1. 删除空会话（没有消息的会话）
2. 合并重复主题
3. 移除测试数据
4. 重新计算统计信息

请提供清洗脚本。

原始数据：[粘贴JSON]
```

---

## 八、数据安全注意事项

1. **敏感信息**：
   - `keyVaults` 字段包含加密的 API 密钥
   - 导出前应确认是否包含敏感对话内容

2. **个人隐私**：
   - 消息内容可能包含个人信息
   - 分享数据前应脱敏处理

3. **加密字段**：
   - `keyVaults` 使用特定加密算法
   - 格式：`盐:初始化向量:加密数据`

---

## 九、版本信息

- **Schema Hash**: 用于验证数据结构版本
- **Mode**: 存储后端类型（如 postgres）
- 当前文档基于 LobeChat 数据格式（2025-12-13版本）

---

## 十、扩展阅读

- LobeChat 官方文档：https://lobehub.com/docs
- 数据导出功能说明
- API 参考文档
- 插件开发指南

---

**文档更新时间**: 2025-12-13  
**适用版本**: LobeChat 数据格式 v1.x  
**维护者**: AI Assistant
