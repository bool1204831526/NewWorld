# NewWorld 架构设计书

## 1. 产品定位

NewWorld 是一个面向小说、剧本、游戏设定和长篇叙事资料的世界构建与剧情推演工具。用户输入剧情文本、人物设定、世界观设定、组织设定、历史事件等资料后，系统抽取重要节点和关系，构建可编辑的关系图谱与世界观档案，并基于时间线推演剧情发展走向。

这里的“节点”不一定是人，也可以是组织、地点、国家、种族、物品、事件、规则、能力、信仰、灾难、秘密或任何会影响剧情的关键设定。

产品体验应像一个清晰、好用、有一点探索感的创作工作台，而不是学术建模软件。适用场景包括：

- 小说剧情、人物设定、世界观设定整理
- 长篇故事的人物关系图谱构建
- 多势力、多地点、多事件的剧情发展推演
- 不同时间点的人物状态和世界状态追踪
- 作者手动补充人物、组织、事件和规则设定
- 从已有设定中发现冲突、伏笔、矛盾和可能走向

## 2. 必要需求

当前阶段以用户明确提出的必要需求为核心：

1. 抽取文字资料，包括小说剧情、人物设定、世界观设定等，构建重要节点关系图谱。点代表人物或其他重要设定，线代表关系。
2. 根据抽取资料构建世界观设定，包括规则、地点、组织、历史、能力体系、阵营、物品、事件等。
3. 根据关系图谱与世界观设定推演世界剧情发展走向。
4. 除文字资料外，用户可以自主添加设定人物或其他重要节点。
5. 通过设定时间轴查看不同时间点的人物信息、节点状态与剧情发展。
6. 提供清晰的时间发展时间线。

## 3. MVP 目标

第一个可用版本要回答一个核心问题：

> 给定一批小说或世界观资料，当前世界里有哪些关键节点，它们之间是什么关系，在不同时间点状态如何，剧情可能怎样继续发展？

MVP 应包含：

- 粘贴或导入文字资料
- 抽取重要节点、节点类型、节点简介
- 抽取节点之间的关系
- 抽取世界观设定条目
- 手动新增和编辑节点
- 手动新增和编辑关系
- 创建和编辑时间线事件
- 查看不同时间点的节点状态
- 基于图谱、设定和时间线推演剧情走向
- 输出剧情推演报告

## 4. 核心概念

### Project / 项目

一个故事、小说、剧本或游戏世界的总容器。它保存所有资料、图谱、世界观、时间线、节点状态和推演记录。

### Source / 来源资料

用户提供的原始材料，例如小说正文、剧情大纲、人物设定、世界观设定、组织设定、历史年表、章节摘要或 Markdown 文档。

### Node / 重要节点

关系图谱中的点。节点不只代表人物，也可以代表组织、地点、国家、种族、物品、能力、规则、事件、秘密、阵营、神明、灾难等。

节点应包含：

- 名称
- 类型
- 简介
- 别名
- 标签
- 重要程度
- 来源引用
- 当前状态
- 可选的时间状态记录

### Relationship / 关系

关系图谱中的线。它连接两个节点，表示人物关系、组织隶属、敌对、同盟、血缘、师徒、持有、统治、影响、因果、地点归属、秘密关联等。

关系应包含：

- 起点节点
- 终点节点
- 关系类型
- 关系描述
- 强度或权重
- 发生时间或有效时间段
- 来源引用
- 是否确定

### LoreEntry / 世界观设定条目

从资料中抽取或由用户手动添加的设定条目。它用于承载世界规则，而不只是人物关系。

类型包括：

- 地理与地点
- 历史与纪年
- 组织与势力
- 能力体系
- 社会制度
- 种族与文化
- 物品与资源
- 禁忌与规则
- 已知伏笔或秘密

### TimelineEvent / 时间线事件

发生在某个时间点或时间段的剧情、历史或设定事件。时间可以是现实日期，也可以是作品内纪年，例如“王历 142 年”“第三章之后”“灾变前十年”。

### NodeStateSnapshot / 节点状态快照

某个节点在某个时间点的状态。例如人物的位置、阵营、目标、伤势、关系变化、持有物、已知信息、心理状态等。

### PredictionRun / 剧情推演

一次基于当前图谱、世界观和时间线的推演。它记录输入假设、推演过程、可能剧情走向、关键触发点和风险提示。

