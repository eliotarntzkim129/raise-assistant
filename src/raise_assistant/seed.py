from __future__ import annotations

from .config import Settings
from .db import Database
from .ingestion import extract_bytes


def seed_public_guidance(db: Database, project_id: str, config: Settings) -> None:
    source = config.app_root / "knowledge" / "public" / "google_architecture_baseline.md"
    if not source.is_file():
        return
    if any(doc["storage_path"] == str(source) for doc in db.list_documents(project_id)):
        return
    parts = extract_bytes(source.name, source.read_bytes())
    db.add_document(
        project_id,
        source.name,
        "reference",
        "text/markdown",
        str(source),
        [(part.locator, part.text) for part in parts],
    )

