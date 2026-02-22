"""
Multi-Cloud Auto Deploy - AWS Pulumi Implementation

Architecture:
- Lambda Function (Python 3.12, ZIP deployment)
- API Gateway (HTTP API v2)
- S3 (Static website hosting)
- CloudFront (Optional, for custom domain)

Cost: ~$2-5/month for low traffic
"""

import base64
import pathlib
import os
import json
import pulumi
import pulumi_aws as aws
import monitoring

# Configuration
config = pulumi.Config()
aws_config = pulumi.Config("aws")
region = aws_config.get("region") or "us-east-1"
stack = pulumi.get_stack()
project_name = "multicloud-auto-deploy"

# CORS allowed origins (configurable per environment)
allowed_origins = config.get("allowedOrigins") or "*"
allowed_origins_list = allowed_origins.split(
    ",") if allowed_origins != "*" else ["*"]

# CloudFront domain (set after first deploy: pulumi config set cloudFrontDomain <domain>)
# Used for Cognito callback/logout URLs and frontend_web redirect URIs
cf_domain = config.get("cloudFrontDomain") or ""

# Common tags
common_tags = {
    "Project": project_name,
    "ManagedBy": "pulumi",
    "Environment": stack,
}

# ========================================
# IAM Role for Lambda
# ========================================
lambda_role = aws.iam.Role(
    "lambda-role",
    name=f"{project_name}-{stack}-lambda-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Effect": "Allow",
                }
            ],
        }
    ),
    tags=common_tags,
)

