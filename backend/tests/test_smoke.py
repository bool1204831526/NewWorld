import os
import tempfile

os.environ["NEWWORLD_DB_PATH"] = os.path.join(tempfile.gettempdir(), "newworld_test.db")

from fastapi.testclient import TestClient

from app.extractor import extract_llm_error_message, validate_llm_api_base, validate_llm_api_key
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

def test_llm_api_key_rejects_chinese_characters() -> None:
    try:
        validate_llm_api_key("sk-测试")
    except ValueError as error:
        assert "API Key" in str(error)
        assert "中文" in str(error)
    else:
        raise AssertionError("expected invalid API key to raise")


def test_llm_api_base_rejects_non_ascii_url() -> None:
    try:
        validate_llm_api_base("https://例子.com/v1")
    except ValueError as error:
        assert "API Base" in str(error)
        assert "中文" in str(error)
    else:
        raise AssertionError("expected invalid API base to raise")
def test_merge_node_rewrites_relationships_and_timeline() -> None:
    project_response = client.post("/api/projects", json={"name": "节点合并测试"})
    project = project_response.json()
    target = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "林曜", "type": "人物", "summary": "北境少年。"},
    ).json()
    duplicate = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "林耀", "type": "人物", "summary": "同一角色的误写。"},
    ).json()
    other = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "王印", "type": "物品", "summary": "继承凭证。"},
    ).json()
    client.post(
        f"/api/projects/{project['id']}/relationships",
        json={"source_node_id": duplicate["id"], "target_node_id": other["id"], "type": "追寻", "summary": "寻找王印。"},
    )
    client.post(
        f"/api/projects/{project['id']}/relationships",
        json={"source_node_id": target["id"], "target_node_id": duplicate["id"], "type": "同一人", "summary": "误抽成两个节点。"},
    )
    client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "出发", "time_label": "第一章", "time_order": 1, "description": "林耀出发。", "participant_node_ids": [duplicate["id"]]},
    )

    response = client.post(
        f"/api/projects/{project['id']}/nodes/{target['id']}/merge",
        json={"source_node_id": duplicate["id"]},
    )
    assert response.status_code == 200
    merged = response.json()
    assert "林耀" in merged["aliases"]
    assert "误写" in merged["summary"]

    graph = client.get(f"/api/projects/{project['id']}/graph").json()
    assert {node["id"] for node in graph["nodes"]} == {target["id"], other["id"]}
    assert all(relationship["source_node_id"] != duplicate["id"] for relationship in graph["relationships"])
    assert all(relationship["target_node_id"] != duplicate["id"] for relationship in graph["relationships"])
    assert any(relationship["source_node_id"] == target["id"] and relationship["target_node_id"] == other["id"] for relationship in graph["relationships"])

    timeline = client.get(f"/api/projects/{project['id']}/timeline").json()
    assert timeline[0]["participant_node_ids"] == [target["id"]]
def test_update_timeline_event() -> None:
    project_response = client.post("/api/projects", json={"name": "时间线编辑测试"})
    project = project_response.json()
    event = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "旧事件", "time_label": "第一章", "time_order": 2, "description": "旧描述", "participant_node_ids": []},
    ).json()

    response = client.put(
        f"/api/projects/{project['id']}/timeline-events/{event['id']}",
        json={"title": "新事件", "time_label": "第二章", "time_order": 1, "description": "新描述", "participant_node_ids": []},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "新事件"

    timeline = client.get(f"/api/projects/{project['id']}/timeline").json()
    assert timeline[0]["title"] == "新事件"
    assert timeline[0]["time_label"] == "第二章"



def test_timeline_flow_layout_persists() -> None:
    project_response = client.post("/api/projects", json={"name": "流程图保存失败"})
    project = project_response.json()
    first = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "出发", "time_label": "第一章", "time_order": 1, "description": "离开故乡。", "participant_node_ids": []},
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "分歧", "time_label": "第二章", "time_order": 2, "description": "路线分开。", "participant_node_ids": []},
    ).json()

    payload = {
        "project_id": "wrong_project_id",
        "positions": [
            {"event_id": first["id"], "x": 240, "y": 80},
            {"event_id": second["id"], "x": 520, "y": 260},
            {"event_id": "missing", "x": 1, "y": 1},
        ],
        "edges": [
            {"id": "edge_branch", "source_event_id": first["id"], "target_event_id": second["id"]},
            {"id": "edge_invalid", "source_event_id": first["id"], "target_event_id": "missing"},
        ],
    }
    response = client.put(f"/api/projects/{project['id']}/timeline-flow", json=payload)
    assert response.status_code == 200
    saved = response.json()
    assert saved["project_id"] == project["id"]
    assert saved["has_layout"] is True
    assert len(saved["positions"]) == 2
    assert saved["edges"] == [{"id": "edge_branch", "source_event_id": first["id"], "target_event_id": second["id"]}]

    loaded = client.get(f"/api/projects/{project['id']}/timeline-flow")
    assert loaded.status_code == 200
    assert loaded.json() == saved


