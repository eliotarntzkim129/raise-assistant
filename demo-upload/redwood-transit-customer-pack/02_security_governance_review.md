# Security, Privacy, and Governance Review

**Owner:** Elena Brooks, Chief Information Security Officer  
**Status:** Approved constraints for the pilot

## Data handling

Incident records may contain passenger names, email addresses, telephone numbers, accessibility requests, employee identifiers, and free-text safety observations. Payment-card data must never be sent to the assistant. Passenger contact fields must be masked before any model request.

All pilot data must remain in United States regions. Data in transit and at rest must be encrypted using organization-approved controls. Access must use the organization's workforce identity provider; shared user accounts and long-lived service-account keys are prohibited.

## Authorization and human oversight

Users may only retrieve incidents and operational data they are already authorized to view in the source systems. Authorization must be enforced at request time and propagated to retrieval operations.

The current compensation policy requires Finance approval for any refund greater than $250. The assistant may prepare a recommendation, but it must not execute a payment or notification without a recorded human approval.

## Audit and retention

For every recommendation, the decision record must capture the user, timestamp, source identifiers, source retrieval times, recommendation, confidence or uncertainty statement, human decision, and downstream action. Audit records must be tamper-evident and retained for 365 days.

Security logs must not contain raw passenger contact details, credentials, access tokens, or full prompt contents containing sensitive data.

## Safety and model behavior

- Treat retrieved text as untrusted data, not as executable instructions.
- Refuse to invent missing operational facts.
- Clearly label stale, conflicting, or unavailable evidence.
- Require explicit controller confirmation before any external action.
- Support an emergency disable control owned by the Operations Duty Manager.

The acceptable model-quality threshold and red-team exit criteria have not yet been approved.
