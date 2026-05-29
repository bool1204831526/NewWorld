from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.extractor import extract_world, organize_timeline_board_with_llm, organize_timeline_board_with_rules, organize_timeline_flow_with_llm
from app.schemas import (
    CreateLoreEntryRequest,
    CreateNodeRequest,
    CreatePredictionRequest,
    CreateProjectRequest,
    CreateRelationshipRequest,
    CreateSourceRequest,
    CreateTimelineEventRequest,
    ExtractProjectRequest,
    ExtractionResult,
    GraphResponse,
    LoreEntry,
    MergeNodeRequest,
    Node,
    OrganizeTimelineBoardRequest,
    OrganizeTimelineFlowRequest,
    PredictionReport,
    Project,
    Relationship,
    Source,
    TimelineBoard,
    TimelineEvent,
    TimelineFlowEdge,
    TimelineFlowLayout,
    TimelineFlowPosition,
    UpdateNodeRequest,
    UpdateRelationshipRequest,
    WikiEntry,
    WikiLink,
    WikiResponse,
)
from app.storage import store

router = APIRouter()
SUPPORTED_SOURCE_SUFFIXES = {".txt", ".md", ".markdown"}


def ensure_project(project_id: str) -> Project:
    project = store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def sanitize_timeline_flow_layout(project_id: str, payload: TimelineFlowLayout) -> TimelineFlowLayout:
    event_ids = {event.id for event in store.list_timeline_events(project_id)}
    positions = [
        TimelineFlowPosition(event_id=item.event_id, x=max(0, item.x), y=max(0, item.y))
        for item in payload.positions
        if item.event_id in event_ids
    ]
    edge_keys = set()
    edges: List[TimelineFlowEdge] = []
    for edge in payload.edges:
        if edge.source_event_id == edge.target_event_id:
            continue
        if edge.source_event_id not in event_ids or edge.target_event_id not in event_ids:
            continue
        key = (edge.source_event_id, edge.target_event_id)
        if key in edge_keys:
            continue
        edge_keys.add(key)
        edges.append(edge)
    return TimelineFlowLayout(project_id=project_id, positions=positions, edges=edges)


def build_wiki_entries(project_id: str) -> List[WikiEntry]:
    nodes = store.list_nodes(project_id)
    relationships = store.list_relationships(project_id)
    events = store.list_timeline_events(project_id)
    lore_entries = store.list_lore_entries(project_id)
    node_by_id = {node.id: node for node in nodes}
    entries: List[WikiEntry] = []

    for node in nodes:
        links: List[WikiLink] = []
        for relationship in relationships:
            if relationship.source_node_id != node.id and relationship.target_node_id != node.id:
                continue
            other_id = relationship.target_node_id if relationship.source_node_id == node.id else relationship.source_node_id
            other = node_by_id.get(other_id)
            if other:
                links.append(WikiLink(id=other.id, kind="node", title=other.name, relation=relationship.type))
        for event in events:
            if node.id in event.participant_node_ids:
                links.append(WikiLink(id=event.id, kind="event", title=event.title, relation="参与事件"))
        for entry in lore_entries:
            if node.name in entry.title or node.name in entry.content or node.id in entry.related_node_ids:
                links.append(WikiLink(id=entry.id, kind="lore", title=entry.title, relation="相关设定"))
        entries.append(WikiEntry(
            id=node.id,
            kind="node",
            title=node.name,
            type=node.type,
            summary=node.summary or node.current_state,
            content=node.summary or node.current_state or "暂无节点说明",
            links=links,
            source_refs=node.source_refs,
        ))

    for event in events:
        links = [
            WikiLink(id=node_id, kind="node", title=node_by_id[node_id].name, relation="参与节点")
            for node_id in event.participant_node_ids
            if node_id in node_by_id
        ]
        entries.append(WikiEntry(
            id=event.id,
            kind="event",
            title=event.title,
            type=event.time_label,
            summary=event.description,
            content=event.description or "暂无事件描述",
            links=links,
            source_refs=event.source_refs,
        ))

    for entry in lore_entries:
        links = []
        for node in nodes:
            if node.id in entry.related_node_ids or node.name in entry.title or node.name in entry.content:
                links.append(WikiLink(id=node.id, kind="node", title=node.name, relation="相关节点"))
        for event in events:
            if event.id in entry.related_event_ids or event.title in entry.content:
                links.append(WikiLink(id=event.id, kind="event", title=event.title, relation="相关事件"))
        entries.append(WikiEntry(
            id=entry.id,
            kind="lore",
            title=entry.title,
            type=entry.type,
            summary=entry.content[:120],
            content=entry.content,
            links=links,
            source_refs=entry.source_refs,
        ))

    return entries


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


