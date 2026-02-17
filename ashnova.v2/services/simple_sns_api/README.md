# Simple SNS API (FastAPI)

FastAPI app targeting AWS Lambda via Mangum. Endpoints mirror the legacy Simple SNS API.

## Local dev

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Lambda

Use `handler.py` as the Lambda entry point. Packaging is wired by the Pulumi stack in
infra/pulumi/aws/simple-sns.
