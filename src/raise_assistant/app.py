from __future__ import annotations

import mimetypes
import re
import shutil
import uuid
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .db import Database
from .classification import DOCUMENT_ROLES, ROLE_LABELS
from .ingestion import IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS, extract_bytes, summarize_parts
from .providers import create_provider, provider_statuses
from .seed import seed_public_guidance
from .workflow import WorkflowService


settings.prepare_directories()
db = Database(settings.database_path)
workflow = WorkflowService(db, settings)

app = FastAPI(title="RAISE Assistant", version="0.1.0", docs_url="/api/docs", redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
STATIC_DIR = settings.app_root / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def enforce_local_origin(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in {
            f"http://127.0.0.1:{settings.port}",
            f"http://localhost:{settings.port}",
        }:
            return Response("Cross-origin write denied", status_code=403)
    return await call_next(request)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    provider: str = "openai"
    model: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    provider: str | None = None
    model: str | None = None


class ChatRequest(BaseModel):
    task: Literal["task1", "task2"]
    message: str = Field(min_length=1, max_length=30000)
    provider: str | None = None
    model: str | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=8)


class ProviderRequest(BaseModel):
    model: str | None = None


class DraftAction(BaseModel):
    task: Literal["task1", "task2"]
    provider: str | None = None
    model: str | None = None


class DraftSave(BaseModel):
    task: Literal["task1", "task2"]
    content: str = Field(max_length=500000)


def _project_or_404(project_id: str) -> dict:
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def _safe_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(400, str(exc))
    return HTTPException(502, f"Model or service request failed: {exc}")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "version": "0.1.0", "storage": str(settings.data_dir)}


@app.get("/api/providers")
def providers() -> list[dict]:
    return provider_statuses(settings)


@app.post("/api/providers/{provider_id}/test")
def test_provider(provider_id: str, request: ProviderRequest) -> dict:
    try:
        provider = create_provider(provider_id, request.model, settings)
        response = provider.test()
        return {"ok": "CONNECTION_OK" in response.upper(), "response": response, "model": provider.model}
    except Exception as exc:
        raise _safe_error(exc) from exc


@app.get("/api/projects")
def list_projects() -> list[dict]:
    return db.list_projects()


@app.post("/api/projects", status_code=201)
def create_project(request: ProjectCreate) -> dict:
    valid = {item["id"] for item in provider_statuses(settings)}
    if request.provider not in valid:
        raise HTTPException(400, "Unknown provider")
    project = db.create_project(request.name, request.description, request.provider, request.model)
    seed_public_guidance(db, project["id"], settings)
    return project


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    project = _project_or_404(project_id)
    project["documents"] = db.list_documents(project_id)
    project["drafts"] = {
        "task1": db.get_draft(project_id, "task1"),
        "task2": db.get_draft(project_id, "task2"),
    }
    return project


@app.patch("/api/projects/{project_id}")
def update_project(project_id: str, request: ProjectUpdate) -> dict:
    _project_or_404(project_id)
    return db.update_project(project_id, **request.model_dump(exclude_none=True)) or {}


@app.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: str) -> Response:
    _project_or_404(project_id)
    project_dir = (settings.uploads_dir / project_id).resolve()
    uploads_root = settings.uploads_dir.resolve()
    if project_dir.parent != uploads_root:
        raise HTTPException(400, "Invalid project storage path")
    db.delete_project(project_id)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    return Response(status_code=204)


@app.get("/api/projects/{project_id}/documents")
def list_documents(project_id: str) -> list[dict]:
    _project_or_404(project_id)
    return db.list_documents(project_id)