# Attach basic Lambda execution policy
aws.iam.RolePolicyAttachment(
    "lambda-basic-execution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# Attach Secrets Manager read policy for Lambda
aws.iam.RolePolicyAttachment(
    "lambda-secrets-manager",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/SecretsManagerReadWrite",
)

# ========================================
# AWS Secrets Manager
# ========================================
# Create a secret for database credentials or API keys
app_secret = aws.secretsmanager.Secret(
    "app-secret",
    name=f"{project_name}/{stack}/app-config",
    description=f"Application secrets for {project_name} {stack} environment",
    tags=common_tags,
)

# Store initial secret value (example - should be updated with actual values)
app_secret_version = aws.secretsmanager.SecretVersion(
    "app-secret-version",
    secret_id=app_secret.id,
    secret_string=pulumi.Output.secret(
        '{"database_url":"changeme","api_key":"changeme"}'
    ),
)

# ========================================
# Cognito User Pool for Authentication
# ========================================
user_pool = aws.cognito.UserPool(
    "user-pool",
    name=f"{project_name}-{stack}-users",
    mfa_configuration="OFF",
    password_policy={
        "minimum_length": 8,
        "require_lowercase": True,
        "require_numbers": True,
        "require_symbols": False,
        "require_uppercase": True,
        "temporary_password_validity_days": 7,
    },
    auto_verified_attributes=["email"],
    schemas=[
        {
            "attribute_data_type": "String",
            "name": "email",
            "required": True,
            "mutable": True,
        }
    ],
    account_recovery_setting={
        "recovery_mechanisms": [
            {
                "name": "verified_email",
                "priority": 1,
            }
        ]
    },
    email_configuration={
        "email_sending_account": "COGNITO_DEFAULT",
    },
    tags=common_tags,
)

# Cognito User Pool Client
user_pool_client = aws.cognito.UserPoolClient(
    "user-pool-client",
    name=f"{project_name}-{stack}-web-client",
    user_pool_id=user_pool.id,
    allowed_oauth_flows=["code", "implicit"],
    allowed_oauth_scopes=["openid", "email", "profile"],
    allowed_oauth_flows_user_pool_client=True,
    callback_urls=[
        "http://localhost:8080/callback",
        "https://localhost:8080/callback",
    ] + ([f"https://{cf_domain}/sns/auth/callback"] if cf_domain else []),
    logout_urls=[
        "http://localhost:8080/",
        "https://localhost:8080/",
    ] + ([f"https://{cf_domain}/sns/"] if cf_domain else []),
    access_token_validity=1,
    id_token_validity=1,
    refresh_token_validity=30,
    token_validity_units={
        "access_token": "hours",
        "id_token": "hours",
        "refresh_token": "days",
    },
    prevent_user_existence_errors="ENABLED",
    enable_token_revocation=True,
    explicit_auth_flows=[
        "ALLOW_ADMIN_USER_PASSWORD_AUTH",
        "ALLOW_REFRESH_TOKEN_AUTH",
        "ALLOW_USER_PASSWORD_AUTH",
        "ALLOW_USER_SRP_AUTH",
    ],
    supported_identity_providers=["COGNITO"],
)

# Cognito User Pool Domain
user_pool_domain = aws.cognito.UserPoolDomain(
    "user-pool-domain",
    domain=f"{project_name}-{stack}",
    user_pool_id=user_pool.id,
)

# ========================================
# DynamoDB Table (Single Table Design)
# ========================================
posts_table = aws.dynamodb.Table(
    "posts-table",
    name=f"{project_name}-{stack}-posts",
    billing_mode="PAY_PER_REQUEST",
    hash_key="PK",
    range_key="SK",
    attributes=[
        {
            "name": "PK",
            "type": "S",
        },
        {
            "name": "SK",
            "type": "S",
        },
        {
            "name": "postId",
            "type": "S",
        },
        {
            "name": "userId",
            "type": "S",
        },
        {
            "name": "createdAt",
            "type": "S",
        },
    ],
    global_secondary_indexes=[
        {
            "name": "PostIdIndex",
            "hash_key": "postId",
            "projection_type": "ALL",
        },
        {
            "name": "UserPostsIndex",
            "hash_key": "userId",
            "range_key": "createdAt",
            "projection_type": "ALL",
        },
    ],
    tags=common_tags,
)

# S3 Bucket for Images
images_bucket = aws.s3.BucketV2(
    "images-bucket",
    bucket=f"{project_name}-{stack}-images",
    tags=common_tags,
)

# Disable versioning for cost savings
aws.s3.BucketVersioningV2(
    "images-bucket-versioning",
    bucket=images_bucket.id,
    versioning_configuration={
        "status": "Disabled",
    },
)

# CORS configuration for browser uploads
aws.s3.BucketCorsConfigurationV2(
    "images-bucket-cors",
    bucket=images_bucket.id,
    cors_rules=[
        {
            "allowed_headers": ["*"],
            "allowed_methods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
            "allowed_origins": allowed_origins_list,
            "expose_headers": ["ETag"],
            "max_age_seconds": 3000,
        }
    ],
)

# Block public access for images bucket
aws.s3.BucketPublicAccessBlock(
    "images-bucket-public-access",
    bucket=images_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True,
)

# Create inline policy for DynamoDB and S3 access
lambda_policy = aws.iam.RolePolicy(
    "lambda-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(posts_table.arn, images_bucket.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                        ],
                        "Resource": [
                            args[0],
                            f"{args[0]}/index/*",
                        ],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                        ],
                        "Resource": f"{args[1]}/*",
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["s3:ListBucket"],
                        "Resource": args[1],
                    },
                ],
            }
        )
    ),
)

# ========================================
# Lambda Layer (Dependencies)
# ========================================
# Lambda Layer with all dependencies (FastAPI, Pydantic, Mangum, etc.)
# Build with: ./scripts/build-lambda-layer.sh
# The layer ZIP is automatically managed by Pulumi


# Path to Lambda Layer ZIP
# Strategy: Use GITHUB_WORKSPACE env var in CI, fallback to relative path for local development
workspace_root = os.environ.get("GITHUB_WORKSPACE")
if workspace_root:
    # GitHub Actions: GITHUB_WORKSPACE points to repository root (/home/runner/work/multicloud-auto-deploy/multicloud-auto-deploy)
    # Build step creates ZIP at services/api/lambda-layer.zip (relative to repository root)
    layer_zip_path = pathlib.Path(
        workspace_root) / "services" / "api" / "lambda-layer.zip"
