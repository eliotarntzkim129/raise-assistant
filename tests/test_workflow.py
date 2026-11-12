from __future__ import annotations

import io
import re
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raise_assistant.config import settings
from raise_assistant.db import Database
from raise_assistant.ingestion import extract_bytes
from raise_assistant.retrieval import format_context, retrieve
from raise_assistant.seed import seed_public_guidance
from raise_assistant.workflow import WorkflowService
from raise_assistant.templates import fallback_template


class FakeProvider:
    model = "fake-model"
    calls: list[tuple[str, str, int]] = []

    def generate(self, system, prompt, images=None):
        self.calls.append((system, prompt, len(images or [])))
        if "CLASSIFY_DOCUMENT_ROLE" in prompt:
            return "brief"
        if "strict assessor" in prompt:
            return "Readiness: Needs work — confirm REQ-001."
        if "complete working draft" in prompt:
            template = re.search(r"<template>\n(.*?)\n</template>", prompt, flags=re.DOTALL)
            document = template.group(1) if template else "# Working draft"
            requirement = "Requirement REQ-001 is supported by [S1]." if "discovery.md" in prompt else "REQ-001 maps to a control [S1]."
            return f"{document}\n\n{requirement}"
        return "The customer requires audit logs [S1]."


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    from raise_assistant import app as app_module
    import raise_assistant.workflow as workflow_module

    config = replace(settings, data_dir=tmp_path / "data", app_root=settings.app_root)
    database = Database(config.database_path)
    service = WorkflowService(database, config)
    fake = FakeProvider()
    fake.calls = []
    monkeypatch.setattr(workflow_module, "create_provider", lambda *_args, **_kwargs: fake)
    monkeypatch.setattr(app_module, "db", database)
    monkeypatch.setattr(app_module, "workflow", service)
    monkeypatch.setattr(app_module, "settings", config)
    return TestClient(app_module.app, base_url="http://127.0.0.1:8765"), database, service, fake


def test_upload_retrieve_chat_draft_and_export(isolated):
    client, database, _, fake = isolated
    home = client.get("/").text
    assert "RAISE Assistant" in home
    assert "Supporting documents" in home
    assert 'id="documentKind"' not in home
    assert 'id="previewDraftButton"' in home
    assert 'id="draftPreview"' in home
    assert 'id="deleteProjectButton"' in home
    app_javascript = client.get("/static/app.js")
    assert app_javascript.status_code == 200
    assert "function renderMarkdown" in app_javascript.text
    created = client.post("/api/projects", json={"name": "AeroGlobal", "provider": "openai"})
    assert created.status_code == 201
    project_id = created.json()["id"]
    assert any(doc["filename"] == "google_architecture_baseline.md" for doc in database.list_documents(project_id))

    evidence = b"REQ-001: The customer requires tamper-evident audit logs and a 30-day review window."
    uploaded = client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "customer"},
        files=[("files", ("customer.md", evidence, "text/markdown"))],
    )
    assert uploaded.status_code == 201
    assert uploaded.json()[0]["extraction"]["characters"] == len(evidence)

    context, sources = format_context(retrieve(database, project_id, "audit logs", 5))
    assert "tamper-evident" in context
    assert any(source["source"] == "customer.md" for source in sources)

    chat = client.post(
        f"/api/projects/{project_id}/chat",
        json={"task": "task1", "message": "What are the audit log requirements?"},
    )
    assert chat.status_code == 200
    assert chat.json()["content"].startswith("The customer requires")
    assert len(database.list_messages(project_id, "task1")) == 2
    assert "customer.md" in fake.calls[-1][1]

    draft = client.post(f"/api/projects/{project_id}/draft/generate", json={"task": "task1"})
    assert draft.status_code == 200
    assert "REQ-001" in draft.json()["content"]
    assert draft.json()["official_template_used"] is False
    review = client.post(f"/api/projects/{project_id}/draft/review", json={"task": "task1"})
    assert review.status_code == 200
    assert "Needs work" in review.json()["content"]
    export = client.get(f"/api/projects/{project_id}/export/task1")
    assert export.status_code == 200
    assert "discovery.md" in export.headers["content-disposition"]
    assert "# Discovery" in export.text
    changed = client.put(
        f"/api/projects/{project_id}/draft",
        json={"task": "task1", "content": "# Human edited discovery"},
    )
    assert changed.json()["version"] == 2
    history = client.get(f"/api/projects/{project_id}/draft/task1/history").json()
    assert [item["version"] for item in history] == [2, 1]
    restored = client.post(f"/api/projects/{project_id}/draft/task1/restore/1")
    assert restored.json()["version"] == 3
    assert "REQ-001" in restored.json()["content"]