@app.post("/api/projects/{project_id}/documents", status_code=201)
def upload_documents(
    project_id: str,
    kind: str = Form("auto"),
    files: list[UploadFile] = File(...),
) -> list[dict]:
    _project_or_404(project_id)
    allowed_kinds = {"auto", *DOCUMENT_ROLES}
    if kind not in allowed_kinds:
        raise HTTPException(400, "Unknown document kind")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    results = []
    project_dir = settings.uploads_dir / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        original_name = Path(upload.filename or "upload").name
        suffix = Path(original_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(400, f"Unsupported file type for {original_name}: {suffix or 'unknown'}")
        data = upload.file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(413, f"{original_name} is larger than {settings.max_upload_mb} MB")
        try:
            parts = extract_bytes(original_name, data)
        except Exception as exc:
            raise HTTPException(400, f"Could not read {original_name}: {exc}") from exc
        mime_type = upload.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        resolved_kind = kind
        classification_method = "selected role"
        if kind == "auto":
            extracted_text = "\n\n".join(part.text for part in parts)
            resolved_kind, classification_method = workflow.classify_upload(
                project_id,
                original_name,
                mime_type,
                extracted_text,
                data if suffix in IMAGE_EXTENSIONS else None,
            )
        stored_name = f"{uuid.uuid4().hex}{suffix}"
        storage_path = project_dir / stored_name
        storage_path.write_bytes(data)
        document = db.add_document(
            project_id,
            original_name,
            resolved_kind,
            mime_type,
            str(storage_path),
            [(part.locator, part.text) for part in parts],
        )
        document["extraction"] = summarize_parts(parts)
        document["image_only"] = suffix in IMAGE_EXTENSIONS
        document["classification_method"] = classification_method
        document["classification_label"] = ROLE_LABELS[resolved_kind]
        if not parts and not document["image_only"]:
            document["warning"] = "No searchable text was extracted. For a scanned document, upload page screenshots and attach them to chat."
        results.append(document)
    return results


@app.get("/api/projects/{project_id}/messages/{task}")
def messages(project_id: str, task: Literal["task1", "task2"]) -> list[dict]:
    _project_or_404(project_id)
    return db.list_messages(project_id, task)


@app.post("/api/projects/{project_id}/chat")
def chat(project_id: str, request: ChatRequest) -> dict:
    _project_or_404(project_id)
    try:
        return workflow.chat(
            project_id,
            request.task,
            request.message,
            request.provider,
            request.model,
            request.attachment_ids,
        )
    except Exception as exc:
        raise _safe_error(exc) from exc


@app.get("/api/projects/{project_id}/draft/{task}")
def get_draft(project_id: str, task: Literal["task1", "task2"]) -> dict:
    _project_or_404(project_id)
    draft = db.get_draft(project_id, task)
    template, official = workflow.get_template(project_id, task)
    return {"draft": draft, "template": template, "official_template_used": official}


@app.put("/api/projects/{project_id}/draft")
def save_draft(project_id: str, request: DraftSave) -> dict:
    _project_or_404(project_id)
    return db.save_draft(project_id, request.task, request.content)


@app.get("/api/projects/{project_id}/draft/{task}/history")
def draft_history(project_id: str, task: Literal["task1", "task2"]) -> list[dict]:
    _project_or_404(project_id)
    return db.list_draft_versions(project_id, task)


@app.post("/api/projects/{project_id}/draft/{task}/restore/{version}")
def restore_draft(project_id: str, task: Literal["task1", "task2"], version: int) -> dict:
    _project_or_404(project_id)
    old = db.get_draft_version(project_id, task, version)
    if not old:
        raise HTTPException(404, "Draft version not found")
    return db.save_draft(project_id, task, old["content"])


@app.post("/api/projects/{project_id}/draft/generate")
def generate_draft(project_id: str, request: DraftAction) -> dict:
    _project_or_404(project_id)
    try:
        return workflow.generate_draft(project_id, request.task, request.provider, request.model)
    except Exception as exc:
        raise _safe_error(exc) from exc


@app.post("/api/projects/{project_id}/draft/review")
def review_draft(project_id: str, request: DraftAction) -> dict:
    _project_or_404(project_id)
    try:
        return workflow.review_draft(project_id, request.task, request.provider, request.model)
    except Exception as exc:
        raise _safe_error(exc) from exc


@app.get("/api/projects/{project_id}/export/{task}")
def export_draft(project_id: str, task: Literal["task1", "task2"]) -> Response:
    project = _project_or_404(project_id)
    draft = db.get_draft(project_id, task)
    if not draft or not draft["content"].strip():
        raise HTTPException(404, "There is no draft to export")
    filename = "discovery.md" if task == "task1" else "spec.md"
    safe_project = re.sub(r"[^A-Za-z0-9_.-]+", "-", project["name"]).strip("-") or "raise-project"
    headers = {"Content-Disposition": f'attachment; filename="{safe_project}-{filename}"'}
    return Response(draft["content"], media_type="text/markdown; charset=utf-8", headers=headers)


def main() -> None:
    if settings.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("RAISE_HOST must be 127.0.0.1 or localhost. This local app does not support network exposure.")
    print(f"\nRAISE Assistant is running at http://{settings.host}:{settings.port}")
    print("Press Ctrl+C to stop.\n")
    uvicorn.run("raise_assistant.app:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()