## 5. 系统架构

建议初始技术栈：

- 前端：React + TypeScript + Vite
- 后端 API：Python FastAPI
- 数据库：本地 MVP 使用 SQLite，后续迁移 PostgreSQL
- ORM：SQLModel 或 SQLAlchemy
- 可视化：关系图使用 React Flow，复杂图谱后续可评估 Cytoscape
- 时间线：前端先自研轻量时间线组件，后续再引入专用库
- LLM 接入：使用模型适配器接口，先支持 OpenAI，后续支持本地模型
- 测试：默认使用 mock LLM provider

高层模块：

```text
frontend/
  应用外壳、资料输入、图谱视图、设定库、时间线、推演报告

backend/
  API 路由、应用服务、模型适配器、持久化

backend/app/engine/
  资料抽取、图谱构建、设定抽取、时间线抽取、剧情推演、报告生成

backend/app/prompts/
  extract_nodes.md、extract_lore.md、extract_timeline.md、predict_plot.md

docs/
  架构、产品说明、API 说明
```

## 6. 后端模块设计

### API 层

初始接口：

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/sources`
- `POST /projects/{project_id}/extract`
- `GET /projects/{project_id}/graph`
- `POST /projects/{project_id}/nodes`
- `PATCH /nodes/{node_id}`
- `POST /projects/{project_id}/relationships`
- `PATCH /relationships/{relationship_id}`
- `GET /projects/{project_id}/lore`
- `POST /projects/{project_id}/lore`
- `GET /projects/{project_id}/timeline`
- `POST /projects/{project_id}/timeline-events`
- `GET /projects/{project_id}/node-states?time=...`
- `POST /projects/{project_id}/predictions`
- `GET /predictions/{prediction_id}`

### 资料抽取服务

输入：

- 来源文本
- 来源类型：剧情、人物设定、世界观设定、章节摘要、其他
- 可选关注点
- 抽取 schema 版本

输出：

- 重要节点
- 节点关系
- 世界观设定条目
- 时间线事件
- 节点状态快照
- 不确定项和待确认项
- 来源引用

### 图谱服务

职责：

- 合并重复节点
- 维护节点类型和重要程度
- 维护关系类型、强度和有效时间段
- 支持用户手动新增、编辑、合并、删除节点和关系
- 为前端提供图谱布局所需的数据

### 世界观设定服务

职责：

- 管理 LoreEntry
- 将设定条目关联到节点和时间线事件
- 检测设定冲突，例如同一地点归属、能力规则、历史事件顺序矛盾
- 为剧情推演提供世界规则上下文

### 时间线服务

职责：

- 管理 TimelineEvent
- 支持作品内时间表达
- 根据时间点查询节点状态
- 根据事件更新节点状态快照
- 为前端提供清晰时间线视图

### 剧情推演服务

推演不应只让智能体聊天，而应围绕叙事因果展开：

1. 读取当前图谱、世界观设定和时间线。
2. 识别关键冲突、未解决目标、伏笔和风险。
3. 生成若干可能剧情分支。
4. 对每个分支说明触发条件、参与节点、关系变化和世界影响。
5. 给出下一步剧情建议和需要补充的设定。

### 报告服务

输出：

- 剧情走向摘要
- 可能分支
- 关键触发事件
- 受影响人物或节点
- 关系变化
- 世界观影响
- 时间线变化
- 设定矛盾或空缺
- 来源引用

## 7. 前端体验

第一屏应该是创作工作台。

主布局建议：

- 左侧：项目、来源资料、抽取按钮、推演按钮
- 中间：图谱 / 时间线 / 设定库 / 推演报告 标签页
- 右侧：选中节点、关系、事件或设定条目的详情编辑面板

核心视图：

### 图谱视图

- 点代表人物或重要设定节点
- 线代表关系
- 支持按节点类型、阵营、时间点过滤
- 点击点查看节点设定和时间状态
- 点击线查看关系说明和有效时间

### 设定库视图

- 按地理、历史、组织、能力体系、社会制度、物品、秘密等分类查看
- 支持手动新增设定条目
- 支持关联到节点和时间线事件

### 时间线视图

- 展示清晰的时间发展线
- 支持作品内时间表达
- 点击事件查看参与节点和影响
- 支持选择时间点，刷新人物状态和图谱关系

### 推演报告视图

- 展示剧情可能走向
- 展示分支、触发条件和影响节点
- 标记设定矛盾、空缺和需要用户确认的问题

## 8. 数据模型草案

```text
Project
  id, name, description, created_at, updated_at

