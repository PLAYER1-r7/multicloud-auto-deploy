"""
AWS Simple SNS - Pulumi Infrastructure

Architecture:
- API Gateway (HTTP API)
- Lambda Function (Python 3.12)
- DynamoDB Table
- S3 Bucket for images
- CloudFront Distribution (optional)
- Cognito User Pool (optional)
"""
import json
import zipfile
from pathlib import Path
import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
environment = config.get("environment") or "staging"
project_name = config.get("project_name") or "simple-sns"
aws_region = config.get("aws:region") or "ap-northeast-1"

# Tags
tags = {
    "Project": project_name,
    "Environment": environment,
    "ManagedBy": "pulumi",
    "Framework": "python",
}


# ========================================
# 1. DynamoDB Table
# ========================================

messages_table = aws.dynamodb.Table(
    "messages-table",
    name=f"{project_name}-messages-{environment}",
    billing_mode="PAY_PER_REQUEST",  # On-demand pricing
    hash_key="id",
    attributes=[
        aws.dynamodb.TableAttributeArgs(name="id", type="S"),
        aws.dynamodb.TableAttributeArgs(name="created_at", type="S"),
    ],
    global_secondary_indexes=[
        aws.dynamodb.TableGlobalSecondaryIndexArgs(
            name="created_at-index",
            hash_key="id",
            range_key="created_at",
            projection_type="ALL",
        )
    ],
    tags=tags,
)


# ========================================
# 2. S3 Bucket for Images
# ========================================

images_bucket = aws.s3.BucketV2(
    "images-bucket",
    bucket=f"{project_name}-images-{environment}",
    tags=tags,
)

# Block public access
aws.s3.BucketPublicAccessBlock(
    "images-bucket-public-access-block",
    bucket=images_bucket.id,
    block_public_acls=False,
    block_public_policy=False,
    ignore_public_acls=False,
    restrict_public_buckets=False,
)

# Bucket policy for public read
bucket_policy = aws.s3.BucketPolicy(
    "images-bucket-policy",
    bucket=images_bucket.id,
    policy=images_bucket.arn.apply(
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
)

# CORS configuration
aws.s3.BucketCorsConfigurationV2(
    "images-bucket-cors",
    bucket=images_bucket.id,
    cors_rules=[
        aws.s3.BucketCorsConfigurationV2CorsRuleArgs(
            allowed_headers=["*"],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD"],
            allowed_origins=["*"],  # In production, restrict to your domain
            expose_headers=["ETag"],
            max_age_seconds=3600,
        )
    ],
)


# ========================================
# 3. Lambda Function
# ========================================

# IAM Role for Lambda
lambda_role = aws.iam.Role(
    "lambda-role",
    name=f"{project_name}-lambda-role-{environment}",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    ),
    tags=tags,
)

# Attach basic Lambda execution policy
aws.iam.RolePolicyAttachment(
    "lambda-basic-execution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
)

# Custom policy for DynamoDB and S3
lambda_policy = aws.iam.RolePolicy(
    "lambda-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(messages_table.arn, images_bucket.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:PutItem",
                            "dynamodb:GetItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                        ],
                        "Resource": [args[0], f"{args[0]}/index/*"],
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3:PutObject",
                            "s3:GetObject",
                            "s3:DeleteObject",
                        ],
                        "Resource": f"{args[1]}/*",
                    },
                ],
            }
        )
    ),
)

# Build Lambda deployment package
def build_lambda_package():
    """Build Lambda deployment package"""
    api_dir = Path("../../../../services/api")
    build_dir = Path(".build")
    build_dir.mkdir(exist_ok=True)
    
    zip_path = build_dir / "lambda.zip"
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add app code
        for py_file in (api_dir / "app").rglob("*.py"):
            zipf.write(py_file, f"app/{py_file.relative_to(api_dir / 'app')}")
    
    return str(zip_path)

# Create Lambda function
lambda_function = aws.lambda_.Function(
    "api-lambda",
    name=f"{project_name}-api-{environment}",
    runtime="python3.12",
    handler="app.main.handler",  # Using Mangum handler
    role=lambda_role.arn,
    code=pulumi.FileArchive(build_lambda_package()),
    timeout=30,
    memory_size=512,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "CLOUD_PROVIDER": "aws",
            "AWS_REGION": aws_region,
            "DYNAMODB_TABLE_NAME": messages_table.name,
            "S3_BUCKET_NAME": images_bucket.bucket,
            "CORS_ORIGINS": "*",
            "AUTH_DISABLED": "true",
        }
    ),
    tags=tags,
)


# ========================================
# 4. API Gateway (HTTP API)
# ========================================

api = aws.apigatewayv2.Api(
    "http-api",
    name=f"{project_name}-api-{environment}",
    protocol_type="HTTP",
    cors_configuration=aws.apigatewayv2.ApiCorsConfigurationArgs(
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=3600,
    ),
    tags=tags,
)

# Lambda integration
integration = aws.apigatewayv2.Integration(
    "lambda-integration",
    api_id=api.id,
    integration_type="AWS_PROXY",
    integration_uri=lambda_function.arn,
    payload_format_version="2.0",
)

# Default route
route = aws.apigatewayv2.Route(
    "default-route",
    api_id=api.id,
    route_key="$default",
    target=integration.id.apply(lambda id: f"integrations/{id}"),
)

# Stage
stage = aws.apigatewayv2.Stage(
    "api-stage",
    api_id=api.id,
    name="$default",
    auto_deploy=True,
)

# Lambda permission for API Gateway
aws.lambda_.Permission(
    "api-lambda-permission",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=api.execution_arn.apply(lambda arn: f"{arn}/*/*"),
)


# ========================================
# 5. Outputs
# ========================================

pulumi.export("api_url", api.api_endpoint)
pulumi.export("messages_table_name", messages_table.name)
pulumi.export("images_bucket_name", images_bucket.bucket)
pulumi.export("lambda_function_name", lambda_function.name)
pulumi.export("region", aws_region)
