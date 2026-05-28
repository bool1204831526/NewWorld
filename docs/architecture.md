# NewWorld 架构设计书

## 1. 产品定位

NewWorld 是一个灵活、有趣的多智能体情景模拟工具。用户把一段材料、一个事件或一个设定放进来，系统生成参与者、关系、动机与冲突，让这些角色在一个小世界里互动，最后帮助用户观察舆论、叙事、风险或决策可能怎样演化。

它不应该像严肃学术建模工具，而应该像一个好玩的分析实验室。适用场景包括：

- 政策、公共事件或舆论反应预演
- 市场、竞品、品牌事件情景推演
- 小说、游戏、剧本里的角色动态模拟
- 社区、论坛、社交媒体话题走向测试
- 团队决策、危机处理、桌面推演

## 2. MVP 目标

第一个可用版本要回答一个核心问题：

> 给定一批资料和一个情景问题，里面有哪些关键角色，他们想要什么，他们会怎样互动，可能出现哪些结果？

MVP 应包含：

- 文档或粘贴文本输入
- 实体、关系、冲突抽取
- 基于实体生成智能体
- 按回合推进的互动模拟
- 可视化角色关系图
- 实时互动信息流
- 最终情景报告
- 可保存的模拟运行记录

## 3. 核心概念

### World / 世界

一次情景模拟的容器。它保存情景描述、输入资料、抽取结果、智能体、环境规则和运行历史。

### Source / 来源

用户提供的输入材料，例如粘贴文本、Markdown、PDF 提取文本、网页快照、笔记或结构化 JSON。

### Entity / 实体

从资料中抽取出的命名对象，可以是人物、组织、地点、政策、产品、事件、指标、社区或抽象概念。

### Relationship / 关系

实体之间的有类型连接，例如支持、反对、资助、监管、竞争、依赖、影响、提及。

### Agent / 智能体

模拟中的主动参与者，可以从实体生成，也可以由用户手动创建。它拥有目标、信念、限制、记忆、表达风格、影响力和决策规则。

### Environment / 环境

智能体互动发生的地方。早期版本可以是一个共享信息流；后续可以扩展为频道、新闻事件、市场指标、投票、私信等。

### Run / 运行

一次具体的模拟执行。它记录配置、消息、状态变化、指标和最终报告。

## 4. 系统架构

建议初始技术栈：

- 前端：React + TypeScript + Vite
- 后端 API：Python FastAPI
- 数据库：本地 MVP 使用 SQLite，后续迁移 PostgreSQL
- ORM：SQLModel 或 SQLAlchemy
- 任务执行：早期使用进程内任务，后续再引入队列
- LLM 接入：使用模型适配器接口，先支持 OpenAI，后续支持本地模型
- 可视化：关系图使用 React Flow 或 Cytoscape，互动流使用普通组件

高层模块：

```text
frontend/
  应用外壳、世界编辑器、关系图视图、信息流视图、报告视图

backend/
  API 路由、应用服务、模拟引擎、模型适配器

storage/
  数据模型、迁移、仓储层

engine/
  抽取、智能体生成、模拟循环、报告生成

docs/
  架构、产品说明、API 说明
```

## 5. 后端模块设计

### API 层

职责：

- 接收资料和情景提示词
- 创建和更新世界
- 启动模拟运行
- 流式返回或轮询运行进度
- 返回关系图、信息流、指标和报告

初始接口：

- `POST /worlds`
- `GET /worlds`
- `GET /worlds/{world_id}`
- `POST /worlds/{world_id}/sources`
- `POST /worlds/{world_id}/extract`
- `POST /worlds/{world_id}/agents`
- `POST /worlds/{world_id}/runs`
- `GET /runs/{run_id}`
- `GET /runs/{run_id}/events`

### 抽取服务

输入：

- 来源文本
- 可选的用户关注点
- 抽取 schema 版本

输出：

- 实体
- 关系
- 主张
- 不确定点
- 来源引用

MVP 可以先使用 LLM 输出 JSON，再进行 schema 校验。规则启发式抽取只作为演示和测试的兜底，不作为主路径。

### 智能体服务

从实体和用户编辑内容创建智能体。

智能体字段：

- 名称
- 代表的实体
- 角色
- 目标
- 信念
- 限制
- 立场
- 影响力
- 表达风格
- 记忆摘要

### 模拟引擎

