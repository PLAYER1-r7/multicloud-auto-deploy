import json
import pulumi
import pulumi_aws as aws
from config import project_name, base_tags


def create_compute_resources(storage, auth, zip_path):
    posts_table = storage["posts_table"]
    images_bucket = storage["images_bucket"]
    distribution = storage["distribution"]
    user_pool = auth["user_pool"]
    user_pool_client = auth["user_pool_client"]

    assume_role = aws.iam.get_policy_document(
        statements=[
            aws.iam.GetPolicyDocumentStatementArgs(
                actions=["sts:AssumeRole"],
                principals=[
                    aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                        type="Service",
                        identifiers=["lambda.amazonaws.com"],
                    )
                ],
            )
        ]
    )

    lambda_role = aws.iam.Role(
        f"{project_name}-lambda-role",
        assume_role_policy=assume_role.json,
        tags=base_tags,
    )

    aws.iam.RolePolicyAttachment(
        f"{project_name}-lambda-basic",
        role=lambda_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

    lambda_policy = aws.iam.Policy(
        f"{project_name}-lambda-policy",
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
                                "dynamodb:DeleteItem",
                                "dynamodb:Query",
                                "dynamodb:BatchGetItem",
                            ],
                            "Resource": [args[0], f"{args[0]}/index/*"],
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
                    ],
                }
            )
        ),
    )

    aws.iam.RolePolicyAttachment(
        f"{project_name}-lambda-policy-attach",
        role=lambda_role.name,
        policy_arn=lambda_policy.arn,
    )

    api_lambda = aws.lambda_.Function(
        f"{project_name}-api",
        runtime="python3.12",
        architectures=["arm64"],
        timeout=10,
        memory_size=256,
        handler="handler.handler",
        role=lambda_role.arn,
        code=pulumi.FileArchive(str(zip_path)),
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "POSTS_TABLE_NAME": posts_table.name,
                "IMAGES_BUCKET_NAME": images_bucket.bucket,
                "IMAGES_CDN_URL": pulumi.Output.concat("https://", distribution.domain_name),
                "COGNITO_USER_POOL_ID": user_pool.id,
                "COGNITO_CLIENT_ID": user_pool_client.id,
            }
        ),
        tags=base_tags,
    )

    aws.cloudwatch.LogGroup(
        f"{project_name}-log-group",
        name=pulumi.Output.concat("/aws/lambda/", api_lambda.name),
        retention_in_days=30,
        tags=base_tags,
    )

    api = aws.apigatewayv2.Api(
        f"{project_name}-api",
        name=f"{project_name}-api",
        protocol_type="HTTP",
        tags=base_tags,
    )

    api_integration = aws.apigatewayv2.Integration(
        f"{project_name}-integration",
        api_id=api.id,
        integration_type="AWS_PROXY",
        integration_uri=api_lambda.invoke_arn,
        payload_format_version="2.0",
    )

    aws.apigatewayv2.Route(
        f"{project_name}-route",
        api_id=api.id,
        route_key="$default",
        target=api_integration.id.apply(
            lambda integration_id: f"integrations/{integration_id}"),
    )

    aws.apigatewayv2.Stage(
        f"{project_name}-stage",
        api_id=api.id,
        name="$default",
        auto_deploy=True,
    )

    aws.lambda_.Permission(
        f"{project_name}-apigw-permission",
        action="lambda:InvokeFunction",
        function=api_lambda.name,
        principal="apigateway.amazonaws.com",
        source_arn=pulumi.Output.concat(api.execution_arn, "/*/*"),
    )

    return {
        "api_lambda": api_lambda,
        "api": api,
    }
