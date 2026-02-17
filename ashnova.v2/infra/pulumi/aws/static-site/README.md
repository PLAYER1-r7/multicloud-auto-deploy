# AWS Static Site (Pulumi)

This stack provisions an S3-backed static site with optional CloudFront.

## Config

- aws:region (Pulumi standard config)
- project_name: Logical name prefix for resources
- site_dir: Path to local site content (default: ../../../../static-site)
- enable_cloudfront: true|false (default: true)
- domain_name: Custom domain (optional)
- zone_id: Route53 hosted zone ID for DNS validation (required when domain_name set)
- price_class: CloudFront price class (default: PriceClass_100)
- force_destroy: true|false (default: false)

## Usage

1) Create a virtualenv and install deps:

   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

2) Configure and deploy:

   pulumi stack init dev
   pulumi config set aws:region ap-northeast-1
   pulumi config set project_name ashnova-static-site
   pulumi up

## Outputs

- bucket_name
- cloudfront_domain_name (when enabled)
- website_url
