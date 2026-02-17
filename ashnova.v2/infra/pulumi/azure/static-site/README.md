# Azure Static Site (Pulumi)

This stack provisions an Azure Storage Account static website and uploads the site contents.

## Config

- azure:location (default: japaneast)
- project_name: Logical name prefix for resources (default: ashnova-static-site)
- environment: Environment name (default: prod)
- site_dir: Path to local site content (default: ../../../../ashnova.old/azure/website)
- enable_frontdoor: true|false (default: true)
- custom_domain: Custom domain for Front Door (optional)
- tags: Optional key/value tags

## Usage

1) Create a virtualenv and install deps:

   python3 -m venv .venv
   . .venv/bin/activate
   pip install -r requirements.txt

2) Configure and deploy:

   pulumi stack init dev
   pulumi config set azure:location japaneast
   pulumi config set project_name ashnova-static-site
   pulumi up

## Outputs

- storage_account_name
- static_website_url
- frontdoor_endpoint_host
- frontdoor_custom_domain
