# AWS Simple SNS Web (Pulumi)

This stack provisions API Gateway (REST) and Lambda for the SSR web frontend.

## Config

- aws:region (Pulumi standard config)
- aws:profile (Pulumi standard config)
- project_name: Logical name prefix (default: simple-sns-web)
- api_base_url: Base URL for the Simple SNS API (required)
- tags: Optional key/value tags

## Usage

1) Create a virtualenv and install deps:

   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

2) Configure and deploy:

   pulumi stack init dev
   pulumi config set aws:region ap-northeast-1
   pulumi config set project_name simple-sns-web
   pulumi config set api_base_url https://btghogtp08.execute-api.ap-northeast-1.amazonaws.com/prod
   pulumi up

## Outputs

- web_url

## Notes

- Lambda packaging is done during `pulumi up` by zipping `services/simple_sns_web` with dependencies.
