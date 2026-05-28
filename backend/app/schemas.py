from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""


class Project(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, name: str, description: str) -> "Project":
        now = datetime.utcnow()
        return cls(
            id=new_id("project"),
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )


class CreateSourceRequest(BaseModel):
    title: str = Field(min_length=1)
    type: str = "剧情资料"
    content: str = Field(min_length=1)


class Source(BaseModel):
    id: str
    project_id: str
    title: str
    type: str
    content: str
    created_at: datetime

    @classmethod
    def create(cls, project_id: str, title: str, type: str, content: str) -> "Source":
        return cls(
            id=new_id("source"),
            project_id=project_id,
            title=title,
            type=type,
            content=content,
            created_at=datetime.utcnow(),
        )


class CreateNodeRequest(BaseModel):
    name: str = Field(min_length=1)
    type: str = "人物"
    summary: str = ""


class Node(BaseModel):
    id: str
    project_id: str
    name: str
    type: str
    aliases: List[str] = []
    summary: str = ""
    tags: List[str] = []
    importance: int = 50
    current_state: str = ""
    confidence: float = 1.0
    source_refs: List[str] = []

    @classmethod
    def create(cls, project_id: str, name: str, type: str, summary: str) -> "Node":
        return cls(
            id=new_id("node"),
            project_id=project_id,
            name=name,
            type=type,
            summary=summary,
        )


class CreateRelationshipRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    type: str = "关联"
    summary: str = ""


class Relationship(BaseModel):
    id: str
    project_id: str
    source_node_id: str
    target_node_id: str
    type: str
    summary: str = ""
    weight: int = 50
    confidence: float = 1.0
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    source_refs: List[str] = []

    @classmethod
    def create(
        cls,
        project_id: str,
        source_node_id: str,
        target_node_id: str,
        type: str,
        summary: str,
    ) -> "Relationship":
        return cls(
            id=new_id("rel"),
            project_id=project_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            type=type,
            summary=summary,
        )


class LoreEntry(BaseModel):
    id: str
    project_id: str
    type: str
    title: str
    content: str
    related_node_ids: List[str] = []
    related_event_ids: List[str] = []
    confidence: float = 1.0
    source_refs: List[str] = []

    @classmethod
    def create(cls, project_id: str, type: str, title: str, content: str) -> "LoreEntry":
        return cls(
            id=new_id("lore"),
            project_id=project_id,
            type=type,
            title=title,
            content=content,
        )


class CreateTimelineEventRequest(BaseModel):
    title: str = Field(min_length=1)
    time_label: str
    time_order: int = 0
    description: str = ""
    participant_node_ids: List[str] = []


class TimelineEvent(BaseModel):
    id: str
    project_id: str
    title: str
    time_label: str
    time_order: int
    description: str
    participant_node_ids: List[str] = []
    related_lore_ids: List[str] = []
    source_refs: List[str] = []

    @classmethod
    def create(
        cls,
        project_id: str,
        title: str,
        time_label: str,
        time_order: int,
        description: str,
        participant_node_ids: List[str],
    ) -> "TimelineEvent":
        return cls(
            id=new_id("event"),
            project_id=project_id,
            title=title,
            time_label=time_label,
            time_order=time_order,
            description=description,
            participant_node_ids=participant_node_ids,
        )


class GraphResponse(BaseModel):
    nodes: List[Node]
    relationships: List[Relationship]


class PredictionReport(BaseModel):
    project_id: str
    summary: str
    branches: List[str]
    latest_event: str
    open_questions: List[str]


class ExtractionResult(BaseModel):
    project_id: str
    created_nodes: int
    created_relationships: int
    created_lore_entries: int
    created_timeline_events: int