else:
    # Local development: Calculate relative path from this file
    # __file__ -> infrastructure/pulumi/aws/__main__.py
    # Go up 3 levels to reach project root, then down to services/api
    layer_zip_path = pathlib.Path(
        __file__).parent.parent.parent / "services" / "api" / "lambda-layer.zip"

# Check if layer ZIP exists
if not layer_zip_path.exists():
    pulumi.log.warn(
        f"Lambda Layer ZIP not found at {layer_zip_path}. "
        "Run './scripts/build-lambda-layer.sh' to build the layer. "
        "Using placeholder for now."
    )
    # Create a minimal placeholder if ZIP doesn't exist
    layer_zip_path = None
else:
    pulumi.log.info(
        f"Lambda Layer ZIP found: {layer_zip_path} ({os.path.getsize(layer_zip_path) / 1024 / 1024:.2f} MB)")

# Create Lambda Layer (only if ZIP exists)
lambda_layer = None
if layer_zip_path:
    lambda_layer = aws.lambda_.LayerVersion(
        "dependencies-layer",
        layer_name=f"{project_name}-{stack}-dependencies",
        code=pulumi.FileArchive(str(layer_zip_path)),
        compatible_runtimes=["python3.12"],
        description=f"Dependencies for {project_name} {stack} (FastAPI, Mangum, Pydantic, etc.)",
        opts=pulumi.ResourceOptions(
            # Delete old versions automatically (keeps only latest)
            delete_before_replace=True,
        ),
    )
    pulumi.export("lambda_layer_arn", lambda_layer.arn)
    pulumi.export("lambda_layer_version", lambda_layer.version)

# ========================================
# Lambda Function (FastAPI with Mangum)
# ========================================
# Note: Lambda function code is deployed separately using deploy-lambda-aws.sh script
# Pulumi manages the function configuration, but not the code itself

# Create a minimal placeholder Lambda function
# The actual code will be deployed via CI/CD or deploy script

placeholder_code = """
import json
def handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Please deploy actual code using deploy-lambda-aws.sh'})
    }
"""

lambda_function = aws.lambda_.Function(
    "api-function",
    name=f"{project_name}-{stack}-api",
    runtime="python3.12",
    handler="app.main.handler",  # FastAPI application entry point with Mangum
    role=lambda_role.arn,
    # 512MB for both staging and production (cold start performance)
    memory_size=512,
    timeout=30,
    # Use x86_64 for compatibility with custom layers
    architectures=["x86_64"],
    # Lambda Layer is automatically managed by Pulumi
    # If lambda-layer.zip exists, it will be deployed as a Layer Version
    # and automatically attached to this function
    layers=[lambda_layer.arn] if lambda_layer else [],
    # Use inline code or skip code updates
    # Code will be uploaded separately via deploy-lambda-aws.sh
    code=pulumi.AssetArchive(
        {"index.py": pulumi.StringAsset(placeholder_code)}),
    # Skip code and layer updates: deployed by deploy-aws.yml workflow
    # Layers are managed by the CI/CD pipeline (lambda-layer.zip is built at deploy time)
    opts=pulumi.ResourceOptions(
        ignore_changes=["code", "source_code_hash", "layers"]),
    environment={
        "variables": {
            "ENVIRONMENT": stack,
            "CLOUD_PROVIDER": "aws",
            "AUTH_PROVIDER": "cognito",
            "AUTH_DISABLED": "false",
            "SECRET_NAME": app_secret.name,
            "COGNITO_USER_POOL_ID": user_pool.id,
            "COGNITO_CLIENT_ID": user_pool_client.id,
            "COGNITO_REGION": region,
            "POSTS_TABLE_NAME": posts_table.name,
            "IMAGES_BUCKET_NAME": images_bucket.id,
            "CORS_ORIGINS": allowed_origins,
        }
    },
    tags=common_tags,
)

