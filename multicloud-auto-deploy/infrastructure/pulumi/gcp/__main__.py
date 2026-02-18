"""
Multi-Cloud Auto Deploy - GCP Pulumi Implementation

Architecture:
- Cloud Storage (Function source + Frontend)
- Cloud Functions Gen 2 (deployed via gcloud CLI in workflow)
- IAM settings
- Secret Manager with IAM bindings

Note: Cloud Functions is deployed via gcloud CLI, not Pulumi,
because Pulumi requires the ZIP file to exist before creating the function.

Cost: ~$2-5/month for low traffic
"""

import pulumi
import pulumi_gcp as gcp
import os
import monitoring

# Configuration
config = pulumi.Config()
gcp_config = pulumi.Config("gcp")
project = gcp_config.require("project")
region = gcp_config.get("region") or "asia-northeast1"
stack = pulumi.get_stack()
project_name = "multicloud-auto-deploy"

# Get the service account email from environment or config (used by GitHub Actions)
# This will be set from GCP_CREDENTIALS in the workflow
github_actions_sa = config.get("github_actions_sa") or os.getenv("GITHUB_ACTIONS_SA")

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
    "firebase.googleapis.com",  # Firebase
    "identitytoolkit.googleapis.com",  # Identity Platform (Firebase Auth backend)
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
# Authentication Setup - Firebase Project
# ========================================
# Create Firebase Project (enables Firebase for this GCP project)
firebase_project = gcp.firebase.Project(
    "firebase-project",
    project=project,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Create Firebase Web App
firebase_web_app = gcp.firebase.WebApp(
    "web-app",
    project=project,
    display_name=f"{project_name}-{stack}-web",
    opts=pulumi.ResourceOptions(depends_on=[firebase_project]),
)

# Note: Firebase Web App configuration (API Key, Auth Domain) is available
# in the Firebase Console after the app is created. These cannot be retrieved
# programmatically via Pulumi at provisioning time.
#
# To get the configuration:
# 1. Visit Firebase Console: https://console.firebase.google.com/
# 2. Select your project
# 3. Go to Project Settings → General
# 4. Scroll down to "Your apps" and find your Web App
# 5. Copy the Firebase SDK configuration

# Note: Authentication providers (Google, Email/Password, etc.) must be configured
# manually in Firebase Console due to OAuth consent screen requirements.
# Visit: https://console.firebase.google.com/project/{project}/authentication/providers
#
# Required steps:
# 1. Enable Google Sign-In provider
# 2. Configure OAuth consent screen
# 3. Add authorized domains for your frontend

# ========================================
# Secret Manager
# ========================================
# Create a secret for application configuration
app_secret = gcp.secretmanager.Secret(
    "app-secret",
    secret_id=f"{project_name}-{stack}-app-config",
    project=project,
    replication=gcp.secretmanager.SecretReplicationArgs(
        auto=gcp.secretmanager.SecretReplicationAutoArgs(),
    ),
    labels=common_labels,
    opts=pulumi.ResourceOptions(depends_on=enabled_services),
)

# Grant access to the secret manually via gcloud or Cloud Console
# IAM bindings must be set manually because Pulumi SA needs setIamPolicy permission
# Run: scripts/setup-gcp-secret-permissions.sh
# Or use: gcloud secrets add-iam-policy-binding multicloud-auto-deploy-staging-app-config \
#         --member="serviceAccount:github-actions-deploy@ashnova.iam.gserviceaccount.com" \
#         --role="roles/secretmanager.secretAccessor"

# NOTE: SecretVersion resource intentionally removed from Pulumi management.
# Pulumi SA lacks 'secretmanager.versions.access' permission (read-back after create causes 403).
# Secret versions are managed manually via gcloud:
#   gcloud secrets versions add {project_name}-{stack}-app-config --data-file=secret.json

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
# Note: Cloud Armor is disabled for staging to reduce cost (~$6-7/month)
# ========================================
if stack == "production":
    armor_security_policy = gcp.compute.SecurityPolicy(
        "cloud-armor-policy",
        name=f"{project_name}-{stack}-armor",
        project=project,
        type="CLOUD_ARMOR_EDGE",  # Required for edge security
        description="Cloud Armor edge security policy for CDN protection",
        rules=[
            # Block known bad IPs (example - can be customized)
            gcp.compute.SecurityPolicyRuleArgs(
                action="deny(403)",
                priority=1000,
                match=gcp.compute.SecurityPolicyRuleMatchArgs(
                    versioned_expr="SRC_IPS_V1",
                    config=gcp.compute.SecurityPolicyRuleMatchConfigArgs(
                        src_ip_ranges=["192.0.2.0/24"],  # Example bad IP range
                    ),
                ),
                description="Block known bad IP ranges",
            ),
            # Default rule: allow all (required at priority 2147483647)
            gcp.compute.SecurityPolicyRuleArgs(
                action="allow",
                priority=2147483647,
                match=gcp.compute.SecurityPolicyRuleMatchArgs(
                    versioned_expr="SRC_IPS_V1",
                    config=gcp.compute.SecurityPolicyRuleMatchConfigArgs(
                        src_ip_ranges=["*"],
                    ),
                ),
                description="Default rule: allow all traffic",
            ),
        ],
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

# Backend Bucket for Cloud CDN with conditional Cloud Armor
backend_bucket_kwargs = {
    "name": f"{project_name}-{stack}-cdn-backend",
    "bucket_name": frontend_bucket.name,
    "enable_cdn": True,
    "project": project,
    "cdn_policy": gcp.compute.BackendBucketCdnPolicyArgs(
        cache_mode="CACHE_ALL_STATIC",
        default_ttl=3600,  # 1 hour
        max_ttl=86400,  # 24 hours
        client_ttl=3600,
        negative_caching=True,
        serve_while_stale=86400,
    ),
    "opts": pulumi.ResourceOptions(depends_on=enabled_services),
}

# Attach Cloud Armor security policy only for production
if stack == "production":
    backend_bucket_kwargs["edge_security_policy"] = armor_security_policy.self_link

backend_bucket = gcp.compute.BackendBucket(
    "cdn-backend-bucket", **backend_bucket_kwargs
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
# Custom domain configuration (optional)
custom_domain = config.get("customDomain")  # e.g., gcp.yourdomain.com
ssl_domains = (
    [custom_domain] if custom_domain else [f"{project_name}-{stack}.example.com"]
)

managed_ssl_cert = gcp.compute.ManagedSslCertificate(
    "managed-ssl-cert",
    name=f"{project_name}-{stack}-ssl-cert",
    project=project,
    managed=gcp.compute.ManagedSslCertificateManagedArgs(
        domains=ssl_domains,
    ),
    opts=pulumi.ResourceOptions(
        depends_on=enabled_services,
        delete_before_replace=True,  # Required for domain changes
    ),
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

# Custom domain exports (if configured)
if custom_domain:
    pulumi.export("custom_domain", custom_domain)
    pulumi.export("custom_domain_url", f"https://{custom_domain}")
    pulumi.export("ssl_certificate_domains", ssl_domains)

# Firebase Authentication
pulumi.export("firebase_project_id", project)
pulumi.export("firebase_web_app_id", firebase_web_app.app_id)
pulumi.export("firebase_web_app_name", firebase_web_app.name)
pulumi.export(
    "auth_config_instructions",
    pulumi.Output.concat(
        "Firebase Web App created successfully!\\n",
        "\\n",
        "To get Firebase configuration (API Key, Auth Domain):\\n",
        "1. Visit: https://console.firebase.google.com/project/",
        project,
        "/settings/general\\n",
        "2. Scroll to 'Your apps' section\\n",
        "3. Find your web app: ",
        firebase_web_app.display_name,
        "\\n",
        "4. Copy the Firebase SDK configuration\\n",
        "\\n",
        "To enable authentication:\\n",
        "1. Visit: https://console.firebase.google.com/project/",
        project,
        "/authentication\\n",
        "2. Enable Google Sign-In provider\\n",
        "3. Configure OAuth consent screen\\n",
        "\\n",
        "Cloud Functions environment variables:\\n" "  AUTH_PROVIDER=firebase\\n",
        "  GCP_PROJECT_ID=",
        project,
        "\\n",
    ),
)
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
# Cloud Armor exports only for production
if stack == "production":
    pulumi.export("cloud_armor_policy_name", armor_security_policy.name)
pulumi.export("ssl_certificate_name", managed_ssl_cert.name)

# ========================================
# Monitoring and Alerts
# ========================================
alarm_email = config.get("alarmEmail")
function_name = f"{project_name}-{stack}-api"

monitoring_resources = monitoring.setup_monitoring(
    project_name=project_name,
    stack=stack,
    function_name=pulumi.Output.from_input(function_name),
    region=region,
    project_id=project,
    alarm_email=alarm_email,
    monthly_budget_usd=config.get_int("monthlyBudgetUsd") or 50,
)

# Function name for gcloud deployment (fixed name)
pulumi.export("function_name", f"{project_name}-{stack}-api")

# Monitoring exports
if monitoring_resources["notification_channel"]:
    pulumi.export(
        "monitoring_notification_channel_id",
        monitoring_resources["notification_channel"].id,
    )
pulumi.export(
    "monitoring_function_alerts", list(monitoring_resources["function_alerts"].keys())
)
pulumi.export(
    "monitoring_firestore_alerts", list(monitoring_resources["firestore_alerts"].keys())
)
if monitoring_resources["billing_budget"]:
    pulumi.export(
        "monitoring_billing_budget_name",
        monitoring_resources["billing_budget"].display_name,
    )

# Cost estimation
cost_estimate_base = (
    "Cloud Functions: 2M free invocations/month, then $0.40 per 1M. "
    "Cloud Storage: $0.02/GB/month. "
    "Cloud CDN: $0.02-0.08/GB depending on region. "
    "Managed SSL Certificate: Free. "
    "Secret Manager: $0.06 per month per secret + $0.03 per 10,000 access operations. "
    "External IP: $0.01/hour (~$7.30/month). "
)

if stack == "production":
    cost_estimate = (
        cost_estimate_base
        + "Cloud Armor: $6/month per policy + $0.75 per 1M requests. "
        "Estimated: $15-25/month for low traffic with security features."
    )
else:
    cost_estimate = (
        cost_estimate_base + "Cloud Armor: Disabled for staging (saves ~$6-7/month). "
        "Estimated: $8-15/month for low traffic without Cloud Armor."
    )

pulumi.export("cost_estimate", cost_estimate)
