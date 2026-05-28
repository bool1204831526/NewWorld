# NewWorld 后端

FastAPI 后端骨架，目标环境为 Python 3.8。

当前使用内存存储，后续会接入 SQLite 和持久化仓储层。

## 启动

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload --port 8000
```

健康检查：

```text
GET http://127.0.0.1:8000/health
```

## 测试

```powershell
python -m pytest tests
```
