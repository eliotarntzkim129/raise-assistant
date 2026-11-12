from __future__ import annotations


DISCOVERY_TEMPLATE = """<!--
WORKING FALLBACK reconstructed from the visible official-template screenshots.
The screenshots establish all 15 sections and their visible tables/instructions.
This remains a reconstruction rather than the original file. Upload the original
Task 1 Markdown template when available; the app will replace this fallback
automatically.
-->

# Discovery Document

## 1. Document Control

| Field | Value |
|---|---|
| Author | |
| Date | |
| Version | |
| Prioritization framework used | |

### 1.1 Artifact Review Log

*One row per file in the package.*

| Artifact filename | Modality | Reviewed? | Requirements sourced | Notes / issues encountered |
|---|---|---|---|---|

## 2. Executive Summary

### 2.1 The problem in the customer's own terms

### 2.2 Quantified business impact

### 2.3 Top 5 requirements by priority

### 2.4 Recommended Phase 1 scope and the cut line

### 2.5 The three things that must be resolved before design can start

## 3. Stakeholder Register

| Name | Role / Title | Key agenda / mandate | Sign-off / veto authority | Source citation |
|---|---|---|---|---|

### 3.1 Stakeholder tensions to be reconciled

| Tension # | Position A (stakeholder + citation) | Position B (stakeholder + citation) | Recommended resolution / default | Decision owner |
|---|---|---|---|---|

## 4. Business Context & Value Drivers

### 4.1 Current state and why existing systems cannot solve it

### 4.2 Regulatory and Legal Landscape

### 4.3 Active enforcement and live incidents

## 5. Functional Requirements Register

| Req ID | Functional Requirement Statement | Source Artifact | Locator | Verbatim Quote | Acceptance Criteria | Priority | Priority Justification |
|---|---|---|---|---|---|---|---|

## 6. Non-Functional Requirements Register

| Req ID | Non-Functional Requirement Statement | Quality Attribute | Target Metric / SLA | Source Artifact | Locator | Verbatim Quote | Priority | Priority Justification |
|---|---|---|---|---|---|---|---|---|

### 6.1 Quality attribute coverage check

List the quality attributes covered by the NFRs. If the source package contains no requirement for an attribute, flag it and raise it in section 8; do not invent one.

## 7. Customer-Imposed Constraints & Non-Negotiables

| Const ID | Constraint Description | Mandated By | Source Artifact | Locator | Verbatim Quote | Design Impact |
|---|---|---|---|---|---|---|

### 7.1 Explicit out-of-scope / negative scope

## 8. Open Questions & Clarifications Required

| Q # | Open Question | Why it matters for design | Owner | Blocking Task 2? | Default if unanswered |
|---|---|---|---|---|---|

## 9. Assumptions Register

| Asm ID | Assumption Statement | Rationale | Risk if wrong | Owner | Validation action |
|---|---|---|---|---|---|

## 10. Conflicts, Contradictions & Discovery Risks

### 10.1 Contradictions between artifacts

| Conflict # | Source A (artifact + locator + quote) | Source B (artifact + locator + quote) | Recommended resolution / default | Decision owner |
|---|---|---|---|---|

### 10.2 Unsourced or undefined dependencies

### 10.3 Discovery risks

## 11. Prioritization Method & Ranked Backlog

### 11.1 Declared framework

### 11.2 Prioritization matrix/table

### 11.3 Ranked backlog with the Phase 1 cut line

*List all requirements in priority order, with a visible cut line after the last Phase 1 item.*

| Rank | Req ID | Priority | Phase | Justification |
|---|---|---|---|---|

### 11.4 Deliberate de-prioritisations

## 12. Data & Integration Inventory

### 12.1 Structured data sources

### 12.2 Unstructured content sources

### 12.3 Sensitive data classification

## 13. Dependencies & Delivery Sequencing

### 13.1 Dependency map

### 13.2 Proposed phasing

| Phase | Req IDs | Outcome | Exit criteria |
|---|---|---|---|

## 14. Traceability Matrix (Artifact → Requirements)

| Artifact Filename | Requirements Sourced | Count | Unique Contribution |
|---|---|---|---|

## 15. Appendix

### 15.1 Glossary of domain terms

### 15.2 Additional notes or context
"""


SPEC_TEMPLATE = """<!--
WORKING FALLBACK TEMPLATE — not an official RAISE template.
Replace this by uploading the live assessment's official Task 2 template as “Task 2 official template”.
Do not remove required headings from an official template.
-->

# Solution specification

## 1. Document control and decision status

| Field | Value |
|---|---|
| Customer / case | |
| Discovery input/version | |
| Author | |
| Date | |
| Status | Draft |

## 2. Executive solution summary

State the proposed outcome, architecture approach, major decisions, and material unresolved items.

## 3. Goals, non-goals and design principles

### Goals

### Non-goals

### Design principles

## 4. Requirements-to-design traceability

| Requirement ID | Design response | Component(s) | Validation method | Status |
|---|---|---|---|---|

## 5. Architecture overview

```mermaid
flowchart LR
  User[User] --> Experience[Experience layer]
  Experience --> Orchestration[Agent / orchestration]
  Orchestration --> Data[Grounded enterprise data]
```

Describe boundaries, trust zones, request flow, and why the design fits the stated requirements.

## 6. Component design

| Component | Responsibility | Inputs / outputs | Technology choice | Scaling / failure behavior | Requirement IDs |
|---|---|---|---|---|---|

## 7. Data, grounding and integrations

Cover ingestion, indexing, freshness, citations, access-control propagation, source-of-truth behavior, connectors, contracts, and failure handling.

## 8. Agent and model behavior

Cover model/provider choice, prompts/instructions, tools, memory boundaries, routing, grounding, uncertainty behavior, safety controls, evaluation, and fallback.

## 9. Identity, security, privacy and responsible AI

Cover user and workload identity, least privilege, secrets, encryption, network boundaries, auditability, data handling, prompt-injection controls, abuse controls, human oversight and policy alignment.

## 10. Reliability, performance and scalability

Include service objectives, quotas, concurrency, timeouts, retries, idempotency, degradation, backup/recovery, regional considerations, load assumptions and capacity tests.

## 11. Observability, evaluation and operations

Define logs, metrics, traces, model/agent quality measures, dashboards, alerts, runbooks, ownership, incident response, release controls and rollback.

## 12. Environments and delivery plan

| Phase | Deliverable | Entry criteria | Validation | Exit criteria | Owner |
|---|---|---|---|---|---|

## 13. Cost and commercial considerations

Document cost drivers, assumptions, controls, budgets/alerts, optimization options and unknowns. Do not fabricate prices.

## 14. Decisions, alternatives and trade-offs

| Decision ID | Chosen approach | Alternatives considered | Rationale | Trade-offs | Requirement IDs |
|---|---|---|---|---|---|

## 15. Risks, assumptions and unresolved questions

| ID | Item | Impact | Mitigation / owner | Resolution date or trigger |
|---|---|---|---|---|

## 16. Verification and acceptance plan

Map functional, security, reliability, performance, operations and model-quality tests to requirements and measurable pass conditions.

## 17. Evidence and reference index

| Source ID | File / official reference | Design claims supported |
|---|---|---|
"""


def fallback_template(task: str) -> str:
    if task == "task1":
        return DISCOVERY_TEMPLATE
    if task == "task2":
        return SPEC_TEMPLATE
    raise ValueError(f"Unknown task: {task}")


def template_kind(task: str) -> str:
    if task not in {"task1", "task2"}:
        raise ValueError(f"Unknown task: {task}")
    return f"template_{task}"

