from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_project_and_node_flow() -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "雾港纪事", "description": "测试项目"},
    )
    assert project_response.status_code == 200
    project = project_response.json()

    source_response = client.post(
        f"/api/projects/{project['id']}/sources",
        json={"title": "第一章摘要", "type": "剧情资料", "content": "林曜进入雾港。"},
    )
    assert source_response.status_code == 200

    node_response = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "林曜", "type": "人物", "summary": "寻找北境王印的人。"},
    )
    assert node_response.status_code == 200

    graph_response = client.get(f"/api/projects/{project['id']}/graph")
    assert graph_response.status_code == 200
    assert graph_response.json()["nodes"][0]["name"] == "林曜"
