---
name: newworld
description: 仅用于 C:\NewWorld 项目的开发协作 skill。Use only when the current repository, working directory, target files, or explicit user request refer to C:\NewWorld / NewWorld project. 用于继续开发 NewWorld 多智能体情景模拟项目，包括架构设计、前后端骨架、模拟引擎、数据模型、prompt、文档和项目工程决策。Do not use for other projects even if they are also multi-agent or simulation related.
---

# NewWorld

## 作用范围检查

使用本 skill 前必须先确认任务属于 `C:\NewWorld` 项目。

只有满足以下任一条件时才使用：

- 当前工作目录位于 `C:\NewWorld`。
- 用户明确提到 NewWorld 项目。
- 用户要求修改的文件位于 `C:\NewWorld`。

如果任务不属于 `C:\NewWorld`，立即停止使用本 skill，改按普通上下文处理。

## 项目概述

NewWorld 是一个轻量、灵活、有趣的多智能体情景模拟工具。用户提供资料后，系统构建一个包含角色、关系、动机与冲突的小世界，让智能体在其中互动，并输出可能的叙事、舆论、风险或决策走向。

项目根目录：`C:\NewWorld`

做架构、模块、schema、路线图或产品范围决策时，读取 `references/project-architecture.md`。小改动优先使用本文件，只有需要细节时再加载参考文件。

## 开发流程

1. 修改前先检查仓库状态和现有文件。
2. 优先遵循 `docs/architecture.md` 和 `references/project-architecture.md`。
3. 早期实现保持窄、可运行、可继续演进。
4. 前端第一屏做真实工作台，不做营销落地页。
5. 模拟步骤要可检查、可保存、可复放。
6. 模型输出入库前必须做 schema 校验。
7. 用户要求提交时，按清晰里程碑提交。

## 产品词汇

优先使用简单词汇：

- 世界：一次情景模拟容器
- 来源：输入材料
- 地图：实体和关系图
- 人物：生成或编辑的智能体
- 信息流：模拟互动内容
- 运行：一次模拟执行
- 报告：总结与预测

避免过度学术化。界面文案要清楚、有一点玩具感，但不要牺牲专业性。

## 推荐架构

初始技术栈：

- 前端：React + TypeScript + Vite
- 后端：Python FastAPI
- 存储：MVP 使用 SQLite，后续 PostgreSQL
- 可视化：React Flow 或 Cytoscape
- LLM 接入：模型适配器接口
- 测试：默认使用 mock LLM provider

核心后端服务：

- 抽取服务
- 智能体服务
- 模拟引擎
- 报告服务
- 模型适配器
- 持久化仓储层

## 实现原则

- 面向模型的 schema 要显式、可版本化。
- 用户编辑状态和生成建议分开存储。
- 保存模拟事件，让运行可以复放。
- 报告引用来源材料和运行事件。
- 测试中使用确定性的 mock provider。
- 不做无法演进成正式产品的宽泛 demo。

## MVP 主流程

围绕这个流程推进：

1. 创建世界。
2. 添加粘贴文本作为来源。
3. 抽取实体和关系，形成地图。
4. 从重要实体生成智能体人物。
5. 启动少量回合的运行。
6. 在信息流中展示智能体行动。
7. 生成包含结果预测和不确定因素的报告。

## 参考文件

- `references/project-architecture.md`：后续开发使用的中文架构参考。