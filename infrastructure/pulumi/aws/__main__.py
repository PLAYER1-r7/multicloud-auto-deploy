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
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Effect": "Allow",
        }]
    }),
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
# Note: ZIP file must be created in GitHub Actions workflow
# using: pip install -r requirements.txt -t package/ && zip -r function.zip

lambda_function = aws.lambda_.Function(
    "api-function",
    name=f"{project_name}-{stack}-api",
    runtime="python3.12",
    handler="handler.handler",  # handler.py の handler 関数
    role=lambda_role.arn,
    memory_size=512,
    timeout=30,
    architectures=["x86_64"],
    
    # Code will be uploaded separately via S3 or directly
    # This is a placeholder - actual deployment via workflow
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../../../services/api")  # Temporary
    }),
    
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
    }
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

# Make bucket public for static website hosting
frontend_bucket_policy = aws.s3.BucketPolicy(
    "frontend-bucket-policy",
    bucket=frontend_bucket.id,
    policy=frontend_bucket.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"{arn}/*"
        }]
    }))
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

# Disable block public access
aws.s3.BucketPublicAccessBlock(
    "frontend-public-access",
    bucket=frontend_bucket.id,
    block_public_acls=False,
    block_public_policy=False,
    ignore_public_acls=False,
    restrict_public_buckets=False,
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
pulumi.export("frontend_url", frontend_bucket.website_endpoint.apply(
    lambda endpoint: f"http://{endpoint}"
))

# Cost estimation
pulumi.export("cost_estimate", 
    "AWS Lambda: 1M free requests/month, then $0.20 per 1M requests. "
    "API Gateway: $1 per million requests. "
    "S3: $0.023/GB/month. "
    "Estimated: $2-5/month for low traffic."
)
