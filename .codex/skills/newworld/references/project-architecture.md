# NewWorld 架构参考

## 项目目的

NewWorld 是一个灵活的多智能体情景模拟工具。它把输入材料转化成一个小型模拟世界：角色、关系、动机、冲突、互动和报告。

## MVP 范围

- 粘贴文本输入
- 实体和关系抽取
- 智能体生成
- 按回合推进的信息流模拟
- 角色关系图
- 情景报告
- 保存运行记录

## 数据模型

```text
World(id, name, description, created_at, updated_at)
Source(id, world_id, type, title, content, metadata, created_at)
Entity(id, world_id, name, type, summary, confidence, source_refs)
Relationship(id, world_id, source_entity_id, target_entity_id, type, summary, weight, confidence, source_refs)
Agent(id, world_id, entity_id, name, role, goals, beliefs, constraints, stance, influence, style, memory)
Run(id, world_id, status, config, started_at, completed_at)
RunEvent(id, run_id, round, agent_id, action_type, content, state_delta, metrics, created_at)
Report(id, run_id, summary, sections, citations, created_at)
```

## 后端模块

- API 路由：世界 CRUD、来源上传、抽取、智能体生成、运行、运行事件
- 抽取服务：实体、关系、主张、不确定点、来源引用
- 智能体服务：角色、目标、信念、限制、立场、影响力、风格
- 模拟引擎：回合上下文、活跃智能体、行动、环境反馈、记忆更新、指标
- 报告服务：预测、叙事、角色变化、不确定因素、下一轮情景建议
- 模型适配器：用统一接口访问不同模型

## LLM 适配器

```text
generate_json(task, schema, messages, temperature)
generate_text(task, messages, temperature)
embed(texts)
```

逐步创建 OpenAI、本地模型和 mock 适配器。所有 JSON 输出入库前必须校验。

## 初始 API

```text
POST /worlds
GET /worlds
GET /worlds/{world_id}
POST /worlds/{world_id}/sources
POST /worlds/{world_id}/extract
POST /worlds/{world_id}/agents
POST /worlds/{world_id}/runs
GET /runs/{run_id}
GET /runs/{run_id}/events
```

## 模拟循环

1. 根据世界状态构建当前回合上下文。
2. 选择活跃智能体。
3. 生成每个智能体行动。
4. 应用环境反馈。
5. 更新记忆和指标。
6. 存储事件。
7. 达到回合数或收敛条件后停止。

初始行动类型：post、reply、amplify、challenge、ask_for_evidence、form_alliance、change_stance。

## 前端工作台

第一屏必须是实际产品工作台：

- 左侧：世界、来源、运行控制
- 中间：地图和信息流标签页
- 右侧：选中实体或智能体详情
- 报告或对比区域

使用简单词汇：世界、来源、地图、人物、信息流、运行、报告。

## Prompt 文件

```text
backend/prompts/extract_world.md
backend/prompts/create_agents.md
backend/prompts/agent_turn.md
backend/prompts/summarize_run.md
```

Prompt 是产品代码。必须明确输入契约、输出 schema、约束和必要示例。

## 测试

- 单元测试确定性服务和 schema 校验。
- CI 使用 mock provider。
- 真实模型测试必须显式开启，并依赖环境变量。
- 添加创建世界 -> 抽取 -> 模拟 -> 报告的端到端烟测。