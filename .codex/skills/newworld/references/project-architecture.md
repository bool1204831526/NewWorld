# NewWorld 架构参考

## 项目目的

NewWorld 是一个面向小说、剧本、游戏设定和长篇叙事资料的世界构建与剧情推演工具。它从文字资料中抽取重要节点、关系、世界观设定和时间线事件，帮助用户查看不同时间点的节点状态，并推演剧情发展走向。

## 必要需求

- 抽取小说剧情、人物设定、世界观设定等文字资料。
- 构建重要节点关系图谱，点代表人物或重要设定，线代表关系。
- 根据抽取资料构建世界观设定。
- 根据关系图谱、世界观设定和时间线推演剧情发展走向。
- 支持手动添加设定人物或其他重要节点。
- 支持通过时间轴查看不同时间点的人物信息、节点状态与剧情发展。
- 提供清晰的时间发展时间线。

## MVP 范围

- 粘贴文本输入
- 重要节点抽取
- 关系抽取
- 世界观设定抽取
- 时间线事件抽取
- 手动新增和编辑节点、关系、设定
- 图谱视图
- 时间线视图
- 节点时间状态查看
- 剧情推演报告

## 数据模型

```text
Project(id, name, description, created_at, updated_at)
Source(id, project_id, type, title, content, metadata, created_at)
Node(id, project_id, name, type, aliases, summary, tags, importance, current_state, confidence, source_refs)
Relationship(id, project_id, source_node_id, target_node_id, type, summary, weight, confidence, valid_from, valid_to, source_refs)
LoreEntry(id, project_id, type, title, content, related_node_ids, related_event_ids, confidence, source_refs)
TimelineEvent(id, project_id, title, time_label, time_order, description, participant_node_ids, related_lore_ids, source_refs)
NodeStateSnapshot(id, project_id, node_id, time_label, time_order, state, location, faction, goals, knowledge, source_refs)
PredictionRun(id, project_id, status, premise, config, created_at, completed_at)
PredictionBranch(id, prediction_run_id, title, summary, trigger_conditions, affected_node_ids, relationship_changes, timeline_changes, confidence)
Report(id, prediction_run_id, summary, sections, citations, created_at)
```

## 后端模块

- API 路由：项目、来源、节点、关系、设定、时间线、节点状态、剧情推演
- 资料抽取服务：节点、关系、世界观设定、时间线事件、状态快照
- 图谱服务：节点合并、关系维护、图谱查询、用户编辑
- 世界观设定服务：设定条目管理、设定关联、冲突检测
- 时间线服务：事件管理、作品内时间表达、时间点状态查询
- 剧情推演服务：冲突识别、伏笔识别、剧情分支、因果解释
- 模型适配器：用统一接口访问不同模型

## 初始 API

```text
POST /projects
GET /projects
GET /projects/{project_id}
POST /projects/{project_id}/sources
POST /projects/{project_id}/extract
GET /projects/{project_id}/graph
POST /projects/{project_id}/nodes
PATCH /nodes/{node_id}
POST /projects/{project_id}/relationships
PATCH /relationships/{relationship_id}
GET /projects/{project_id}/lore
POST /projects/{project_id}/lore
GET /projects/{project_id}/timeline
POST /projects/{project_id}/timeline-events
GET /projects/{project_id}/node-states?time=...
POST /projects/{project_id}/predictions
GET /predictions/{prediction_id}
```

## Prompt 文件

```text
backend/app/prompts/extract_nodes.md
backend/app/prompts/extract_lore.md
backend/app/prompts/extract_timeline.md
backend/app/prompts/merge_graph.md
backend/app/prompts/predict_plot.md
backend/app/prompts/summarize_prediction.md
```

Prompt 是产品代码。必须明确输入契约、输出 schema、约束和必要示例。

## 前端工作台

第一屏必须是实际创作工作台：

- 左侧：项目、来源资料、抽取按钮、推演按钮
- 中间：图谱、时间线、设定库、推演报告标签页
- 右侧：选中节点、关系、事件或设定条目的详情编辑面板

## 工程原则

- 节点不等于人物，必须支持所有重要设定对象。
- 图谱、世界观设定和时间线是同等重要的一等数据。
- 用户手动添加和编辑的设定优先级高于模型抽取建议。
- 模型输出只作为建议，入库前必须校验。
- 每个抽取结果应保留来源引用。
- 时间线要能驱动不同时间点的节点状态和关系变化。
- 剧情推演要解释因果，不只生成一段故事文本。
