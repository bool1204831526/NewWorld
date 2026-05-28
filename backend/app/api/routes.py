from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.extractor import extract_world
from app.schemas import (
    CreateNodeRequest,
    CreateProjectRequest,
    CreateRelationshipRequest,
    CreateSourceRequest,
    CreateTimelineEventRequest,
    ExtractionResult,
    GraphResponse,
    LoreEntry,
    Node,
    PredictionReport,
    Project,
    Relationship,
    Source,
    TimelineEvent,
)
from app.storage import store


router = APIRouter()


def ensure_project(project_id: str) -> Project:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@router.get("/projects")
def list_projects() -> List[Project]:
    return store.list_projects()


@router.post("/projects")
def create_project(payload: CreateProjectRequest) -> Project:
    project = Project.create(name=payload.name, description=payload.description)
    return store.save_project(project)


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
    return store.save_source(source)



SUPPORTED_SOURCE_SUFFIXES = {".txt", ".md", ".markdown"}

def decode_source_file(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 或 GB18030 文本文件")

@router.post("/projects/{project_id}/sources/upload")
async def upload_sources(
    project_id: str,
    files: List[UploadFile] = File(...),
    type: str = Form("剧情资料"),
) -> List[Source]:
    ensure_project(project_id)
    created_sources: List[Source] = []
    for file in files:
        filename = file.filename or "未命名资料.txt"
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_SOURCE_SUFFIXES:
            raise HTTPException(status_code=400, detail=f"暂不支持 {suffix or '无扩展名'} 文件，请上传 txt 或 md")
        content = decode_source_file(await file.read()).strip()
        if not content:
            raise HTTPException(status_code=400, detail=f"{filename} 内容为空")
        title = Path(filename).stem or filename
        source = Source.create(project_id=project_id, title=title, type=type, content=content)
        created_sources.append(store.save_source(source))
    return created_sources

@router.get("/projects/{project_id}/sources")
def list_sources(project_id: str) -> List[Source]:
    ensure_project(project_id)
    return store.list_sources(project_id)


@router.post("/projects/{project_id}/extract")
def extract_project(project_id: str) -> ExtractionResult:
    ensure_project(project_id)
    created_nodes, created_relationships, created_lore_entries, created_timeline_events, processed_sources, skipped_sources = extract_world(project_id, store)
    return ExtractionResult(
        project_id=project_id,
        created_nodes=created_nodes,
        created_relationships=created_relationships,
        created_lore_entries=created_lore_entries,
        created_timeline_events=created_timeline_events,
        processed_sources=processed_sources,
        skipped_sources=skipped_sources,
    )


@router.get("/projects/{project_id}/lore")
def get_lore(project_id: str) -> List[LoreEntry]:
    ensure_project(project_id)
    return store.list_lore_entries(project_id)


@router.get("/projects/{project_id}/graph")
def get_graph(project_id: str) -> GraphResponse:
    ensure_project(project_id)
    return GraphResponse(
        nodes=store.list_nodes(project_id),
        relationships=store.list_relationships(project_id),
    )


@router.post("/projects/{project_id}/nodes")
def add_node(project_id: str, payload: CreateNodeRequest) -> Node:
    ensure_project(project_id)
    node = Node.create(
        project_id=project_id,
        name=payload.name,
        type=payload.type,
        summary=payload.summary,
    )
    return store.save_node(node)



@router.delete("/projects/{project_id}/nodes/{node_id}")
def delete_node(project_id: str, node_id: str) -> dict:
    ensure_project(project_id)
    deleted = store.delete_node(project_id, node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"deleted": True, "node_id": node_id}

@router.post("/projects/{project_id}/relationships")
def add_relationship(project_id: str, payload: CreateRelationshipRequest) -> Relationship:
    ensure_project(project_id)
    existing_ids = {node.id for node in store.list_nodes(project_id)}
    if payload.source_node_id not in existing_ids or payload.target_node_id not in existing_ids:
        raise HTTPException(status_code=400, detail="关系两端节点必须存在")
    relationship = Relationship.create(
        project_id=project_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        type=payload.type,
        summary=payload.summary,
    )
    return store.save_relationship(relationship)


@router.get("/projects/{project_id}/timeline")
def get_timeline(project_id: str) -> List[TimelineEvent]:
    ensure_project(project_id)
    return store.list_timeline_events(project_id)


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
    return store.save_timeline_event(event)


@router.post("/projects/{project_id}/predictions")
def create_prediction(project_id: str) -> PredictionReport:
    ensure_project(project_id)
    project_nodes = store.list_nodes(project_id)
    project_events = store.list_timeline_events(project_id)
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


