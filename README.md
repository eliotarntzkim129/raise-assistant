# RAISE Assistant

RAISE Assistant is a private, local workspace for two connected assessment tasks:

1. **Task 1 — Discovery:** turn customer evidence into a traceable `discovery.md`.
2. **Task 2 — Solution design:** turn the approved discovery into a defensible `spec.md`.

It supports chat, screenshots, source uploads, local session memory, grounded drafting, review, and Markdown export. The application runs on the user's computer; API keys and uploaded customer files are not sent to this repository.
Drafts have local revision history, so a generated replacement can be restored later.

Each new project includes a short public Google architecture reference. Upload the actual assessment's customer artifacts, briefs, internal decks, and feedback to ground customer-specific answers; private materials are never committed by the app.

Document roles are enforced in retrieval:

- **Customer evidence, task brief, references, and approved discovery** may ground factual claims.
- **Official templates** control output structure but are not factual evidence.
- **RAISE feedback** controls review criteria but is not factual evidence.
- **Prior submission — review only** can teach the reviewer what to flag, but it is never retrieved as grounding and must not be copied into a new draft.

This separation also enforces the assessment-integrity instruction visible in the portal: model assistance may support the work, but the final deliverable must be the participant's independent synthesis rather than a reproduction of another participant's submission.

> Important: the included document structures are clearly labeled working fallbacks. The Task 1 fallback reconstructs all 15 sections visible in the supplied official-template screenshots. The Task 2 fallback is generic because the source export contains only the Task 2 portal overview, not its Markdown template. Upload the original RAISE templates when available; the app will use them instead.

Image-only uploads are saved but are not searchable text. Attach customer screenshots to chat when discussing them. Feedback and prior-submission screenshots are automatically supplied to **Review readiness** (up to eight images) and remain review-only; they never enter factual retrieval.

## Fastest setup (macOS or Linux)

```bash
cd raise-assistant
bash setup.sh
bash run.sh
```

The setup wizard asks which providers to configure. A user needs only one working provider. Open the address printed by `run.sh` (normally `http://127.0.0.1:8765`). Running with `bash` works for Git clones and downloaded ZIP archives even if executable file permissions were not preserved.

## Windows PowerShell

```powershell
cd raise-assistant
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
.\run.ps1
```

## Provider choices

| Choice | Local requirement | Cloud administrator may be needed |
|---|---|---|
| OpenAI API | `OPENAI_API_KEY` | No |
| Anthropic API | `ANTHROPIC_API_KEY` | No |
| Gemini API | `GEMINI_API_KEY` | No |
| Gemini on Vertex AI | Google ADC + project/location | Possibly |
| Claude on Vertex AI Model Garden | Google ADC + project/location + enabled model | Usually |

Keys are stored only in `.env`, which Git ignores. The browser never receives them.

## Vertex AI: the safe two-step setup

Google separates project authorization from workstation login. This app does too.

### A. One-time project bootstrap (authorized user or administrator)

Run in Google Cloud Shell:

```bash
bash scripts/gcp_bootstrap.sh \
  --project YOUR_PROJECT_ID \
  --principal user:PERSON@COMPANY.COM
```

The script enables Vertex AI and attempts to grant the standard Vertex AI User and Service Usage Consumer roles. If organization policy, reseller restrictions, or missing IAM authority blocks it, the script writes `gcp-admin-request.txt` with the remaining request. It cannot bypass organization policy.

Claude Model Garden access can additionally require an authorized person to open its model card and accept the provider terms. Model availability and allowed regions are organization-specific.

### B. One-time local login (the person running the app)

Run on the same computer as this app:

```bash
bash scripts/gcp_local_auth.sh --project YOUR_PROJECT_ID
```

This uses Application Default Credentials. Do not create or email a service-account JSON key unless the organization's security team explicitly requires it.

Then set the project, locations, and exact model IDs in `.env`, or rerun:

```bash
.venv/bin/python scripts/configure.py
```

## Check a broken installation

```bash
bash doctor.sh
```

The doctor never prints secret values. It checks Python, configuration, Google credentials, writable storage, and optional live model calls.

## Closed or restricted environments

- The installer honors `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`, and proxy variables supplied by the organization.
- Package installation still requires access to an approved Python package index or a prepared wheelhouse.
- Vertex AI may be blocked by `constraints/vertexai.allowedModels`, service restrictions, or unaccepted partner-model terms. Only the Google Cloud administrator can change these controls.
- Keep the server bound to `127.0.0.1`. Do not expose it to a shared network without adding authentication and TLS.

## What is stored locally

- `data/raise.db`: projects, messages, drafts, citations, and document text.
- `data/uploads/`: original uploaded files.
- `exports/`: generated Markdown exports.

All three locations are excluded from Git. To move work safely, use the app's project export and follow the organization's data-handling policy.

## Typical workflow

1. Create a project and choose a provider/model.
2. Upload the customer source pack, task brief, and official template if available.
3. Work in **Task 1** until every claim is traceable and unknowns are explicit.
4. Export and approve `discovery.md`.
5. Work in **Task 2** using the approved discovery as a primary input.
6. Review coverage, assumptions, security, reliability, operations, cost, observability, evaluation, and human controls.
7. Export `spec.md`.

## Developer checks

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest
```

Public implementation references:

- [OpenAI Python API](https://developers.openai.com/api/reference/python)
- [Gemini API Python quickstart](https://ai.google.dev/gemini-api/docs/get-started?lang=python)
- [Vertex AI Application Default Credentials](https://docs.cloud.google.com/docs/authentication/set-up-adc-local-dev-environment)
- [Claude on Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude)

