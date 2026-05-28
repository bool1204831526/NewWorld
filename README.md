# NewWorld

NewWorld 是一个面向小说、剧本、游戏设定和长篇叙事资料的世界构建与剧情推演项目。

它的目标是让用户提供剧情文本、人物设定、世界观设定等资料，系统抽取重要节点、关系、世界观设定和时间线事件，帮助用户查看不同时间点的节点状态，并推演剧情发展走向。

## 当前阶段

项目地基已完成：

- Git 仓库已初始化
- 基础 `.gitignore`
- 中文 README
- 中文架构设计书
- NewWorld 项目专用 Codex skill
- FastAPI 后端骨架
- Vite React 前端工作台骨架

## 规划方向

- 输入小说剧情、人物设定、世界观设定或章节摘要
- 抽取人物与重要设定节点
- 构建节点关系图谱
- 构建世界观设定库
- 创建清晰的剧情时间线
- 查看不同时间点的节点状态
- 基于图谱、设定库和时间线推演剧情走向

## 技术栈

- 后端：Python 3.8 + FastAPI
- 前端：React + TypeScript + Vite
- 存储：SQLite（默认本地数据库位于 `backend/data/newworld.db`）
- 可视化：React Flow 作为后续图谱视图候选

## 本地开发

一键启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_newworld.ps1
```

或使用 Python 启动器：

```powershell
python .\start_newworld.py
```

首次运行或依赖缺失时：

```powershell
powershell -ExecutionPolicy Bypass -File .\start_newworld.ps1 -Install
python .\start_newworld.py --install
```
后端：

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

默认地址：

- 后端健康检查：`http://127.0.0.1:8000/health`
- 前端工作台：`http://127.0.0.1:5173`



