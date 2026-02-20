# frontend_web — Simple SNS Web Frontend (SSR)

FastAPI + Jinja2 SSR frontend for Simple SNS.  
Ported from `ashnova.v3/services/web` for the multicloud-auto-deploy platform.

## Overview

- **Framework**: FastAPI + Jinja2 (Server-Side Rendering)
- **Auth**: AWS Cognito / Azure AD / GCP Identity / Firebase / Local dev
- **Deploy targets**: AWS Lambda (Mangum), Azure Functions (ASGI), GCP Cloud Run

## Local Development

```bash
cd multicloud-auto-deploy/services/frontend_web
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set API_BASE_URL to your running backend
# For local dev:  API_BASE_URL=http://localhost:8000  AUTH_DISABLED=true

uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Then open http://localhost:8080

## Environment Variables

See [.env.example](.env.example) for full options.

| Variable | Description | Default |
|---|---|---|
| `API_BASE_URL` | Backend API endpoint | `http://localhost:8000` |
| `AUTH_PROVIDER` | `aws` / `azure` / `gcp` / `firebase` / `local` | `aws` |
| `AUTH_DISABLED` | Disable auth (local dev only) | `false` |
| `STAGE_NAME` | URL prefix stage name | `""` |

## Deployment

### AWS Lambda
`handler.py` — Lambda entry point via [Mangum](https://mangum.io/).

### Azure Functions
`function_app.py` — wraps FastAPI with `azure.functions.AsgiMiddleware`.

### GCP Cloud Run
Build from `Dockerfile`, deploy to Cloud Run (port `8080`).

## Structure

```
app/
├── main.py           FastAPI app, middleware, static mounts
├── config.py         pydantic-settings configuration
├── routers/
│   ├── auth.py       Login / logout / session / auth callback
│   └── views.py      Home / posts / profile (proxy to API)
├── templates/        Jinja2 HTML templates
└── static/           CSS, JS, SVG assets
Dockerfile            Cloud Run / container build
handler.py            AWS Lambda entry point
function_app.py       Azure Functions entry point
host.json             Azure Functions host config
requirements.txt      Python dependencies
.env.example          Example environment configuration
```

## API Communication

All data requests proxy to the `API_BASE_URL` backend (multicloud-auto-deploy `services/api`).

- AWS:   `https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/prod`
- Azure: `https://<function-app>.azurewebsites.net`
- GCP:   `https://<service>-<hash>-an.a.run.app`
