gcp_project_id = "ashnova"
gcp_region     = "asia-northeast1"

static_site_enable_cdn     = true
static_site_custom_domain  = "sns.gcp.ashnova.jp"
static_site_custom_domains = ["sns.gcp.ashnova.jp", "www.gcp.ashnova.jp"]
static_site_sns_host       = "sns.gcp.ashnova.jp"
static_site_backend_type   = "cloudrun"
static_site_default_host   = "www.gcp.ashnova.jp"
static_site_cloudrun_images = {
  "sns.gcp.ashnova.jp" = "asia-northeast1-docker.pkg.dev/ashnova/ashnova/sns-frontend:latest"
  "www.gcp.ashnova.jp" = "asia-northeast1-docker.pkg.dev/ashnova/ashnova/website:latest"
}

simple_sns_allowed_origins = ["http://34.95.112.162", "https://sns.gcp.ashnova.jp"]
