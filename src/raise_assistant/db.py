from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _initialize(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT 'openai',
            model TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            kind TEXT NOT NULL,
            mime_type TEXT NOT NULL DEFAULT '',
            storage_path TEXT NOT NULL,
            extracted_chars INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            source TEXT NOT NULL,
            locator TEXT NOT NULL,
            text TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            text,
            source,
            project_id UNINDEXED,
            chunk_id UNINDEXED,
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            task TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            sources_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS drafts (
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            task TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(project_id, task)
        );

        CREATE TABLE IF NOT EXISTS draft_versions (
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            task TEXT NOT NULL,
            version INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(project_id, task, version)
        );

        CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);
        CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project_id);
        CREATE INDEX IF NOT EXISTS idx_messages_project_task ON messages(project_id, task, created_at);
        """
        with self._lock, self.connect() as conn:
            conn.executescript(schema)

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def create_project(self, name: str, description: str, provider: str, model: str) -> dict[str, Any]:
        project_id = str(uuid.uuid4())
        now = utc_now()
        with self._lock, self.connect() as conn:
            conn.execute(
                "INSERT INTO projects(id,name,description,provider,model,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (project_id, name.strip(), description.strip(), provider, model.strip(), now, now),
            )
        return self.get_project(project_id)  # type: ignore[return-value]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._row(conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())

    def update_project(self, project_id: str, **fields: str) -> dict[str, Any] | None:
        allowed = {"name", "description", "provider", "model"}
        changes = {key: value for key, value in fields.items() if key in allowed and value is not None}
        if not changes:
            return self.get_project(project_id)
        changes["updated_at"] = utc_now()
        assignments = ", ".join(f"{key}=?" for key in changes)
        with self._lock, self.connect() as conn:
            conn.execute(
                f"UPDATE projects SET {assignments} WHERE id=?",
                (*changes.values(), project_id),
            )
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> None:
        with self._lock, self.connect() as conn:
            chunk_ids = conn.execute("SELECT id FROM chunks WHERE project_id=?", (project_id,)).fetchall()
            conn.executemany("DELETE FROM chunks_fts WHERE chunk_id=?", [(row[0],) for row in chunk_ids])
            conn.execute("DELETE FROM projects WHERE id=?", (project_id,))

    def add_document(
        self,
        project_id: str,
        filename: str,
        kind: str,
        mime_type: str,
        storage_path: str,
        parts: Iterable[tuple[str, str]],
    ) -> dict[str, Any]:
        document_id = str(uuid.uuid4())
        materialized = [(locator, text) for locator, text in parts if text.strip()]
        extracted_chars = sum(len(text) for _, text in materialized)
        now = utc_now()
        with self._lock, self.connect() as conn:
            conn.execute(
                "INSERT INTO documents(id,project_id,filename,kind,mime_type,storage_path,extracted_chars,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (document_id, project_id, filename, kind, mime_type, storage_path, extracted_chars, now),
            )
            for locator, text in materialized:
                cursor = conn.execute(
                    "INSERT INTO chunks(project_id,document_id,source,locator,text) VALUES(?,?,?,?,?)",
                    (project_id, document_id, filename, locator, text),
                )
                conn.execute(
                    "INSERT INTO chunks_fts(text,source,project_id,chunk_id) VALUES(?,?,?,?)",
                    (text, filename, project_id, cursor.lastrowid),
                )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return self.get_document(document_id)  # type: ignore[return-value]

    def get_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._row(conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone())

    def list_documents(self, project_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC", (project_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def document_path(self, project_id: str, document_id: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT storage_path FROM documents WHERE id=? AND project_id=?", (document_id, project_id)
            ).fetchone()
        return row[0] if row else None

    def search_chunks(
        self, project_id: str, query: str, limit: int, kinds: tuple[str, ...] | None = None
    ) -> list[dict[str, Any]]:
        kind_clause = ""
        parameters: list[Any] = [query, project_id]
        if kinds:
            kind_clause = f" AND d.kind IN ({','.join('?' for _ in kinds)})"
            parameters.extend(kinds)
        parameters.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT c.id, c.document_id, c.source, c.locator, c.text, bm25(chunks_fts) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.chunk_id
                JOIN documents d ON d.id = c.document_id
                WHERE chunks_fts MATCH ? AND chunks_fts.project_id = ?
                {kind_clause}
                ORDER BY rank
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_chunks(
        self, project_id: str, limit: int, kinds: tuple[str, ...] | None = None
    ) -> list[dict[str, Any]]:
        kind_clause = ""
        parameters: list[Any] = [project_id]
        if kinds:
            kind_clause = f" AND d.kind IN ({','.join('?' for _ in kinds)})"
            parameters.extend(kinds)
        parameters.append(limit)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT c.id,c.document_id,c.source,c.locator,c.text,0.0 AS rank
                FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE c.project_id=? {kind_clause}
                ORDER BY c.id DESC LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def chunks_by_kind(self, project_id: str, kind: str, limit: int = 80) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id,c.document_id,c.source,c.locator,c.text,0.0 AS rank
                FROM chunks c
                JOIN documents d ON d.id=c.document_id
                WHERE c.project_id=? AND d.kind=?
                ORDER BY c.id ASC LIMIT ?
                """,
                (project_id, kind, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_message(
        self, project_id: str, task: str, role: str, content: str, sources: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        now = utc_now()
        payload = json.dumps(sources or [], ensure_ascii=False)
        with self._lock, self.connect() as conn:
            conn.execute(
                "INSERT INTO messages(id,project_id,task,role,content,sources_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (message_id, project_id, task, role, content, payload, now),
            )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return {"id": message_id, "project_id": project_id, "task": task, "role": role, "content": content, "sources": sources or [], "created_at": now}

    def list_messages(self, project_id: str, task: str, limit: int = 60) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM messages WHERE project_id=? AND task=? ORDER BY created_at DESC LIMIT ?
                ) ORDER BY created_at ASC
                """,
                (project_id, task, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["sources"] = json.loads(item.pop("sources_json"))
            result.append(item)
        return result

    def get_draft(self, project_id: str, task: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._row(
                conn.execute("SELECT * FROM drafts WHERE project_id=? AND task=?", (project_id, task)).fetchone()
            )

    def save_draft(self, project_id: str, task: str, content: str) -> dict[str, Any]:
        current = self.get_draft(project_id, task)
        if current and current["content"] == content:
            return current
        version = int(current["version"]) + 1 if current else 1
        now = utc_now()
        with self._lock, self.connect() as conn:
            conn.execute(
                """
                INSERT INTO drafts(project_id,task,content,version,updated_at) VALUES(?,?,?,?,?)
                ON CONFLICT(project_id,task) DO UPDATE SET content=excluded.content, version=excluded.version, updated_at=excluded.updated_at
                """,
                (project_id, task, content, version, now),
            )
            conn.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
            conn.execute(
                "INSERT INTO draft_versions(project_id,task,version,content,created_at) VALUES(?,?,?,?,?)",
                (project_id, task, version, content, now),
            )
        return self.get_draft(project_id, task)  # type: ignore[return-value]

    def list_draft_versions(self, project_id: str, task: str, limit: int = 30) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT project_id,task,version,created_at,length(content) AS characters
                FROM draft_versions WHERE project_id=? AND task=?
                ORDER BY version DESC LIMIT ?
                """,
                (project_id, task, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_draft_version(self, project_id: str, task: str, version: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            return self._row(
                conn.execute(
                    "SELECT * FROM draft_versions WHERE project_id=? AND task=? AND version=?",
                    (project_id, task, version),
                ).fetchone()
            )

