# Operations and Customer Experience Interview

**Date:** 2026-10-22  
**Participants:** Maya Chen, Operations Director; Luis Ortega, Customer Experience Director; Priya Nair, Lead Controller

## Current workflow

Priya described the current workflow:

> I copy the incident number into three systems, call the rail or bus desk, check the vehicle map, and then write a summary in the shared spreadsheet.

Controllers use the incident system as the authoritative record for event status. The vehicle-location interface can be delayed by up to 45 seconds. Staffing availability is obtained through a read-only REST interface limited to 60 requests per second. Customer notifications are sent through an existing notification gateway limited to 100 requests per second.

## Human authority

Maya stated:

> The assistant can recommend, but a controller must approve every route change, station closure, safety instruction, or compensation action before anything is sent.

Luis requested that the pilot eventually support automatic goodwill refunds up to $500 when a verified delay exceeds two hours. Maya did not approve that request during the interview and asked for Finance and Legal review.

## Operating priorities

1. Public and employee safety.
2. Accurate information with visible source timestamps.
3. Fast acknowledgement and brief assembly.
4. Clear escalation when evidence is missing or contradictory.
5. Reduced duplicate entry for controllers.

## Known gaps

- The owner of the pilot acceptance decision has not been formally named.
- The allowed age of vehicle-location data has not been agreed.
- The customer-notification team has not confirmed whether the 100 requests-per-second limit is per region or global.
- No recovery-time objective has been approved for the new assistant.