# Lambda Function URL (no API Gateway needed for simple HTTP)
lambda_url = aws.lambda_.FunctionUrl(
    "api-function-url",
    function_name=lambda_function.name,
    authorization_type="NONE",  # Public access
    cors={
        "allow_origins": allowed_origins_list,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "max_age": 3600,
    },
)

# ========================================
# API Gateway HTTP API v2
# ========================================
api_gateway = aws.apigatewayv2.Api(
    "http-api",
    name=f"{project_name}-{stack}-api",
    protocol_type="HTTP",
    cors_configuration={
        "allow_origins": allowed_origins_list,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
        "max_age": 3600,
    },
    tags=common_tags,
)

# API Gateway Integration with Lambda (backend api)
integration = aws.apigatewayv2.Integration(
    "lambda-integration",
    api_id=api_gateway.id,
    integration_type="AWS_PROXY",
    integration_uri=lambda_function.arn,
    integration_method="POST",
    payload_format_version="2.0",
)

# API Gateway Route
route = aws.apigatewayv2.Route(
    "default-route",
    api_id=api_gateway.id,
    route_key="$default",  # Catch all routes
    target=integration.id.apply(lambda id: f"integrations/{id}"),
)

# API Gateway Stage
stage = aws.apigatewayv2.Stage(
    "default-stage",
    api_id=api_gateway.id,
    name="$default",
    auto_deploy=True,
)

# Permission for API Gateway to invoke Lambda
aws.lambda_.Permission(
    "api-gateway-invoke",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=api_gateway.execution_arn.apply(lambda arn: f"{arn}/*/*"),
)

# ========================================
# S3 Bucket for Frontend
# ========================================
frontend_bucket = aws.s3.Bucket(
    "frontend-bucket",
    bucket=f"{project_name}-{stack}-frontend",
    website={
        "index_document": "index.html",
        "error_document": "index.html",  # For SPA routing
    },
    tags=common_tags,
)

# Disable block public access FIRST (before adding public policy)
frontend_public_access = aws.s3.BucketPublicAccessBlock(
    "frontend-public-access",
    bucket=frontend_bucket.id,
    block_public_acls=False,
    block_public_policy=False,
    ignore_public_acls=False,
    restrict_public_buckets=False,
)

# Make bucket public for static website hosting (after disabling public access block)
frontend_bucket_policy = aws.s3.BucketPolicy(
    "frontend-bucket-policy",
    bucket=frontend_bucket.id,
    policy=frontend_bucket.arn.apply(
        lambda arn: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"{arn}/*",
                    }
                ],
            }
        )
    ),
    opts=pulumi.ResourceOptions(depends_on=[frontend_public_access]),
)

# Configure bucket for website hosting
aws.s3.BucketWebsiteConfigurationV2(
    "frontend-website-config",
    bucket=frontend_bucket.id,
    index_document={
        "suffix": "index.html",
    },
    error_document={
        "key": "index.html",
    },
)

# ========================================
# CloudFront Distribution for Frontend
# ========================================
# CloudFront Origin Access Identity (OAI) for S3 access
cloudfront_oai = aws.cloudfront.OriginAccessIdentity(
    "cloudfront-oai",
    comment=f"{project_name}-{stack} CloudFront OAI",
)

# Update S3 bucket policy to allow CloudFront OAI access
cloudfront_bucket_policy = aws.s3.BucketPolicy(
    "cloudfront-bucket-policy",
    bucket=frontend_bucket.id,
    policy=pulumi.Output.all(frontend_bucket.arn, cloudfront_oai.iam_arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"{args[0]}/*",
                    },
                    {
                        "Sid": "CloudFrontOAIAccess",
                        "Effect": "Allow",
                        "Principal": {"AWS": args[1]},
                        "Action": "s3:GetObject",
                        "Resource": f"{args[0]}/*",
                    },
                ],
            }
        )
    ),
    opts=pulumi.ResourceOptions(
        depends_on=[frontend_public_access], replace_on_changes=["bucket"]
    ),
)

