import os
import tempfile

os.environ["NEWWORLD_DB_PATH"] = os.path.join(tempfile.gettempdir(), "newworld_test.db")

from fastapi.testclient import TestClient

from app.main import app
from app.storage import store


client = TestClient(app)


def setup_function() -> None:
    store.reset()


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


def test_timeline_and_prediction_flow() -> None:
    project_response = client.post("/api/projects", json={"name": "时间线测试"})
    assert project_response.status_code == 200
    project = project_response.json()

    node_response = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "北境王印", "type": "物品", "summary": "继承权凭证。"},
    )
    assert node_response.status_code == 200
    node = node_response.json()

    event_response = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={
            "title": "王印失踪",
            "time_label": "第一章",
            "time_order": 1,
            "description": "北境王印从王城密库失踪。",
            "participant_node_ids": [node["id"]],
        },
    )
    assert event_response.status_code == 200

    timeline_response = client.get(f"/api/projects/{project['id']}/timeline")
    assert timeline_response.status_code == 200
    assert timeline_response.json()[0]["title"] == "王印失踪"

    prediction_response = client.post(f"/api/projects/{project['id']}/predictions")
    assert prediction_response.status_code == 200
    assert prediction_response.json()["latest_event"] == "王印失踪"
