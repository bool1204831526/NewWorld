import os
import tempfile

os.environ["NEWWORLD_DB_PATH"] = os.path.join(tempfile.gettempdir(), "newworld_test.db")

from fastapi.testclient import TestClient

from app.extractor import extract_llm_error_message
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

def test_extract_project_from_source_flow() -> None:
    project_response = client.post("/api/projects", json={"name": "抽取测试"})
    assert project_response.status_code == 200
    project = project_response.json()

    source_response = client.post(
        f"/api/projects/{project['id']}/sources",
        json={
            "title": "第一章设定",
            "type": "剧情资料",
            "content": "林曜：北境少年，寻找北境王印。北境王印：继承权凭证。第一章，林曜进入雾港寻找北境王印。灰塔禁令规定旧术不能公开使用。",
        },
    )
    assert source_response.status_code == 200

    extract_response = client.post(f"/api/projects/{project['id']}/extract")
    assert extract_response.status_code == 200
    result = extract_response.json()
    assert result["created_nodes"] >= 2
    assert result["created_relationships"] >= 1
    assert result["created_lore_entries"] >= 1
    assert result["created_timeline_events"] >= 1

    graph_response = client.get(f"/api/projects/{project['id']}/graph")
    node_names = {node["name"] for node in graph_response.json()["nodes"]}
    assert "林曜" in node_names
    assert "北境王印" in node_names
    assert "第一章" not in node_names

    graph = graph_response.json()
    relationship = graph["relationships"][0]
    assert "存在" in relationship["summary"]
    assert "第一章，林曜进入雾港寻找北境王印" not in relationship["summary"]

    lore_response = client.get(f"/api/projects/{project['id']}/lore")
    assert lore_response.status_code == 200
    assert len(lore_response.json()) >= 1

    timeline_response = client.get(f"/api/projects/{project['id']}/timeline")
    assert timeline_response.status_code == 200
    assert timeline_response.json()[0]["time_label"] == "第一章"

    sources_response = client.get(f"/api/projects/{project['id']}/sources")
    assert sources_response.json()[0]["extracted_at"] is not None

    second_extract_response = client.post(f"/api/projects/{project['id']}/extract")
    assert second_extract_response.status_code == 200
    second_result = second_extract_response.json()
    assert second_result["processed_sources"] == 0
    assert second_result["skipped_sources"] == 1
    assert second_result["created_nodes"] == 0
    assert second_result["created_lore_entries"] == 0

def test_upload_source_file_flow() -> None:
    project_response = client.post("/api/projects", json={"name": "上传测试"})
    assert project_response.status_code == 200
    project = project_response.json()

    upload_response = client.post(
        f"/api/projects/{project['id']}/sources/upload",
        data={"type": "世界观设定"},
        files={"files": ("灰塔设定.md", "灰塔禁令：旧术不能公开使用。第一章，林曜进入灰塔。", "text/markdown")},
    )
    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    assert len(uploaded) == 1
    assert uploaded[0]["title"] == "灰塔设定"
    assert uploaded[0]["type"] == "世界观设定"
    assert uploaded[0]["extracted_at"] is None

    extract_response = client.post(f"/api/projects/{project['id']}/extract")
    assert extract_response.status_code == 200
    assert extract_response.json()["processed_sources"] == 1

def test_delete_node_removes_relationships() -> None:
    project_response = client.post("/api/projects", json={"name": "删除测试"})
    assert project_response.status_code == 200
    project = project_response.json()

    left_response = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "林曜", "type": "人物", "summary": "北境少年。"},
    )
    right_response = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "北境王印", "type": "物品", "summary": "继承权凭证。"},
    )
    assert left_response.status_code == 200
    assert right_response.status_code == 200
    left = left_response.json()
    right = right_response.json()

    relationship_response = client.post(
        f"/api/projects/{project['id']}/relationships",
        json={
            "source_node_id": left["id"],
            "target_node_id": right["id"],
            "type": "追寻",
            "summary": "林曜寻找北境王印。",
        },
    )
    assert relationship_response.status_code == 200

    delete_response = client.delete(f"/api/projects/{project['id']}/nodes/{left['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    graph_response = client.get(f"/api/projects/{project['id']}/graph")
    graph = graph_response.json()
    assert {node["id"] for node in graph["nodes"]} == {right["id"]}
    assert graph["relationships"] == []

def test_delete_source_flow() -> None:
    project_response = client.post("/api/projects", json={"name": "来源删除测试"})
    project = project_response.json()
    source_response = client.post(
        f"/api/projects/{project['id']}/sources",
        json={"title": "临时资料", "type": "剧情资料", "content": "林曜：北境少年。"},
    )
    source = source_response.json()

    delete_response = client.delete(f"/api/projects/{project['id']}/sources/{source['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    sources_response = client.get(f"/api/projects/{project['id']}/sources")
    assert sources_response.json() == []


def test_extract_selected_sources_only() -> None:
    project_response = client.post("/api/projects", json={"name": "选择抽取测试"})
    project = project_response.json()
    first_response = client.post(
        f"/api/projects/{project['id']}/sources",
        json={"title": "资料一", "type": "剧情资料", "content": "林曜：北境少年，寻找王印。王印：继承凭证。林曜寻找王印。"},
    )
    second_response = client.post(
        f"/api/projects/{project['id']}/sources",
        json={"title": "资料二", "type": "剧情资料", "content": "灰塔：旧术组织。旧术：被禁用的能力。灰塔掌握旧术。"},
    )
    first = first_response.json()
    second = second_response.json()

    extract_response = client.post(
        f"/api/projects/{project['id']}/extract",
        json={"source_ids": [second["id"]], "mode": "rules"},
    )
    assert extract_response.status_code == 200
    result = extract_response.json()
    assert result["processed_sources"] == 1
    assert result["skipped_sources"] == 0

    sources_response = client.get(f"/api/projects/{project['id']}/sources")
    sources = {source["id"]: source for source in sources_response.json()}
    assert sources[first["id"]]["extracted_at"] is None
    assert sources[second["id"]]["extracted_at"] is not None

def test_llm_extract_requires_config() -> None:
    project_response = client.post("/api/projects", json={"name": "LLM错误提示测试"})
    project = project_response.json()
    response = client.post(f"/api/projects/{project['id']}/extract", json={"mode": "llm"})
    assert response.status_code == 400
    assert "LLM 抽取需要填写 API 配置" in response.json()["detail"]

def test_llm_403_1010_error_has_actionable_hint() -> None:
    message = extract_llm_error_message("error code: 1010", 403)
    assert "当前运行环境" in message
    assert "Python/本地客户端" in message