# ========================================
# AWS WAF for CloudFront
# ========================================
# WAF Web ACL for DDoS protection and rate limiting
# Note: WAF is disabled for staging to reduce cost (~$6/month)
if stack == "production":
    waf_web_acl = aws.wafv2.WebAcl(
        "cloudfront-waf",
        name=f"{project_name}-{stack}-cloudfront-waf",
        scope="CLOUDFRONT",  # Must be CLOUDFRONT for CloudFront distributions
        default_action=aws.wafv2.WebAclDefaultActionArgs(
            allow={},
        ),
        rules=[
            # AWS Managed Rule: Core Rule Set (CRS)
            aws.wafv2.WebAclRuleArgs(
                name="AWS-AWSManagedRulesCommonRuleSet",
                priority=1,
                override_action=aws.wafv2.WebAclRuleOverrideActionArgs(
                    none={},
                ),
                statement=aws.wafv2.WebAclRuleStatementArgs(
                    managed_rule_group_statement=aws.wafv2.WebAclRuleStatementManagedRuleGroupStatementArgs(
                        vendor_name="AWS",
                        name="AWSManagedRulesCommonRuleSet",
                    ),
                ),
                visibility_config=aws.wafv2.WebAclRuleVisibilityConfigArgs(
                    cloudwatch_metrics_enabled=True,
                    metric_name="AWSManagedRulesCommonRuleSetMetric",
                    sampled_requests_enabled=True,
                ),
            ),
            # AWS Managed Rule: Known Bad Inputs
            aws.wafv2.WebAclRuleArgs(
                name="AWS-AWSManagedRulesKnownBadInputsRuleSet",
                priority=2,
                override_action=aws.wafv2.WebAclRuleOverrideActionArgs(
                    none={},
                ),
                statement=aws.wafv2.WebAclRuleStatementArgs(
                    managed_rule_group_statement=aws.wafv2.WebAclRuleStatementManagedRuleGroupStatementArgs(
                        vendor_name="AWS",
                        name="AWSManagedRulesKnownBadInputsRuleSet",
                    ),
                ),
                visibility_config=aws.wafv2.WebAclRuleVisibilityConfigArgs(
                    cloudwatch_metrics_enabled=True,
                    metric_name="AWSManagedRulesKnownBadInputsRuleSetMetric",
                    sampled_requests_enabled=True,
                ),
            ),
            # Rate limiting: max 2000 requests per 5 minutes per IP
            aws.wafv2.WebAclRuleArgs(
                name="RateLimitRule",
                priority=3,
                action=aws.wafv2.WebAclRuleActionArgs(
                    block={},
                ),
                statement=aws.wafv2.WebAclRuleStatementArgs(
                    rate_based_statement=aws.wafv2.WebAclRuleStatementRateBasedStatementArgs(
                        limit=2000,
                        aggregate_key_type="IP",
                    ),
                ),
                visibility_config=aws.wafv2.WebAclRuleVisibilityConfigArgs(
                    cloudwatch_metrics_enabled=True,
                    metric_name="RateLimitRuleMetric",
                    sampled_requests_enabled=True,
                ),
            ),
        ],
        visibility_config=aws.wafv2.WebAclVisibilityConfigArgs(
            cloudwatch_metrics_enabled=True,
            metric_name=f"{project_name}-{stack}-waf-metrics",
            sampled_requests_enabled=True,
        ),
        tags=common_tags,
        # WAF for CloudFront must be created in us-east-1
        opts=pulumi.ResourceOptions(
            provider=aws.Provider("us-east-1-provider", region="us-east-1")
        ),
    )

