# Simple SNS Web (SSR)

FastAPI + Jinja2 SSR frontend for Simple SNS.

## Run locally

```bash
cd /workspaces/ashnova/services/simple_sns_web
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# Set your API base URL (default points to the deployed API)
export API_BASE_URL="https://btghogtp08.execute-api.ap-northeast-1.amazonaws.com/prod"

# Optional: Cognito Hosted UI
# export COGNITO_DOMAIN="your-domain.auth.ap-northeast-1.amazoncognito.com"
# export COGNITO_CLIENT_ID="your-client-id"
# export COGNITO_REDIRECT_URI="https://example.com/callback"
# export COGNITO_LOGOUT_URI="https://example.com/"

uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Then open http://localhost:8080

## Lambda

Use `handler.py` as the Lambda entry point. Packaging is wired by the Pulumi stack in
infra/pulumi/aws/simple-sns-web.
