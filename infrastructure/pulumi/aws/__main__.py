"""
Multi-Cloud Auto Deploy - AWS Pulumi Implementation

Architecture:
- Lambda Function (Python 3.12, ZIP deployment)
- API Gateway (HTTP API v2)
- S3 (Static website hosting)
- CloudFront (Optional, for custom domain)

Cost: ~$2-5/month for low traffic
"""

import json
import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
aws_config = pulumi.Config("aws")
region = aws_config.get("region") or "us-east-1"
stack = pulumi.get_stack()
project_name = "multicloud-auto-deploy"

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

# ========================================
# Lambda Function (FastAPI with Mangum)
# ========================================
# Note: Lambda function code is deployed separately using deploy-lambda-aws.sh script
# Pulumi manages the function configuration, but not the code itself

# Create a minimal placeholder Lambda function
# The actual code will be deployed via CI/CD or deploy script
import base64

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
    handler="index.handler",
    role=lambda_role.arn,
    memory_size=512,
    timeout=30,
    architectures=["x86_64"],
    # Use inline code or skip code updates
    # Code will be uploaded separately via deploy-lambda-aws.sh
    code=pulumi.AssetArchive({"index.py": pulumi.StringAsset(placeholder_code)}),
    # Skip code updates if function already exists
    opts=pulumi.ResourceOptions(ignore_changes=["code", "source_code_hash"]),
    environment={
        "variables": {
            "ENVIRONMENT": stack,
            "CLOUD_PROVIDER": "aws",
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
        "allow_origins": ["*"],
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "max_age": 3600,
    },
)

# Alternative: API Gateway HTTP API v2 (more features)
api_gateway = aws.apigatewayv2.Api(
    "http-api",
    name=f"{project_name}-{stack}-api",
    protocol_type="HTTP",
    cors_configuration={
        "allow_origins": ["*"],
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "max_age": 3600,
    },
    tags=common_tags,
)

# API Gateway Integration with Lambda
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

# CloudFront Distribution
cloudfront_distribution = aws.cloudfront.Distribution(
    "cloudfront-distribution",
    enabled=True,
    is_ipv6_enabled=True,
    comment=f"{project_name}-{stack} Frontend Distribution",
    default_root_object="index.html",
    origins=[
        aws.cloudfront.DistributionOriginArgs(
            origin_id=frontend_bucket.bucket_regional_domain_name,
            domain_name=frontend_bucket.bucket_regional_domain_name,
            s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                origin_access_identity=cloudfront_oai.cloudfront_access_identity_path,
            ),
        )
    ],
    default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
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
    # Custom error response for SPA routing
    custom_error_responses=[
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
    restrictions=aws.cloudfront.DistributionRestrictionsArgs(
        geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        ),
    ),
    viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True,
    ),
    tags=common_tags,
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
    frontend_bucket.website_endpoint.apply(lambda endpoint: f"http://{endpoint}"),
)
pulumi.export("cloudfront_distribution_id", cloudfront_distribution.id)
pulumi.export("cloudfront_domain", cloudfront_distribution.domain_name)
pulumi.export(
    "cloudfront_url",
    cloudfront_distribution.domain_name.apply(lambda domain: f"https://{domain}"),
)

# Cost estimation
pulumi.export(
    "cost_estimate",
    "AWS Lambda: 1M free requests/month, then $0.20 per 1M requests. "
    "API Gateway: $1 per million requests. "
    "S3: $0.023/GB/month. "
    "CloudFront: $0.085/GB for first 10TB/month (free tier: 1TB/month for 12 months). "
    "Estimated: $2-10/month for low traffic.",
)
