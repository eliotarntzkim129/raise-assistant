from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .classification import (
    CLASSIFIER_SYSTEM,
    classification_prompt,
    obvious_role,
    parse_model_role,
    safe_fallback_role,
)
from .config import Settings, settings
from .db import Database
from .prompts import chat_prompt, draft_prompt, review_prompt, system_prompt
from .providers import create_provider
from .providers.base import ImageInput
from .retrieval import format_context, retrieve
from .templates import fallback_template, template_kind


def _heading_key(level: str, title: str) -> str:
    numbered = re.match(r"\s*(\d+(?:\.\d+)*)\.?\s+", title)
    if numbered:
        return f"{len(level)}:{numbered.group(1)}"
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
    return f"{len(level)}:{normalized}"


def _markdown_heading_keys(content: str) -> set[str]:
    return {
        _heading_key(match.group(1), match.group(2))
        for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", content, flags=re.MULTILINE)
    }


def _missing_template_headings(template: str, draft: str) -> list[str]:
    actual = _markdown_heading_keys(draft)
    missing = []
    for match in re.finditer(r"^(#{1,6})\s+(.+?)\s*$", template, flags=re.MULTILINE):
        if _heading_key(match.group(1), match.group(2)) not in actual:
            missing.append(match.group(2).strip())
    return missing


FACET_QUERIES = {
    "task1": [
        "business outcomes objectives success metrics stakeholders users",
        "current state pain points workflow systems dependencies",
        "functional requirements scope priorities acceptance criteria",
        "security identity privacy compliance data residency retention",
        "availability performance scale reliability operations observability",
        "risks constraints assumptions unknowns open questions",
    ],
    "task2": [
        "requirements goals non-goals acceptance criteria",
        "architecture components agent model tools memory routing",
        "data sources grounding integrations connectors access control",
        "identity IAM security privacy compliance responsible AI",
        "reliability performance scalability quotas failure recovery",
        "observability tracing evaluation operations deployment cost tradeoffs",
    ],
}


