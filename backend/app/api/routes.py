from __future__ import annotations

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from app.schemas import (
    CreateNodeRequest,
    CreateProjectRequest,
    CreateRelationshipRequest,
    CreateSourceRequest,
    CreateTimelineEventRequest,
    GraphResponse,
    LoreEntry,
    Node,
    PredictionReport,
    Project,
    Relationship,
    Source,
    TimelineEvent,
)


router = APIRouter()

projects: Dict[str, Project] = {}
sources: Dict[str, List[Source]] = {}
nodes: Dict[str, List[Node]] = {}
relationships: Dict[str, List[Relationship]] = {}
timeline_events: Dict[str, List[TimelineEvent]] = {}
lore_entries: Dict[str, List[LoreEntry]] = {}


def ensure_project(project_id: str) -> Project:
    project = projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/projects")
def list_projects() -> List[Project]:
    return list(projects.values())


@router.post("/projects")
def create_project(payload: CreateProjectRequest) -> Project:
    project = Project.create(name=payload.name, description=payload.description)
    projects[project.id] = project
    sources[project.id] = []
    nodes[project.id] = []
    relationships[project.id] = []
    timeline_events[project.id] = []
    lore_entries[project.id] = []
    return project


@router.get("/projects/{project_id}")
def get_project(project_id: str) -> Project:
    return ensure_project(project_id)


@router.post("/projects/{project_id}/sources")
def add_source(project_id: str, payload: CreateSourceRequest) -> Source:
    ensure_project(project_id)
    source = Source.create(
        project_id=project_id,
        title=payload.title,
        type=payload.type,
        content=payload.content,
    )
    sources[project_id].append(source)
    return source


@router.get("/projects/{project_id}/sources")
def list_sources(project_id: str) -> List[Source]:
    ensure_project(project_id)
    return sources[project_id]


@router.get("/projects/{project_id}/graph")
def get_graph(project_id: str) -> GraphResponse:
    ensure_project(project_id)
    return GraphResponse(nodes=nodes[project_id], relationships=relationships[project_id])


@router.post("/projects/{project_id}/nodes")
def add_node(project_id: str, payload: CreateNodeRequest) -> Node:
    ensure_project(project_id)
    node = Node.create(
        project_id=project_id,
        name=payload.name,
        type=payload.type,
        summary=payload.summary,
    )
    nodes[project_id].append(node)
    return node


@router.post("/projects/{project_id}/relationships")
def add_relationship(project_id: str, payload: CreateRelationshipRequest) -> Relationship:
    ensure_project(project_id)
    existing_ids = {node.id for node in nodes[project_id]}
    if payload.source_node_id not in existing_ids or payload.target_node_id not in existing_ids:
        raise HTTPException(status_code=400, detail="关系两端节点必须存在")
    relationship = Relationship.create(
        project_id=project_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        type=payload.type,
        summary=payload.summary,
    )
    relationships[project_id].append(relationship)
    return relationship


@router.get("/projects/{project_id}/timeline")
def get_timeline(project_id: str) -> List[TimelineEvent]:
    ensure_project(project_id)
    return sorted(timeline_events[project_id], key=lambda event: event.time_order)


@router.post("/projects/{project_id}/timeline-events")
def add_timeline_event(project_id: str, payload: CreateTimelineEventRequest) -> TimelineEvent:
    ensure_project(project_id)
    event = TimelineEvent.create(
        project_id=project_id,
        title=payload.title,
        time_label=payload.time_label,
        time_order=payload.time_order,
        description=payload.description,
        participant_node_ids=payload.participant_node_ids,
    )
    timeline_events[project_id].append(event)
    return event


@router.post("/projects/{project_id}/predictions")
def create_prediction(project_id: str) -> PredictionReport:
    ensure_project(project_id)
    project_nodes = nodes[project_id]
    project_events = sorted(timeline_events[project_id], key=lambda event: event.time_order)
    focus = "、".join(node.name for node in project_nodes[:3]) or "当前世界"
    latest_event = project_events[-1].title if project_events else "尚未建立时间线事件"
    return PredictionReport(
        project_id=project_id,
        summary=f"基于当前图谱，后续剧情应优先围绕 {focus} 的关系变化展开。",
        branches=[
            "关系冲突升级：既有矛盾被新的事件触发，推动主要节点重新站队。",
            "秘密暴露：隐藏设定进入明面，改变角色目标和时间线走向。",
            "外部规则介入：世界观规则或势力压力迫使节点做出选择。",
        ],
        latest_event=latest_event,
        open_questions=[
            "哪些节点拥有不可让步的目标？",
            "当前时间线中哪个事件最可能成为转折点？",
            "哪些世界观规则会限制剧情走向？",
        ],
    )