def test_delete_timeline_flow_layout() -> None:
    project_response = client.post("/api/projects", json={"name": "删除流程图布局测试"})
    project = project_response.json()
    event = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "出发", "time_label": "第一章", "time_order": 1, "description": "离开故乡。", "participant_node_ids": []},
    ).json()
    client.put(
        f"/api/projects/{project['id']}/timeline-flow",
        json={"project_id": project["id"], "positions": [{"event_id": event["id"], "x": 120, "y": 90}], "edges": []},
    )

    response = client.delete(f"/api/projects/{project['id']}/timeline-flow")
    assert response.status_code == 200
    assert response.json() == {"project_id": project["id"], "positions": [], "edges": [], "has_layout": False}
    cleared = client.get(f"/api/projects/{project['id']}/timeline-flow").json()
    assert cleared["positions"] == []
    assert cleared["has_layout"] is False


def test_organize_timeline_flow_with_llm(monkeypatch) -> None:
    project_response = client.post("/api/projects", json={"name": "LLM流程图整理测试"})
    project = project_response.json()
    first = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "出发", "time_label": "第一章", "time_order": 1, "description": "离开故乡。", "participant_node_ids": []},
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "分歧", "time_label": "第二章", "time_order": 2, "description": "路线分开。", "participant_node_ids": []},
    ).json()

    def fake_organizer(project_id, events, config):
        from app.schemas import TimelineFlowEdge, TimelineFlowLayout, TimelineFlowPosition

        return TimelineFlowLayout(
            project_id=project_id,
            positions=[
                TimelineFlowPosition(event_id=events[0].id, x=300, y=80),
                TimelineFlowPosition(event_id=events[1].id, x=520, y=260),
            ],
            edges=[TimelineFlowEdge(id="llm_branch", source_event_id=events[0].id, target_event_id=events[1].id)],
        )

    monkeypatch.setattr("app.api.routes.organize_timeline_flow_with_llm", fake_organizer)
    response = client.post(
        f"/api/projects/{project['id']}/timeline-flow/organize",
        json={"llm": {"api_base": "https://example.com/v1", "api_key": "sk-test", "model": "test-model"}},
    )
    assert response.status_code == 200
    layout = response.json()
    assert {position["event_id"] for position in layout["positions"]} == {first["id"], second["id"]}
    assert layout["has_layout"] is True
    assert layout["edges"] == [{"id": "llm_branch", "source_event_id": first["id"], "target_event_id": second["id"]}]
    assert client.get(f"/api/projects/{project['id']}/timeline-flow").json() == layout