模拟循环必须清晰、可检查、可复放：

1. 根据世界状态构建当前回合上下文。
2. 选择本回合活跃智能体。
3. 生成每个智能体的行动。
4. 应用环境反馈。
5. 更新记忆和指标。
6. 存储事件。
7. 回合结束或达到收敛条件后停止。

初始行动类型：

- post / 发帖
- reply / 回复
- amplify / 放大
- challenge / 质疑
- ask_for_evidence / 要求证据
- form_alliance / 结盟
- change_stance / 改变立场

### 报告服务

输出：

- 结果预测
- 最强叙事
- 关键角色变化
- 冲突点
- 不确定性驱动因素
- 推荐的下一轮情景
- 对来源和运行事件的引用

## 6. 前端体验

第一屏应该是实际工作台，而不是营销页。

主布局：

- 左侧：世界列表、资料、运行控制
- 中间：关系图和信息流标签页
- 右侧：选中实体或智能体详情
- 底部或独立标签页：报告和运行对比

关键操作：

- 粘贴资料
- 运行抽取
- 查看和编辑实体
- 查看和编辑智能体
- 启动模拟
- 观察信息流更新
- 打开最终报告
- 修改一个假设并复制运行

视觉和文案风格：

- 简单、活泼、清楚
- 避免过度学术化
- 使用熟悉词汇，例如 World、People、Feed、Map、Runs、Report，或中文界面中的世界、人物、信息流、地图、运行、报告

## 7. 数据模型草案

```text
World
  id, name, description, created_at, updated_at

Source
  id, world_id, type, title, content, metadata, created_at

Entity
  id, world_id, name, type, summary, confidence, source_refs

Relationship
  id, world_id, source_entity_id, target_entity_id, type, summary, weight, confidence, source_refs

Agent
  id, world_id, entity_id, name, role, goals, beliefs, constraints, stance, influence, style, memory

Run
  id, world_id, status, config, started_at, completed_at

RunEvent
  id, run_id, round, agent_id, action_type, content, state_delta, metrics, created_at

Report
  id, run_id, summary, sections, citations, created_at
```

## 8. LLM 适配器设计

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

所有模型输出进入存储前都必须经过校验。

## 9. Prompt 边界

Prompt 应该版本化，并被当作产品代码维护。

建议 prompt 文件：

```text
backend/prompts/extract_world.md
backend/prompts/create_agents.md
backend/prompts/agent_turn.md
backend/prompts/summarize_run.md
```

每个 prompt 应定义：

- 任务
- 输入契约
- 输出 schema
- 约束
- 只在必要时加入示例

## 10. 开发阶段

### Phase 0：地基

- 初始化仓库
- 架构设计书
- 项目专用 skill
- 基础项目骨架

### Phase 1：本地 MVP

- FastAPI 后端
- React 工作台
- SQLite 持久化
- 粘贴文本输入
- LLM 抽取
- 简单智能体生成
- 回合模拟
- 报告生成

### Phase 2：更好用的世界

- 可编辑关系图
- 保存运行
- 运行对比
- 来源引用
- prompt 和版本追踪
- 流式进度

### Phase 3：更丰富的模拟

- 私密频道
- 事件注入
- 指标和投票
- 记忆演化
- 情景分支
- 批量实验

### Phase 4：协作和部署

- 托管部署
- 用户账号
- 共享世界
- 导出报告
- 远程模型配置

## 11. 测试策略

测试层级：

- schema 校验和确定性服务的单元测试
- prompt 输出解析器的快照测试
- 世界和运行流程的 API 测试
- 前端主要工作台组件测试
- 创建世界 -> 抽取 -> 模拟 -> 报告 的端到端烟测

CI 中默认使用 mock LLM。真实模型测试应显式开启，并要求配置环境变量。

## 12. 工程原则

- 面向模型的 schema 必须清晰。
- 原始模型输出只作为调试材料，不直接当作可信状态。
- 模拟步骤必须可复放。
- 用户编辑状态和生成建议要分开存储。
- 优先做窄而有用的 MVP，不做宽而空的演示。
- 报告要能解释，并引用来源材料和运行事件。

## 13. 近期下一步

创建第一个可运行骨架：

- `backend/` FastAPI 应用，包含健康检查
- `frontend/` Vite React 应用，包含简单工作台外壳
- 暂不强制加入 `docker-compose.yml`
- 在 README 中记录开发命令
