"""
Multi-Cloud Auto Deploy - GCP Pulumi Implementation

Architecture:
- Cloud Storage (Function source + Frontend)
- Cloud Functions Gen 2 (deployed via gcloud CLI in workflow)
- IAM settings

Note: Cloud Functions is deployed via gcloud CLI, not Pulumi,
because Pulumi requires the ZIP file to exist before creating the function.

Cost: ~$2-5/month for low traffic
"""
import pulumi
import pulumi_gcp as gcp

# Configuration
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
region = gcp_config.get("region") or "asia-northeast1"
stack = pulumi.get_stack()
project_name = "multicloud-auto-deploy"

# Common labels
common_labels = {
    "project": project_name,
    "managed-by": "pulumi",
    "environment": stack,
}

# ========================================
# Enable required APIs
# ========================================
services = [
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage-api.googleapis.com",
    "run.googleapis.com",  # Cloud Functions Gen 2 uses Cloud Run
]

enabled_services = []
for service in services:
    svc = gcp.projects.Service(
        f"enable-{service.split('.')[0]}",
        project=project,
        service=service,
        disable_on_destroy=False,
    )
    enabled_services.append(svc)

# ========================================
# Cloud Storage Bucket for Function Source
# ========================================
function_source_bucket = gcp.storage.Bucket(
    "function-source-bucket",
    name=f"{project}-{project_name}-{stack}-function-source",
    location=region.upper(),
    storage_class="STANDARD",
    uniform_bucket_level_access=True,
    labels=common_labels,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# ========================================
# Cloud Storage Bucket for Frontend
# ========================================
frontend_bucket = gcp.storage.Bucket(
    "frontend-bucket",
    name=f"{project}-{project_name}-{stack}-frontend",
    location=region.upper(),
    storage_class="STANDARD",
    uniform_bucket_level_access=True,
    
    website=gcp.storage.BucketWebsiteArgs(
        main_page_suffix="index.html",
        not_found_page="index.html",  # For SPA routing
    ),
    
    # CORS configuration
    cors=[gcp.storage.BucketCorArgs(
        origins=["*"],
        methods=["GET", "HEAD", "OPTIONS"],
        response_headers=["*"],
        max_age_seconds=3600,
    )],
    
    labels=common_labels,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Make frontend bucket publicly readable
gcp.storage.BucketIAMBinding(
    "frontend-public-read",
    bucket=frontend_bucket.name,
    role="roles/storage.objectViewer",
    members=["allUsers"],
)

# ========================================
# Cloud CDN for Frontend
# ========================================
# External IP Address for Load Balancer
cdn_ip_address = gcp.compute.GlobalAddress(
    "cdn-ip-address",
    name=f"{project_name}-{stack}-cdn-ip",
    project=project,
    labels=common_labels,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Backend Bucket for Cloud CDN
backend_bucket = gcp.compute.BackendBucket(
    "cdn-backend-bucket",
    name=f"{project_name}-{stack}-cdn-backend",
    bucket_name=frontend_bucket.name,
    enable_cdn=True,
    project=project,
    
    cdn_policy=gcp.compute.BackendBucketCdnPolicyArgs(
        cache_mode="CACHE_ALL_STATIC",
        default_ttl=3600,  # 1 hour
        max_ttl=86400,  # 24 hours
        client_ttl=3600,
        negative_caching=True,
        serve_while_stale=86400,
    ),
    
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# URL Map for Load Balancer
url_map = gcp.compute.URLMap(
    "cdn-url-map",
    name=f"{project_name}-{stack}-cdn-urlmap",
    project=project,
    default_service=backend_bucket.self_link,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Target HTTP Proxy
http_proxy = gcp.compute.TargetHttpProxy(
    "cdn-http-proxy",
    name=f"{project_name}-{stack}-cdn-http-proxy",
    project=project,
    url_map=url_map.self_link,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Global Forwarding Rule (Load Balancer)
forwarding_rule = gcp.compute.GlobalForwardingRule(
    "cdn-forwarding-rule",
    name=f"{project_name}-{stack}-cdn-lb",
    project=project,
    ip_address=cdn_ip_address.address,
    ip_protocol="TCP",
    port_range="80",
    target=http_proxy.self_link,
    load_balancing_scheme="EXTERNAL",
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# ========================================
# Note about Cloud Functions
# ========================================
# Cloud Functions Gen 2 will be deployed via gcloud CLI in the GitHub Actions workflow
# because Pulumi requires the source ZIP to exist before creating the function.
# 
# The workflow will:
# 1. Use Pulumi to create buckets and IAM settings (this file)
# 2. Build and package the function code
# 3. Upload ZIP to function_source_bucket
# 4. Deploy Cloud Functions via: gcloud functions deploy --gen2 --source=gs://...

# ========================================
# Outputs
# ========================================
pulumi.export("project_id", project)
pulumi.export("region", region)
pulumi.export("function_source_bucket", function_source_bucket.name)
pulumi.export("frontend_bucket", frontend_bucket.name)
pulumi.export("frontend_url", frontend_bucket.name.apply(
    lambda name: f"https://storage.googleapis.com/{name}/index.html"
))
pulumi.export("cdn_ip_address", cdn_ip_address.address)
pulumi.export("cdn_url", cdn_ip_address.address.apply(
    lambda ip: f"http://{ip}"
))
pulumi.export("backend_bucket_name", backend_bucket.name)
pulumi.export("url_map_name", url_map.name)

# Function name for gcloud deployment (fixed name)
pulumi.export("function_name", f"{project_name}-{stack}-api")

# Cost estimation
pulumi.export("cost_estimate",
    "Cloud Functions: 2M free invocations/month, then $0.40 per 1M. "
    "Cloud Storage: $0.02/GB/month. "
    "Cloud CDN: $0.02-0.08/GB depending on region. "
    "External IP: $0.01/hour (~$7.30/month). "
    "Estimated: $10-20/month for low traffic."
)