def test_delete_timeline_event_cleans_flow_layout() -> None:
    project_response = client.post("/api/projects", json={"name": "流程节点删除测试"})
    project = project_response.json()
    first = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "出发", "time_label": "第一章", "time_order": 1, "description": "离开故乡。", "participant_node_ids": []},
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "分歧", "time_label": "第二章", "time_order": 2, "description": "路线分开。", "participant_node_ids": []},
    ).json()
    client.put(
        f"/api/projects/{project['id']}/timeline-flow",
        json={
            "project_id": project["id"],
            "positions": [{"event_id": first["id"], "x": 120, "y": 90}, {"event_id": second["id"], "x": 320, "y": 260}],
            "edges": [{"id": "edge_one", "source_event_id": first["id"], "target_event_id": second["id"]}],
            "has_layout": True,
        },
    )

    response = client.delete(f"/api/projects/{project['id']}/timeline-events/{first['id']}")
    assert response.status_code == 200
    timeline = client.get(f"/api/projects/{project['id']}/timeline").json()
    assert [event["id"] for event in timeline] == [second["id"]]
    layout = client.get(f"/api/projects/{project['id']}/timeline-flow").json()
    assert layout["positions"] == [{"event_id": second["id"], "x": 320.0, "y": 260.0}]
    assert layout["edges"] == []


def test_timeline_board_rules_organize() -> None:
    project_response = client.post("/api/projects", json={"name": "故事线规则整理测试"})
    project = project_response.json()
    node = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "林曜", "type": "人物", "summary": "北境少年。"},
    ).json()
    first = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "入城", "time_label": "第一章", "time_order": 1, "description": "林曜进入王城。", "participant_node_ids": [node["id"]]},
    ).json()
    second = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "王印线索", "time_label": "第二章", "time_order": 2, "description": "王印线索出现。", "participant_node_ids": []},
    ).json()

    response = client.post(f"/api/projects/{project['id']}/timeline-board/organize", json={"mode": "rules"})
    assert response.status_code == 200
    board = response.json()
    assert board["mode"] == "rules"
    assert {placement["event_id"] for placement in board["placements"]} == {first["id"], second["id"]}
    assert len(board["lanes"]) >= 1

    loaded = client.get(f"/api/projects/{project['id']}/timeline-board")
    assert loaded.status_code == 200
    assert loaded.json() == board


def test_manual_lore_entry_crud_flow() -> None:
    project_response = client.post("/api/projects", json={"name": "设定库测试"})
    assert project_response.status_code == 200
    project = project_response.json()

    create_response = client.post(
        f"/api/projects/{project['id']}/lore",
        json={"type": "势力", "title": "灰塔", "content": "灰塔管理旧术档案。"},
    )
    assert create_response.status_code == 200
    entry = create_response.json()
    assert entry["title"] == "灰塔"

    update_response = client.put(
        f"/api/projects/{project['id']}/lore/{entry['id']}",
        json={"type": "组织", "title": "灰塔档案局", "content": "灰塔档案局负责封存旧术。"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["type"] == "组织"

    lore_response = client.get(f"/api/projects/{project['id']}/lore")
    assert lore_response.status_code == 200
    assert lore_response.json()[0]["title"] == "灰塔档案局"

    delete_response = client.delete(f"/api/projects/{project['id']}/lore/{entry['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    empty_response = client.get(f"/api/projects/{project['id']}/lore")
    assert empty_response.json() == []


def test_wiki_entries_from_project_graph() -> None:
    project_response = client.post("/api/projects", json={"name": "Wiki测试"})
    assert project_response.status_code == 200
    project = project_response.json()

    node_response = client.post(
        f"/api/projects/{project['id']}/nodes",
        json={"name": "林曜", "type": "人物", "summary": "北境少年。"},
    )
    assert node_response.status_code == 200
    node = node_response.json()

    event_response = client.post(
        f"/api/projects/{project['id']}/timeline-events",
        json={"title": "进入雾港", "time_label": "第一章", "time_order": 1, "description": "林曜进入雾港。", "participant_node_ids": [node["id"]]},
    )
    assert event_response.status_code == 200

    lore_response = client.post(
        f"/api/projects/{project['id']}/lore",
        json={"type": "地点", "title": "雾港", "content": "林曜抵达的港口城市。"},
    )
    assert lore_response.status_code == 200

    wiki_response = client.get(f"/api/projects/{project['id']}/wiki", params={"q": "林曜"})
    assert wiki_response.status_code == 200
    entries = wiki_response.json()["entries"]
    assert any(entry["kind"] == "node" and entry["title"] == "林曜" for entry in entries)
    assert any(link["kind"] in {"event", "lore"} for entry in entries for link in entry["links"])