def test_supporting_documents_are_automatically_classified(isolated):
    client, _, _, fake = isolated
    project_id = client.post("/api/projects", json={"name": "Auto roles", "provider": "openai"}).json()["id"]

    template = client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "auto"},
        files=[(
            "files",
            (
                "Discovery Document Template.md",
                b"# Discovery Document\n\n## 1. Document Control\n\n## 15. Appendix\n",
                "text/markdown",
            ),
        )],
    )
    assert template.status_code == 201
    assert template.json()[0]["kind"] == "template_task1"
    assert template.json()[0]["classification_method"] == "automatic rules"

    instructions = client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "auto"},
        files=[("files", ("packet.txt", b"Complete the assessment within the allotted time.", "text/plain"))],
    )
    assert instructions.status_code == 201
    assert instructions.json()[0]["kind"] == "brief"
    assert instructions.json()[0]["classification_method"] == "project model"
    assert "CLASSIFY_DOCUMENT_ROLE" in fake.calls[-1][1]


def test_delete_project_removes_records_and_uploaded_files(isolated):
    client, database, _, _fake = isolated
    project_id = client.post("/api/projects", json={"name": "Temporary", "provider": "openai"}).json()["id"]
    upload = client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "customer"},
        files=[("files", ("temporary.md", b"Temporary customer evidence.", "text/markdown"))],
    ).json()[0]
    uploaded_path = Path(upload["storage_path"])
    assert uploaded_path.exists()

    deleted = client.delete(f"/api/projects/{project_id}")

    assert deleted.status_code == 204
    assert database.get_project(project_id) is None
    assert database.get_document(upload["id"]) is None
    assert not uploaded_path.parent.exists()
    assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_approved_discovery_precedes_working_draft_and_official_template(isolated):
    client, database, service, fake = isolated
    project_id = client.post("/api/projects", json={"name": "Case", "provider": "openai"}).json()["id"]
    database.save_draft(project_id, "task1", "Draft discovery, pending approval")
    approved = b"# Approved discovery\n\nREQ-101: User identity must be federated."
    response = client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "discovery_approved"},
        files=[("files", ("approved.md", approved, "text/markdown"))],
    )
    assert response.status_code == 201
    template = b"# Official spec\n\n## Required checkpoint A"
    response = client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "template_task2"},
        files=[("files", ("official.md", template, "text/markdown"))],
    )
    assert response.status_code == 201

    result = service.generate_draft(project_id, "task2")
    assert result["official_template_used"] is True
    prompt = fake.calls[-1][1]
    assert "Required checkpoint A" in prompt
    assert "REQ-101" in prompt
    assert "Draft discovery, pending approval" not in prompt