@router.delete("/projects/{project_id}/sources/{source_id}")
def delete_source(project_id: str, source_id: str) -> dict:
    ensure_project(project_id)
    deleted = store.delete_source(project_id, source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="来源资料不存在")
    return {"deleted": True, "source_id": source_id}


@router.post("/projects/{project_id}/extract")
def extract_project(project_id: str, payload: ExtractProjectRequest = ExtractProjectRequest()) -> ExtractionResult:
    ensure_project(project_id)
    if payload.mode == "llm" and not payload.llm:
        raise HTTPException(status_code=400, detail="LLM 抽取需要填写 API 配置")
    try:
        created_nodes, created_relationships, created_lore_entries, created_timeline_events, processed_sources, skipped_sources = extract_world(
            project_id,
            store,
            source_ids=payload.source_ids,
            mode=payload.mode,
            llm_config=payload.llm,
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
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


@router.post("/projects/{project_id}/lore")
def add_lore_entry(project_id: str, payload: CreateLoreEntryRequest) -> LoreEntry:
    ensure_project(project_id)
    entry = LoreEntry.create(project_id=project_id, type=payload.type, title=payload.title, content=payload.content)
    return store.save_lore_entry(entry)


@router.put("/projects/{project_id}/lore/{entry_id}")
def update_lore_entry(project_id: str, entry_id: str, payload: CreateLoreEntryRequest) -> LoreEntry:
    ensure_project(project_id)
    entry = store.get_lore_entry(entry_id)
    if not entry or entry.project_id != project_id:
        raise HTTPException(status_code=404, detail="设定条目不存在")
    updated = entry.model_copy(update={"type": payload.type, "title": payload.title, "content": payload.content})
    return store.save_lore_entry(updated)


@router.delete("/projects/{project_id}/lore/{entry_id}")
def delete_lore_entry(project_id: str, entry_id: str) -> dict:
    ensure_project(project_id)
    deleted = store.delete_lore_entry(project_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="设定条目不存在")
    return {"deleted": True, "entry_id": entry_id}


@router.get("/projects/{project_id}/wiki")
def get_wiki(project_id: str, q: str = "", kind: str = "") -> WikiResponse:
    ensure_project(project_id)
    entries = build_wiki_entries(project_id)
    keyword = q.strip().lower()
    kind_filter = kind.strip().lower()
    if kind_filter:
        entries = [entry for entry in entries if entry.kind == kind_filter]
    if keyword:
        entries = [
            entry for entry in entries
            if keyword in entry.title.lower()
            or keyword in entry.type.lower()
            or keyword in entry.summary.lower()
            or keyword in entry.content.lower()
        ]
    return WikiResponse(project_id=project_id, entries=entries)


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


@router.put("/projects/{project_id}/nodes/{node_id}")
def update_node(project_id: str, node_id: str, payload: UpdateNodeRequest) -> Node:
    ensure_project(project_id)
    node = store.get_node(node_id)
    if not node or node.project_id != project_id:
        raise HTTPException(status_code=404, detail="节点不存在")
    node.name = payload.name.strip()
    node.type = payload.type.strip() or "人物"
    node.summary = payload.summary.strip()
    node.current_state = payload.current_state.strip()
    return store.save_node(node)


@router.post("/projects/{project_id}/nodes/{target_node_id}/merge")
def merge_node(project_id: str, target_node_id: str, payload: MergeNodeRequest) -> Node:
    ensure_project(project_id)
    if target_node_id == payload.source_node_id:
        raise HTTPException(status_code=400, detail="不能合并同一个节点")
    merged = store.merge_node(project_id, target_node_id, payload.source_node_id)
    if not merged:
        raise HTTPException(status_code=404, detail="待合并节点不存在")
    return merged


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


@router.put("/projects/{project_id}/relationships/{relationship_id}")
def update_relationship(project_id: str, relationship_id: str, payload: UpdateRelationshipRequest) -> Relationship:
    ensure_project(project_id)
    relationship = store.get_relationship(relationship_id)
    if not relationship or relationship.project_id != project_id:
        raise HTTPException(status_code=404, detail="关系不存在")
    existing_ids = {node.id for node in store.list_nodes(project_id)}
    if payload.source_node_id not in existing_ids or payload.target_node_id not in existing_ids:
        raise HTTPException(status_code=400, detail="关系两端节点必须存在")
    if payload.source_node_id == payload.target_node_id:
        raise HTTPException(status_code=400, detail="关系两端不能是同一个节点")
    relationship.source_node_id = payload.source_node_id
    relationship.target_node_id = payload.target_node_id
    relationship.type = payload.type.strip() or "关联"
    relationship.summary = payload.summary.strip()
    return store.update_relationship(relationship)


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


@router.put("/projects/{project_id}/timeline-events/{event_id}")
def update_timeline_event(project_id: str, event_id: str, payload: CreateTimelineEventRequest) -> TimelineEvent:
    ensure_project(project_id)
    existing = store.get_timeline_event(event_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(status_code=404, detail="时间线事件不存在")
    existing.title = payload.title
    existing.time_label = payload.time_label
    existing.time_order = payload.time_order
    existing.description = payload.description
    existing.participant_node_ids = payload.participant_node_ids
    return store.update_timeline_event(existing)


@router.delete("/projects/{project_id}/timeline-events/{event_id}")
def delete_timeline_event(project_id: str, event_id: str) -> dict:
    ensure_project(project_id)
    deleted = store.delete_timeline_event(project_id, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="时间线事件不存在")
    layout = store.get_timeline_flow_layout(project_id)
    if layout.has_layout:
        layout.positions = [position for position in layout.positions if position.event_id != event_id]
        layout.edges = [
            edge for edge in layout.edges
            if edge.source_event_id != event_id and edge.target_event_id != event_id
        ]
        store.save_timeline_flow_layout(layout)
    return {"deleted": True, "event_id": event_id}


@router.get("/projects/{project_id}/timeline-board")
def get_timeline_board(project_id: str) -> TimelineBoard:
    ensure_project(project_id)
    return store.get_timeline_board(project_id)


@router.put("/projects/{project_id}/timeline-board")
def save_timeline_board(project_id: str, payload: TimelineBoard) -> TimelineBoard:
    ensure_project(project_id)
    event_ids = {event.id for event in store.list_timeline_events(project_id)}
    lane_ids = {lane.id for lane in payload.lanes}
    payload.project_id = project_id
    payload.placements = [
        placement for placement in payload.placements
        if placement.event_id in event_ids and placement.lane_id in lane_ids
    ]
    return store.save_timeline_board(payload)


@router.post("/projects/{project_id}/timeline-board/organize")
def organize_timeline_board(project_id: str, payload: OrganizeTimelineBoardRequest) -> TimelineBoard:
    ensure_project(project_id)
    events = store.list_timeline_events(project_id)
    if not events:
        raise HTTPException(status_code=400, detail="没有可整理的时间线事件")
    try:
        if payload.mode == "llm":
            if not payload.llm:
                raise ValueError("LLM 整理需要填写 API 配置")
            board = organize_timeline_board_with_llm(project_id, events, payload.llm)
        else:
            board = organize_timeline_board_with_rules(project_id, events, store.list_nodes(project_id))
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
    return store.save_timeline_board(board)


@router.get("/projects/{project_id}/timeline-flow")
def get_timeline_flow(project_id: str) -> TimelineFlowLayout:
    ensure_project(project_id)
    return store.get_timeline_flow_layout(project_id)


@router.put("/projects/{project_id}/timeline-flow")
def save_timeline_flow(project_id: str, payload: TimelineFlowLayout) -> TimelineFlowLayout:
    ensure_project(project_id)
    return store.save_timeline_flow_layout(sanitize_timeline_flow_layout(project_id, payload))


@router.delete("/projects/{project_id}/timeline-flow")
def delete_timeline_flow(project_id: str) -> TimelineFlowLayout:
    ensure_project(project_id)
    return store.delete_timeline_flow_layout(project_id)


@router.post("/projects/{project_id}/timeline-flow/organize")
def organize_timeline_flow(project_id: str, payload: OrganizeTimelineFlowRequest) -> TimelineFlowLayout:
    ensure_project(project_id)
    events = store.list_timeline_events(project_id)
    if not events:
        raise HTTPException(status_code=400, detail="没有可整理的时间线事件")
    try:
        layout = organize_timeline_flow_with_llm(project_id, events, payload.llm)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))
    return store.save_timeline_flow_layout(sanitize_timeline_flow_layout(project_id, layout))