Source
  id, project_id, type, title, content, metadata, created_at

Node
  id, project_id, name, type, aliases, summary, tags, importance, current_state, confidence, source_refs

Relationship
  id, project_id, source_node_id, target_node_id, type, summary, weight, confidence, valid_from, valid_to, source_refs

LoreEntry
  id, project_id, type, title, content, related_node_ids, related_event_ids, confidence, source_refs

TimelineEvent
  id, project_id, title, time_label, time_order, description, participant_node_ids, related_lore_ids, source_refs

NodeStateSnapshot
  id, project_id, node_id, time_label, time_order, state, location, faction, goals, knowledge, source_refs

PredictionRun
  id, project_id, status, premise, config, created_at, completed_at

PredictionBranch
  id, prediction_run_id, title, summary, trigger_conditions, affected_node_ids, relationship_changes, timeline_changes, confidence

Report
  id, prediction_run_id, summary, sections, citations, created_at
```

## 9. LLM 适配器设计

使用模型适配器，避免应用被某个模型供应商绑定。

核心接口：

```text
generate_json(task, schema, messages, temperature)
generate_text(task, messages, temperature)
embed(texts)
```

适配器实现：

- OpenAI 适配器
- 本地模型适配器
- 测试用 mock 适配器

所有模型输出进入存储前都必须经过 schema 校验。

## 10. Prompt 边界

Prompt 应版本化，并被当作产品代码维护。

建议 prompt 文件：

```text
backend/app/prompts/extract_nodes.md
backend/app/prompts/extract_lore.md
backend/app/prompts/extract_timeline.md
backend/app/prompts/merge_graph.md
backend/app/prompts/predict_plot.md
backend/app/prompts/summarize_prediction.md
```

每个 prompt 应定义：

- 任务
- 输入契约
- 输出 schema
- 约束
- 只在必要时加入示例

## 11. 开发阶段

### Phase 0：地基

- 初始化仓库
- 中文架构设计书
- 项目内 Codex skill
- 明确叙事世界建模需求

### Phase 1：本地 MVP

- FastAPI 后端
- React 工作台
- SQLite 持久化
- 粘贴文本输入
- 节点与关系抽取
- 世界观设定抽取
- 时间线事件抽取
- 手动新增节点和关系
- 图谱视图
- 时间线视图
- 剧情推演报告

### Phase 2：更好用的创作工作台

- 图谱节点合并
- 设定冲突检测
- 时间点状态查询
- 运行历史保存
- 推演分支对比
- 来源引用跳转

### Phase 3：更丰富的叙事推演

- 多分支剧情树
- 伏笔追踪
- 阵营与势力变化
- 角色目标演化
- 事件注入
- 批量推演实验

### Phase 4：协作和部署

- 托管部署
- 用户账号
- 项目共享
- 导出图谱、时间线和报告
- 远程模型配置

## 12. 测试策略

测试层级：

- schema 校验和确定性服务的单元测试
- prompt 输出解析器的快照测试
- 项目、来源、图谱、时间线和推演流程的 API 测试
- 前端图谱、时间线、设定库组件测试
- 创建项目 -> 添加资料 -> 抽取图谱 -> 查看时间线 -> 推演剧情 -> 生成报告的端到端烟测

CI 中默认使用 mock LLM。真实模型测试应显式开启，并要求配置环境变量。

## 13. 工程原则

- 节点不等于人物，必须支持所有重要设定对象。
- 图谱、世界观设定和时间线是同等重要的一等数据。
- 用户手动添加和编辑的设定优先级高于模型抽取建议。
- 模型输出只作为建议，入库前必须校验。
- 每个抽取结果应保留来源引用。
- 时间线要能驱动不同时间点的节点状态和关系变化。
- 剧情推演要解释因果，不只生成一段故事文本。

## 14. 近期下一步

创建第一个可运行骨架，并优先支持叙事世界建模闭环：

- `backend/` FastAPI 应用，包含健康检查
- `frontend/` Vite React 应用，包含简单工作台外壳
- 数据模型先覆盖 Project、Source、Node、Relationship、LoreEntry、TimelineEvent
- README 中记录开发命令
