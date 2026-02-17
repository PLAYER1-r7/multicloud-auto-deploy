# GCP Static Site (Pulumi)

This stack provisions a GCS static website and optional Cloud CDN + Global HTTP(S) Load Balancer.

## Config

- gcp:project (required)
- gcp:region (default: asia-northeast1)
- project_name: Logical name prefix (default: ashnova)
- environment: Environment name (default: production)
- site_dir: Path to local site content (default: ../../../../ashnova.old/gcp/website)
- enable_cdn: true|false (default: true)
- bucket_location: ASIA | asia-northeast1 (default: ASIA)
- custom_domain: Custom domain for HTTPS LB (optional)

## Usage

1) Create a virtualenv and install deps:

   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

2) Configure and deploy:

   pulumi stack init dev
   pulumi config set gcp:project YOUR_PROJECT_ID
   pulumi up

## Outputs

- bucket_name
- website_url
- cdn_ip_address (when enable_cdn)