@router.post("/projects/{project_id}/predictions")
def create_prediction(project_id: str, payload: CreatePredictionRequest = CreatePredictionRequest()) -> PredictionReport:
    ensure_project(project_id)
    project_nodes = store.list_nodes(project_id)
    project_events = store.list_timeline_events(project_id)
    relationships = store.list_relationships(project_id)
    lore_entries = store.list_lore_entries(project_id)

    focus_node = None
    if payload.focus_node_id:
        focus_node = next((node for node in project_nodes if node.id == payload.focus_node_id), None)
        if not focus_node:
            raise HTTPException(status_code=404, detail="推演节点不存在")
    elif project_nodes:
        focus_node = project_nodes[0]

    latest_event = project_events[-1].title if project_events else "尚未建立时间线事件"
    if not focus_node:
        return PredictionReport(
            project_id=project_id,
            summary="当前还没有节点。请先建立人物或重要实体，再进行剧情推演。",
            branches=["新增主角节点后，从其目标、阻碍和关系网开始推演。"],
            latest_event=latest_event,
            open_questions=["谁是当前剧情最适合推进的视角节点？"],
        )

    direct_relationships = [
        relationship for relationship in relationships
        if relationship.source_node_id == focus_node.id or relationship.target_node_id == focus_node.id
    ]
    node_by_id = {node.id: node for node in project_nodes}
    related_nodes = []
    for relationship in direct_relationships:
        other_id = relationship.target_node_id if relationship.source_node_id == focus_node.id else relationship.source_node_id
        other = node_by_id.get(other_id)
        if other:
            related_nodes.append(other)

    related_ids = {focus_node.id, *(node.id for node in related_nodes)}
    related_events = [
        event for event in project_events
        if any(node_id in related_ids for node_id in event.participant_node_ids)
    ]
    if not related_events:
        related_events = project_events[-3:]
    related_lore = [
        entry for entry in lore_entries
        if focus_node.name in entry.title or focus_node.name in entry.content or any(node.name in entry.content for node in related_nodes[:3])
    ][:3]

    relation_text = "、".join(
        f"{node_by_id.get(relationship.source_node_id, focus_node).name}-{relationship.type}-{node_by_id.get(relationship.target_node_id, focus_node).name}"
        for relationship in direct_relationships[:5]
    ) or "暂未建立直接关系"
    event_text = "、".join(event.title for event in related_events[-3:]) or latest_event
    lore_text = "、".join(entry.title for entry in related_lore) or "暂无直接关联设定"

    branches = []
    if direct_relationships:
        strongest = direct_relationships[0]
        other_id = strongest.target_node_id if strongest.source_node_id == focus_node.id else strongest.source_node_id
        other = node_by_id.get(other_id)
        if other:
            branches.append(f"关系推进：{focus_node.name} 与 {other.name} 的“{strongest.type}”关系被新事件放大，迫使双方重新选择立场。")
    if related_lore:
        branches.append(f"设定反噬：围绕“{related_lore[0].title}”的规则或秘密浮出水面，改变 {focus_node.name} 的行动代价。")
    branches.append(f"主动选择：{focus_node.name} 从“{event_text}”的后果中发现新目标，开始推动下一阶段剧情。")
    branches.append(f"外部压力：与 {focus_node.name} 相邻的关系网出现断裂，新的势力或人物趁机介入。")

    return PredictionReport(
        project_id=project_id,
        focus_node_id=focus_node.id,
        focus_node_name=focus_node.name,
        summary=f"以 {focus_node.name} 为核心，后续剧情可以从其关系网切入。当前直接关系为：{relation_text}。近期相关事件为：{event_text}。可调用的设定线索为：{lore_text}。",
        branches=branches,
        latest_event=latest_event,
        open_questions=[
            f"{focus_node.name} 当前最想得到或避免的东西是什么？",
            "哪一条关系最适合在下一章发生反转或升级？",
            "已有世界观设定中，哪条规则会限制这个人物的选择？",
        ],
    )
