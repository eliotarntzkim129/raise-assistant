# Redwood Transit Customer Narrative

## Business problem

Redwood Transit operates regional bus and rail services. Service disruptions are coordinated through email, radio calls, spreadsheets, and four separate operational systems. The Operations Control Center wants a decision-support assistant that assembles a consistent incident brief, recommends the next action, and records the evidence used for each recommendation.

Operations Director Maya Chen stated during the discovery kickoff:

> During the evening peak, the controller may spend twelve minutes assembling a usable disruption brief while passengers and station teams wait for direction.

The customer reports an average of 2,400 disruption-related service cases per day. During severe weather, intake can reach 180 new events per minute for periods of up to 20 minutes.

## Desired outcome

The first release should reduce the time required to acknowledge a new disruption and assemble a decision-ready brief. Redwood Transit requires the system to:

- acknowledge a newly received event within 15 seconds for at least 95% of events;
- show the source and retrieval time for every operational fact in a brief;
- preserve the controller as the final decision-maker for service changes, public safety instructions, and customer compensation;
- operate continuously during the 05:00–01:00 service window, Pacific Time;
- integrate with the existing incident, vehicle-location, staffing, and customer-notification interfaces.

## Scope boundaries

Phase 1 covers event intake, evidence collection, brief generation, recommendation presentation, and controller approval. Automatic dispatching, autonomous route changes, employee discipline, and replacement of the existing systems of record are explicitly out of scope.

No cloud provider, model vendor, database, or agent framework has been mandated. Redwood Transit expects the design team to recommend implementation choices during solution design.

## Business success measures

- Reduce median time to a decision-ready brief from the current 12-minute observation to 3 minutes or less during the pilot.
- Achieve at least 90% controller acceptance of factual brief fields in the pilot evaluation set.
- Produce an immutable decision record for every recommendation shown to a controller.

The financial value of faster disruption handling has not yet been quantified. The Finance team owns that analysis.
