# Public Google Cloud architecture guidance for RAISE practice

This is a condensed, authored study reference. It is **not** an official RAISE rubric or template. A customer source pack and current task instructions take precedence for assessment facts and format.

## Discovery before design

Record the customer's business outcomes, stakeholders, present workflow, pain points, success measures, requirements, constraints, data sources, security needs, operating model, risks, and unknowns. Give each important requirement an ID and a source locator. If the customer has not specified a value, mark it open and state who can answer it. Keep solution proposals separate from discovery facts.

Reference: [Google Cloud solution architecture skill](https://github.com/google/skills/tree/main/skills/cloud/google-cloud-solution-architecture).

## Solution design

Map each confirmed requirement to a design decision and a validation method. Describe the request path and trust boundaries. Explain why each major component is chosen, at least one serious alternative, and the trade-off. Include data flow, identities, access controls, safety, reliability, performance, cost drivers, operations, observability, and release/rollback. A design is incomplete if it cannot be tested against the stated success measures.

Reference: [Google Cloud solution architecture output template](https://github.com/google/skills/blob/main/skills/cloud/google-cloud-solution-architecture/assets/output-template.md).

## Grounded agent design

For an agent that uses enterprise sources, identify the source of truth, connector or ingestion path, freshness, indexing, access-control behavior, citation strategy, and handling of missing or conflicting evidence. Tool use should define which actions are allowed, what identity runs them, what is logged, and when a human approves an action. Session memory should have a clear scope and retention rule. Evaluate not only answer quality but also grounding, refusal/uncertainty, safety, and operational failures.

References: [Vertex AI grounding overview](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/grounding/overview), [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework).

## Verification

Use a requirements-to-test table. Include functional checks, security and access checks, latency and load targets, failure/recovery behavior, observability, human oversight, and agent quality. Preserve the difference between a design assumption and a measured result. Request official RAISE feedback or rubric when available to assess assessment-specific readiness.

Reference: [Google Cloud Well-Architected Framework](https://docs.cloud.google.com/architecture/framework).

