# Setup request for Jetski / Antigravity

Copy the following to the internal assistant if the person setting up RAISE Assistant wants help. Replace the bracketed values first.

> Help me set up the local `raise-assistant` project from this repository. I am not a developer. My Google Cloud project is `[PROJECT_ID]` and my company login is `[EMAIL]`. First read the project README and the setup scripts. Run `bash setup.sh` (or `setup.ps1` on Windows) and explain each question in plain English. If I choose Vertex AI, check whether I have authority to run `bash scripts/gcp_bootstrap.sh --project [PROJECT_ID] --principal user:[EMAIL]` in Cloud Shell. Do not grant broad IAM roles or create service-account keys. If permission is denied, use the generated `gcp-admin-request.txt` to tell me exactly what to send the project administrator. Then run `bash scripts/gcp_local_auth.sh --project [PROJECT_ID]` on the computer where the app will run, set the project and exact allowed model IDs in `.env`, run `bash doctor.sh`, and help me test one configured provider. Never paste an API key or access token into chat or a commit. Finally run `bash run.sh` and show me the local URL.