# CloudFront Distribution with conditional WAF
# Use PriceClass_100 for staging (North America + Europe) to reduce cost
cloudfront_kwargs = {
    "enabled": True,
    "is_ipv6_enabled": True,
    "comment": f"{project_name}-{stack} Frontend Distribution",
    "default_root_object": "index.html",
    "price_class": "PriceClass_100" if stack == "staging" else "PriceClass_All",
    "origins": [
        aws.cloudfront.DistributionOriginArgs(
            origin_id=frontend_bucket.bucket_regional_domain_name,
            domain_name=frontend_bucket.bucket_regional_domain_name,
            s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                origin_access_identity=cloudfront_oai.cloudfront_access_identity_path,
            ),
        ),
    ],
    "default_cache_behavior": aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
        target_origin_id=frontend_bucket.bucket_regional_domain_name,
        viewer_protocol_policy="redirect-to-https",
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        cached_methods=["GET", "HEAD"],
        compress=True,
        forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
            query_string=False,
            cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                forward="none",
            ),
        ),
        min_ttl=0,
        default_ttl=3600,  # 1 hour
        max_ttl=86400,  # 24 hours
    ),
    "custom_error_responses": [
        aws.cloudfront.DistributionCustomErrorResponseArgs(
            error_code=403,
            response_code=200,
            response_page_path="/index.html",
        ),
        aws.cloudfront.DistributionCustomErrorResponseArgs(
            error_code=404,
            response_code=200,
            response_page_path="/index.html",
        ),
    ],
    "restrictions": aws.cloudfront.DistributionRestrictionsArgs(
        geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        ),
    ),
    "tags": common_tags,
}

# Custom domain configuration (optional)
custom_domain = config.get("customDomain")  # e.g., aws.yourdomain.com
acm_certificate_arn = config.get(
    "acmCertificateArn"
)  # ACM certificate ARN in us-east-1

if custom_domain and acm_certificate_arn:
    cloudfront_kwargs["aliases"] = [custom_domain]
    cloudfront_kwargs["viewer_certificate"] = (
        aws.cloudfront.DistributionViewerCertificateArgs(
            acm_certificate_arn=acm_certificate_arn,
            ssl_support_method="sni-only",
            minimum_protocol_version="TLSv1.2_2021",
        )
    )
else:
    cloudfront_kwargs["viewer_certificate"] = (
        aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True,
        )
    )

# Add WAF only for production
if stack == "production":
    cloudfront_kwargs["web_acl_id"] = waf_web_acl.arn

# /sns* → S3 bucket (React SPA static files)
# React SPA はビルド済み静的ファイルなので S3 オリジンを使用
# CloudFront Function で /sns/ → /sns/index.html にリライト (SPA ルーティング対応)
cf_function_name = f"spa-sns-rewrite-{stack}"
caller_identity = aws.get_caller_identity()
cf_function_arn = f"arn:aws:cloudfront::{caller_identity.account_id}:function/{cf_function_name}"
cloudfront_kwargs["ordered_cache_behaviors"] = [
    aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
        path_pattern="/sns*",
        target_origin_id=frontend_bucket.bucket_regional_domain_name,
        viewer_protocol_policy="redirect-to-https",
        allowed_methods=["GET", "HEAD", "OPTIONS"],
        cached_methods=["GET", "HEAD"],
        compress=True,
        # Managed CachingOptimized policy (静的ファイル向けキャッシュ)
        cache_policy_id="658327ea-f89d-4fab-a63d-7e88639e58f6",
        function_associations=[
            aws.cloudfront.DistributionOrderedCacheBehaviorFunctionAssociationArgs(
                event_type="viewer-request",
                function_arn=cf_function_arn,
            )
        ],
    )
]

cloudfront_distribution = aws.cloudfront.Distribution(
    "cloudfront-distribution", **cloudfront_kwargs
)