class WorkflowService:
    def __init__(self, db: Database, config: Settings = settings):
        self.db = db
        self.config = config

    @staticmethod
    def validate_task(task: str) -> None:
        if task not in {"task1", "task2"}:
            raise ValueError("task must be task1 or task2")

    def _provider(self, project: dict[str, Any], provider: str | None, model: str | None):
        provider_id = provider or project["provider"]
        chosen_model = model or project["model"] or None
        return provider_id, chosen_model, create_provider(provider_id, chosen_model, self.config)

    def classify_upload(
        self,
        project_id: str,
        filename: str,
        mime_type: str,
        text: str,
        image_data: bytes | None = None,
    ) -> tuple[str, str]:
        role = obvious_role(filename, text)
        if role:
            return role, "automatic rules"

        project = self.db.get_project(project_id)
        if project:
            try:
                _provider_id, _model, client = self._provider(project, None, None)
                images = [ImageInput(image_data, mime_type)] if image_data and mime_type.startswith("image/") else None
                response = client.generate(
                    CLASSIFIER_SYSTEM,
                    classification_prompt(filename, mime_type, text),
                    images,
                )
                role = parse_model_role(response)
                if role:
                    return role, "project model"
            except Exception:
                pass
        return safe_fallback_role(filename, text), "safe fallback"

    def _history(self, project_id: str, task: str) -> str:
        messages = self.db.list_messages(project_id, task, limit=12)
        return "\n\n".join(f"{item['role'].upper()}: {item['content']}" for item in messages)[-16000:]

    def _images(self, project_id: str, document_ids: list[str]) -> list[ImageInput]:
        images = []
        for document_id in document_ids[:8]:
            path_value = self.db.document_path(project_id, document_id)
            if not path_value:
                continue
            path = Path(path_value)
            suffix = path.suffix.lower()
            mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(suffix)
            if mime and path.is_file():
                images.append(ImageInput(path.read_bytes(), mime))
        return images

    def _image_context(self, project_id: str, document_ids: list[str], start: int) -> tuple[str, list[dict[str, Any]]]:
        blocks = []
        sources = []
        for document_id in document_ids[:8]:
            document = self.db.get_document(document_id)
            if not document or document["project_id"] != project_id or not document["mime_type"].startswith("image/"):
                continue
            tag = f"S{start + len(sources)}"
            blocks.append(f"[{tag}] Attached screenshot: {document['filename']}. Inspect the attached image before using it as evidence.")
            sources.append({"id": tag, "document_id": document_id, "source": document["filename"], "locator": "attached screenshot"})
        return "\n".join(blocks), sources

    def _review_image_context(self, project_id: str, limit: int = 8) -> tuple[str, list[dict[str, Any]], list[str]]:
        documents = [
            document
            for document in self.db.list_documents(project_id)
            if document["kind"] in {"feedback", "review_only"}
            and document["mime_type"].startswith("image/")
        ][:limit]
        blocks = []
        sources = []
        document_ids = []
        for index, document in enumerate(documents, start=1):
            tag = f"R{index}"
            blocks.append(
                f"[{tag}] Attached review-only screenshot: {document['filename']}. "
                "Inspect it for assessor expectations or earlier mistakes only; never use it as proof of a customer fact."
            )
            sources.append(
                {
                    "id": tag,
                    "document_id": document["id"],
                    "source": document["filename"],
                    "locator": "attached review-only screenshot",
                }
            )
            document_ids.append(document["id"])
        return "\n".join(blocks), sources, document_ids

    def chat(
        self,
        project_id: str,
        task: str,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        attachment_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        self.validate_task(task)
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        history = self._history(project_id, task)
        self.db.add_message(project_id, task, "user", message)
        chunks = retrieve(self.db, project_id, message, self.config.retrieval_limit)
        if task == "task2":
            approved = self.db.chunks_by_kind(project_id, "discovery_approved", limit=12)
            if approved:
                approved_ids = {item["id"] for item in approved}
                chunks = approved + [item for item in chunks if item["id"] not in approved_ids]
            else:
                working = self.db.get_draft(project_id, "task1")
                if working and working["content"].strip():
                    chunks.insert(0, {
                        "id": -1,
                        "document_id": "task1-draft",
                        "source": "Unapproved Task 1 working draft",
                        "locator": "current discovery.md — verify before submission",
                        "text": working["content"],
                        "rank": -999,
                    })
        context, sources = format_context(chunks)
        image_context, image_sources = self._image_context(project_id, attachment_ids or [], len(sources) + 1)
        if image_context:
            context = f"{context}\n\n{image_context}" if context else image_context
            sources.extend(image_sources)
        provider_id, chosen_model, client = self._provider(project, provider, model)
        response = client.generate(
            system_prompt(task),
            chat_prompt(message, context, history),
            self._images(project_id, attachment_ids or []),
        )
        assistant_message = self.db.add_message(project_id, task, "assistant", response, sources)
        assistant_message["provider"] = provider_id
        assistant_message["model"] = chosen_model or client.model
        return assistant_message

    def _draft_context(self, project_id: str, task: str) -> tuple[str, list[dict[str, Any]]]:
        seen: set[int] = set()
        chunks: list[dict[str, Any]] = []
        for query in FACET_QUERIES[task]:
            for chunk in retrieve(self.db, project_id, query, 10):
                if chunk["id"] not in seen:
                    seen.add(chunk["id"])
                    chunks.append(chunk)
        if task == "task2":
            approved = self.db.chunks_by_kind(project_id, "discovery_approved", limit=30)
            if approved:
                chunks = approved + [chunk for chunk in chunks if chunk["id"] not in {item["id"] for item in approved}]
            task1_draft = self.db.get_draft(project_id, "task1")
            if not approved and task1_draft and task1_draft["content"].strip():
                chunks.insert(
                    0,
                    {
                        "id": -1,
                        "document_id": "task1-draft",
                        "source": "Unapproved Task 1 working draft",
                        "locator": "current discovery.md — verify before submission",
                        "text": task1_draft["content"],
                        "rank": -999,
                    },
                )
        return format_context(chunks, max_chars=90000)

    def get_template(self, project_id: str, task: str) -> tuple[str, bool]:
        self.validate_task(task)
        uploaded = self.db.chunks_by_kind(project_id, template_kind(task))
        if uploaded:
            return "\n\n".join(chunk["text"] for chunk in uploaded), True
        return fallback_template(task), False

    def generate_draft(
        self,
        project_id: str,
        task: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        self.validate_task(task)
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError("Project not found")
        template, official = self.get_template(project_id, task)
        context, sources = self._draft_context(project_id, task)
        provider_id, chosen_model, client = self._provider(project, provider, model)
        content = client.generate(system_prompt(task), draft_prompt(task, template, context))
        missing_headings = _missing_template_headings(template, content)
        if missing_headings:
            preview = ", ".join(missing_headings[:6])
            more = f" and {len(missing_headings) - 6} more" if len(missing_headings) > 6 else ""
            raise RuntimeError(
                f"The model returned an incomplete draft. Missing required sections: {preview}{more}. "
                "No partial draft was saved; try Generate again."
            )
        draft = self.db.save_draft(project_id, task, content)
        draft.update({"sources": sources, "official_template_used": official, "provider": provider_id, "model": chosen_model or client.model})
        return draft

    def review_draft(
        self,
        project_id: str,
        task: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        self.validate_task(task)
        project = self.db.get_project(project_id)
        draft = self.db.get_draft(project_id, task)
        if not project:
            raise ValueError("Project not found")
        if not draft or not draft["content"].strip():
            raise ValueError("There is no draft to review yet.")
        context, sources = self._draft_context(project_id, task)
        review_material = []
        for kind in ("feedback", "review_only"):
            review_material.extend(self.db.chunks_by_kind(project_id, kind, limit=30))
        review_guidance = "\n\n".join(
            f"[{item['source']} — {item['locator']}]\n{item['text']}" for item in review_material
        )[-50000:]
        image_guidance, image_sources, review_image_ids = self._review_image_context(project_id)
        if image_guidance:
            review_guidance = f"{review_guidance}\n\n{image_guidance}" if review_guidance else image_guidance
            sources.extend(image_sources)
        template, _official = self.get_template(project_id, task)
        provider_id, chosen_model, client = self._provider(project, provider, model)
        review = client.generate(
            system_prompt(task),
            review_prompt(task, draft["content"], context, review_guidance, template),
            self._images(project_id, review_image_ids),
        )
        message = self.db.add_message(project_id, task, "assistant", review, sources)
        message.update({"provider": provider_id, "model": chosen_model or client.model})
        return message

