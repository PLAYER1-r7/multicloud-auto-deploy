# AWS Simple SNS (Pulumi)

This stack provisions API Gateway (REST), Lambda, DynamoDB, S3 (images), and Cognito.

## Config

- aws:region (Pulumi standard config)
- aws:profile (Pulumi standard config)
- project_name: Logical name prefix (default: simple-sns)
- tags: Optional key/value tags

## Usage

1) Create a virtualenv and install deps:

   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

2) Configure and deploy:

   pulumi stack init dev
   pulumi config set aws:region ap-northeast-1
   pulumi config set project_name simple-sns
   pulumi up

## Outputs

- api_url
- cognito_user_pool_id
- cognito_client_id
- posts_table_name
- images_bucket_name

## Notes

- Lambda packaging is done during `pulumi up` by zipping `services/simple_sns_api` with dependencies.