def test_feedback_and_failed_submission_are_review_only(isolated):
    client, database, service, fake = isolated
    project_id = client.post("/api/projects", json={"name": "Isolation", "provider": "openai"}).json()["id"]
    client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "customer"},
        files=[("files", ("customer.md", b"The customer needs auditable operations.", "text/markdown"))],
    )
    client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "feedback"},
        files=[("files", ("feedback.md", b"Flag fabricated quotations and oversized Phase 1 scope.", "text/markdown"))],
    )
    client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "review_only"},
        files=[("files", ("failed.md", b"Invented claim: the budget is exactly 999 million dollars.", "text/markdown"))],
    )
    client.post(
        f"/api/projects/{project_id}/documents",
        data={"kind": "feedback"},
        files=[("files", ("feedback-screenshot.jpg", b"image bytes", "image/jpeg"))],
    )

    context, _ = format_context(retrieve(database, project_id, "budget quotations Phase scope", 10))
    assert "999 million" not in context
    assert "fabricated quotations" not in context

    database.save_draft(project_id, "task1", "# Discovery\n\nThe customer needs auditable operations.")
    service.review_draft(project_id, "task1")
    review_prompt_text = fake.calls[-1][1]
    assert "fabricated quotations" in review_prompt_text
    assert "999 million" in review_prompt_text
    assert "Never cite it as proof of a customer fact" in review_prompt_text
    assert "Never reproduce a colleague's or prior participant's submission" in fake.calls[-1][0]
    assert "## 15. Appendix" in review_prompt_text
    assert "Attached review-only screenshot: feedback-screenshot.jpg" in review_prompt_text
    assert fake.calls[-1][2] == 1


def test_images_are_project_scoped_and_origin_guard(isolated):
    client, database, _, fake = isolated
    first = client.post("/api/projects", json={"name": "First", "provider": "openai"}).json()["id"]
    second = client.post("/api/projects", json={"name": "Second", "provider": "openai"}).json()["id"]
    image = client.post(
        f"/api/projects/{first}/documents",
        data={"kind": "customer"},
        files=[("files", ("screenshot.png", b"image bytes", "image/png"))],
    ).json()[0]

    foreign = client.post(
        f"/api/projects/{second}/chat",
        json={"task": "task1", "message": "Read this image", "attachment_ids": [image["id"]]},
    )
    assert foreign.status_code == 200
    assert fake.calls[-1][2] == 0

    own = client.post(
        f"/api/projects/{first}/chat",
        json={"task": "task1", "message": "Read this image", "attachment_ids": [image["id"]]},
    )
    assert own.status_code == 200
    assert fake.calls[-1][2] == 1
    assert any(source["source"] == "screenshot.png" for source in own.json()["sources"])

    denied = client.post(
        "/api/projects",
        json={"name": "Bad origin"},
        headers={"Origin": "https://malicious.example"},
    )
    assert denied.status_code == 403


def test_zip_rejects_traversal_and_large_metadata():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../outside.md", "secret")
    with pytest.raises(ValueError, match="Unsafe ZIP path"):
        extract_bytes("bad.zip", output.getvalue())


def test_discovery_fallback_matches_all_visible_official_sections():
    template = fallback_template("task1")
    assert "## 5. Functional Requirements Register" in template
    assert "## 11. Prioritization Method & Ranked Backlog" in template
    assert "## 14. Traceability Matrix (Artifact → Requirements)" in template
    assert "## 15. Appendix" in template
    assert "### 15.1 Glossary of domain terms" in template
    assert "### 15.2 Additional notes or context" in template
    assert "Official-template section unavailable" not in template


def test_incomplete_generated_draft_does_not_overwrite_saved_work(isolated):
    client, database, _, fake = isolated
    project_id = client.post("/api/projects", json={"name": "Completeness", "provider": "openai"}).json()["id"]
    database.save_draft(project_id, "task1", "# Existing human draft")
    fake.generate = lambda _system, _prompt, _images=None: "# Discovery Document\n\n## 1. Document Control"

    response = client.post(f"/api/projects/{project_id}/draft/generate", json={"task": "task1"})

    assert response.status_code == 502
    assert "No partial draft was saved" in response.json()["detail"]
    assert database.get_draft(project_id, "task1")["content"] == "# Existing human draft"

