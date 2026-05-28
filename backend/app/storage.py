from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel

from app.schemas import LoreEntry, Node, Project, Relationship, Source, TimelineEvent

T = TypeVar("T", bound=BaseModel)

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "newworld.db"

class SQLiteStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        configured = os.getenv("NEWWORLD_DB_PATH")
        self.db_path = Path(configured) if configured else db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS timeline_events (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    time_order INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );

                CREATE TABLE IF NOT EXISTS lore_entries (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
                """
            )

    def reset(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                DELETE FROM timeline_events;
                DELETE FROM lore_entries;
                DELETE FROM relationships;
                DELETE FROM nodes;
                DELETE FROM sources;
                DELETE FROM projects;
                """
            )

    def save_project(self, project: Project) -> Project:
        data = serialize(project)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO projects (id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at
                """,
                (project.id, data, project.created_at.isoformat(), project.updated_at.isoformat()),
            )
        return project

    def list_projects(self) -> List[Project]:
        with self.connect() as connection:
            rows = connection.execute("SELECT data FROM projects ORDER BY created_at ASC").fetchall()
        return parse_many(Project, rows)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._get_one(Project, "projects", project_id)

    def save_source(self, source: Source) -> Source:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO sources (id, project_id, data, created_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET data = excluded.data
                """,
                (source.id, source.project_id, serialize(source), source.created_at.isoformat()),
            )
        return source

    def list_sources(self, project_id: str) -> List[Source]:
        return self._list_by_project(Source, "sources", project_id, "created_at ASC")


    def mark_source_extracted(self, source: Source) -> Source:
        self.save_source(source)
        return source

    def save_node(self, node: Node) -> Node:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO nodes (id, project_id, data) VALUES (?, ?, ?)",
                (node.id, node.project_id, serialize(node)),
            )
        return node

    def list_nodes(self, project_id: str) -> List[Node]:
        return self._list_by_project(Node, "nodes", project_id, "id ASC")

    def save_relationship(self, relationship: Relationship) -> Relationship:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO relationships (id, project_id, source_node_id, target_node_id, data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    relationship.id,
                    relationship.project_id,
                    relationship.source_node_id,
                    relationship.target_node_id,
                    serialize(relationship),
                ),
            )
        return relationship

    def list_relationships(self, project_id: str) -> List[Relationship]:
        return self._list_by_project(Relationship, "relationships", project_id, "id ASC")

    def save_lore_entry(self, entry: LoreEntry) -> LoreEntry:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO lore_entries (id, project_id, type, data) VALUES (?, ?, ?, ?)",
                (entry.id, entry.project_id, entry.type, serialize(entry)),
            )
        return entry

    def list_lore_entries(self, project_id: str) -> List[LoreEntry]:
        return self._list_by_project(LoreEntry, "lore_entries", project_id, "id ASC")

    def save_timeline_event(self, event: TimelineEvent) -> TimelineEvent:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO timeline_events (id, project_id, time_order, data) VALUES (?, ?, ?, ?)",
                (event.id, event.project_id, event.time_order, serialize(event)),
            )
        return event

    def list_timeline_events(self, project_id: str) -> List[TimelineEvent]:
        return self._list_by_project(TimelineEvent, "timeline_events", project_id, "time_order ASC")

    def _get_one(self, model: Type[T], table: str, item_id: str) -> Optional[T]:
        with self.connect() as connection:
            row = connection.execute(f"SELECT data FROM {table} WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        return parse_one(model, row["data"])

    def _list_by_project(self, model: Type[T], table: str, project_id: str, order_by: str) -> List[T]:
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT data FROM {table} WHERE project_id = ? ORDER BY {order_by}",
                (project_id,),
            ).fetchall()
        return parse_many(model, rows)

def serialize(model: BaseModel) -> str:
    return model.model_dump_json()

def parse_one(model: Type[T], data: str) -> T:
    return model.model_validate_json(data)

def parse_many(model: Type[T], rows: Sequence[sqlite3.Row]) -> List[T]:
    return [parse_one(model, row["data"]) for row in rows]

store = SQLiteStore()