# ========================================
# Monitoring and Alerts
# ========================================
alarm_email = config.get("alarmEmail")
monitoring_resources = monitoring.setup_monitoring(
    project_name=project_name,
    stack=stack,
    lambda_function_name=lambda_function.name,
    api_gateway_id=api_gateway.id,
    api_gateway_name=api_gateway.name,
    cloudfront_distribution_id=cloudfront_distribution.id,
    alarm_email=alarm_email,
)

# ========================================
# Outputs
# ========================================
pulumi.export("lambda_function_name", lambda_function.name)
pulumi.export("lambda_function_arn", lambda_function.arn)
pulumi.export("lambda_function_url", lambda_url.function_url)
pulumi.export("api_gateway_id", api_gateway.id)
pulumi.export("api_gateway_endpoint", api_gateway.api_endpoint)
pulumi.export("api_url", api_gateway.api_endpoint)  # For workflow
pulumi.export("frontend_bucket_name", frontend_bucket.id)
pulumi.export(
    "frontend_url",
    frontend_bucket.website_endpoint.apply(
        lambda endpoint: f"http://{endpoint}"),
)
pulumi.export("cloudfront_distribution_id", cloudfront_distribution.id)
pulumi.export("cloudfront_domain", cloudfront_distribution.domain_name)
pulumi.export(
    "cloudfront_url",
    cloudfront_distribution.domain_name.apply(
        lambda domain: f"https://{domain}"),
)
# Custom domain exports (if configured)
if custom_domain:
    pulumi.export("custom_domain", custom_domain)
    pulumi.export("custom_domain_url", f"https://{custom_domain}")
    pulumi.export("acm_certificate_arn", acm_certificate_arn)
# WAF exports only for production
if stack == "production":
    pulumi.export("waf_web_acl_id", waf_web_acl.id)
    pulumi.export("waf_web_acl_arn", waf_web_acl.arn)
pulumi.export("secret_name", app_secret.name)
pulumi.export("secret_arn", app_secret.arn)
pulumi.export("cognito_user_pool_id", user_pool.id)
pulumi.export("cognito_user_pool_arn", user_pool.arn)
pulumi.export("cognito_client_id", user_pool_client.id)
pulumi.export("cognito_domain", user_pool_domain.domain)
pulumi.export("posts_table_name", posts_table.name)
pulumi.export("posts_table_arn", posts_table.arn)
pulumi.export("images_bucket_name", images_bucket.id)
pulumi.export("images_bucket_arn", images_bucket.arn)

# Monitoring exports
if monitoring_resources["sns_topic"]:
    pulumi.export("monitoring_sns_topic_arn",
                  monitoring_resources["sns_topic"].arn)
pulumi.export(
    "monitoring_lambda_alarms", list(
        monitoring_resources["lambda_alarms"].keys())
)
pulumi.export(
    "monitoring_api_alarms", list(
        monitoring_resources["api_gateway_alarms"].keys())
)
pulumi.export(
    "monitoring_cloudfront_alarms",
    list(monitoring_resources["cloudfront_alarms"].keys()),
)

# Cost estimation
pulumi.export(
    "cost_estimate",
    "AWS Lambda: 1M free requests/month, then $0.20 per 1M requests. "
    "API Gateway: $1 per million requests. "
    "S3: $0.023/GB/month. "
    "CloudFront: $0.085/GB for first 10TB/month (free tier: 1TB/month for 12 months). "
    "AWS WAF: $5/month per web ACL + $1/month per rule + $0.60 per 1M requests. "
    "Secrets Manager: $0.40/month per secret + $0.05 per 10,000 API calls. "
    "DynamoDB: Pay-per-request pricing (25 WCU and 25 RCU free tier). "
    "Cognito: 50,000 MAU free for first 12 months, then $0.0055 per MAU. "
    "Estimated: $10-25/month for low traffic with WAF and security features.",
)
