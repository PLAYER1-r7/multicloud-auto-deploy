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

# CORS allowed origins (configurable per environment)
allowed_origins = config.get("allowedOrigins") or "*"
allowed_origins_list = allowed_origins.split(",") if allowed_origins != "*" else ["*"]

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
    "secretmanager.googleapis.com",  # Secret Manager
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
# Secret Manager
# ========================================
# Create a secret for application configuration
app_secret = gcp.secretmanager.Secret(
    "app-secret",
    secret_id=f"{project_name}-{stack}-app-config",
    project=project,
    replication=gcp.secretmanager.SecretReplicationArgs(
        automatic={},
    ),
    labels=common_labels,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Store initial secret value (example - should be updated with actual values)
app_secret_version = gcp.secretmanager.SecretVersion(
    "app-secret-version",
    secret=app_secret.id,
    secret_data=pulumi.Output.secret(
        '{"database_url":"changeme","api_key":"changeme"}'
    ),
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

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
    cors=[
        gcp.storage.BucketCorArgs(
            origins=allowed_origins_list,
            methods=["GET", "HEAD", "OPTIONS"],
            response_headers=["Content-Type", "Authorization", "X-Requested-With"],
            max_age_seconds=3600,
        )
    ],
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
# Cloud Armor Security Policy (WAF)
# ========================================
armor_security_policy = gcp.compute.SecurityPolicy(
    "cloud-armor-policy",
    name=f"{project_name}-{stack}-armor",
    project=project,
    description="Cloud Armor security policy for DDoS protection and rate limiting",
    # Rate limiting rule: max 1000 requests per minute per IP
    rules=[
        gcp.compute.SecurityPolicyRuleArgs(
            action="rate_based_ban",
            priority=1000,
            match=gcp.compute.SecurityPolicyRuleMatchArgs(
                versioned_expr="SRC_IPS_V1",
                config=gcp.compute.SecurityPolicyRuleMatchConfigArgs(
                    src_ip_ranges=["*"],
                ),
            ),
            rate_limit_options=gcp.compute.SecurityPolicyRuleRateLimitOptionsArgs(
                conform_action="allow",
                exceed_action="deny(429)",
                enforce_on_key="IP",
                rate_limit_threshold=gcp.compute.SecurityPolicyRuleRateLimitOptionsRateLimitThresholdArgs(
                    count=1000,
                    interval_sec=60,
                ),
                ban_duration_sec=600,  # 10 minutes ban
            ),
            description="Rate limit: 1000 requests per minute per IP",
        ),
        # Block known bad IPs (example - can be customized)
        gcp.compute.SecurityPolicyRuleArgs(
            action="deny(403)",
            priority=2000,
            match=gcp.compute.SecurityPolicyRuleMatchArgs(
                versioned_expr="SRC_IPS_V1",
                config=gcp.compute.SecurityPolicyRuleMatchConfigArgs(
                    src_ip_ranges=["192.0.2.0/24"],  # Example bad IP range
                ),
            ),
            description="Block known bad IP ranges",
        ),
    ],
    # Default rule: allow all
    adaptive_protection_config=gcp.compute.SecurityPolicyAdaptiveProtectionConfigArgs(
        layer7_ddos_defense_config=gcp.compute.SecurityPolicyAdaptiveProtectionConfigLayer7DdosDefenseConfigArgs(
            enable=True,
        ),
    ),
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# ========================================
# Cloud CDN for Frontend with HTTPS
# ========================================
# External IP Address for Load Balancer
cdn_ip_address = gcp.compute.GlobalAddress(
    "cdn-ip-address",
    name=f"{project_name}-{stack}-cdn-ip",
    project=project,
    labels=common_labels,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Backend Bucket for Cloud CDN with Cloud Armor
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
    # Attach Cloud Armor security policy
    edge_security_policy=armor_security_policy.self_link,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Managed SSL Certificate (for custom domain - optional)
# Note: This requires a custom domain. For now, we'll use HTTP only.
# To enable HTTPS with custom domain:
# 1. Set up a custom domain
# 2. Create a managed SSL certificate
# 3. Use TargetHttpsProxy instead of TargetHttpProxy

# URL Map for Load Balancer
url_map = gcp.compute.URLMap(
    "cdn-url-map",
    name=f"{project_name}-{stack}-cdn-urlmap",
    project=project,
    default_service=backend_bucket.self_link,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Target HTTPS Proxy with SSL (managed certificate)
managed_ssl_cert = gcp.compute.ManagedSslCertificate(
    "managed-ssl-cert",
    name=f"{project_name}-{stack}-ssl-cert",
    project=project,
    managed=gcp.compute.ManagedSslCertificateManagedArgs(
        domains=[f"{project_name}-{stack}.example.com"],  # Replace with actual domain
    ),
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

https_proxy = gcp.compute.TargetHttpsProxy(
    "cdn-https-proxy",
    name=f"{project_name}-{stack}-cdn-https-proxy",
    project=project,
    url_map=url_map.self_link,
    ssl_certificates=[managed_ssl_cert.self_link],
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Target HTTP Proxy (for HTTP to HTTPS redirect)
http_proxy = gcp.compute.TargetHttpProxy(
    "cdn-http-proxy",
    name=f"{project_name}-{stack}-cdn-http-proxy",
    project=project,
    url_map=url_map.self_link,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Global Forwarding Rule for HTTPS (443)
https_forwarding_rule = gcp.compute.GlobalForwardingRule(
    "cdn-https-forwarding-rule",
    name=f"{project_name}-{stack}-cdn-lb-https",
    project=project,
    ip_address=cdn_ip_address.address,
    ip_protocol="TCP",
    port_range="443",
    target=https_proxy.self_link,
    load_balancing_scheme="EXTERNAL",
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Global Forwarding Rule for HTTP (80) - redirect to HTTPS
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
pulumi.export("secret_name", app_secret.secret_id)
pulumi.export(
    "frontend_url",
    frontend_bucket.name.apply(
        lambda name: f"https://storage.googleapis.com/{name}/index.html"
    ),
)
pulumi.export("cdn_ip_address", cdn_ip_address.address)
pulumi.export("cdn_url", cdn_ip_address.address.apply(lambda ip: f"http://{ip}"))
pulumi.export("cdn_https_url", cdn_ip_address.address.apply(lambda ip: f"https://{ip}"))
pulumi.export("backend_bucket_name", backend_bucket.name)
pulumi.export("url_map_name", url_map.name)
pulumi.export("cloud_armor_policy_name", armor_security_policy.name)
pulumi.export("ssl_certificate_name", managed_ssl_cert.name)

# Function name for gcloud deployment (fixed name)
pulumi.export("function_name", f"{project_name}-{stack}-api")

# Cost estimation
pulumi.export(
    "cost_estimate",
    "Cloud Functions: 2M free invocations/month, then $0.40 per 1M. "
    "Cloud Storage: $0.02/GB/month. "
    "Cloud CDN: $0.02-0.08/GB depending on region. "
    "Cloud Armor: $6/month per policy + $0.75 per 1M requests. "
    "Managed SSL Certificate: Free. "
    "Secret Manager: $0.06 per month per secret + $0.03 per 10,000 access operations. "
    "External IP: $0.01/hour (~$7.30/month). "
    "Estimated: $15-25/month for low traffic with security features.",
)
