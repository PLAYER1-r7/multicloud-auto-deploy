import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pulumi
import pulumi_aws as aws

config = pulumi.Config()
project_name = config.get("project_name") or "simple-sns-web"
custom_tags = config.get_object("tags") or {}
api_base_url = config.get("api_base_url")
cognito_domain = config.get("cognito_domain")
cognito_client_id = config.get("cognito_client_id")
cognito_redirect_uri = config.get("cognito_redirect_uri")
cognito_logout_uri = config.get("cognito_logout_uri")
custom_domain = config.get("custom_domain")

base_tags = {
    "Project": project_name,
    "ManagedBy": "Pulumi",
    **custom_tags,
}

repo_root = Path(__file__).resolve().parents[4]
web_source_dir = repo_root / "services" / "simple_sns_web"
build_dir = Path(__file__).resolve().parent / ".build" / "simple_sns_web"
zip_path = build_dir / "lambda.zip"

lambda_python_version = "3.12"
lambda_platform = "manylinux2014_aarch64"
stage_name = ""


def build_lambda_package() -> None:
    if not web_source_dir.exists():
        raise FileNotFoundError(f"Web source not found: {web_source_dir}")

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(web_source_dir / "app", build_dir / "app")
    shutil.copy(web_source_dir / "handler.py", build_dir / "handler.py")

    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(web_source_dir / "requirements.txt"),
            "-t",
            str(build_dir),
            "--platform",
            lambda_platform,
            "--python-version",
            lambda_python_version,
            "--implementation",
            "cp",
            "--abi",
            "cp312",
            "--only-binary=:all:",
        ]
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in build_dir.rglob("*"):
            if path.is_file() and path != zip_path:
                zf.write(path, path.relative_to(build_dir))


build_lambda_package()

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

env_vars = {
    "API_BASE_URL": api_base_url or "",
    "STAGE_NAME": stage_name,
}

if cognito_domain:
    env_vars["COGNITO_DOMAIN"] = cognito_domain
if cognito_client_id:
    env_vars["COGNITO_CLIENT_ID"] = cognito_client_id
if cognito_redirect_uri:
    env_vars["COGNITO_REDIRECT_URI"] = cognito_redirect_uri
if cognito_logout_uri:
    env_vars["COGNITO_LOGOUT_URI"] = cognito_logout_uri

web_lambda = aws.lambda_.Function(
    f"{project_name}-web",
    runtime="python3.12",
    architectures=["arm64"],
    timeout=10,
    memory_size=256,
    handler="handler.handler",
    role=lambda_role.arn,
    code=pulumi.FileArchive(str(zip_path)),
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables=env_vars
    ),
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
    integration_uri=web_lambda.invoke_arn,
    payload_format_version="2.0",
)

api_route = aws.apigatewayv2.Route(
    f"{project_name}-route",
    api_id=api.id,
    route_key="$default",
    target=api_integration.id.apply(
        lambda integration_id: f"integrations/{integration_id}"),
)

api_stage = aws.apigatewayv2.Stage(
    f"{project_name}-stage",
    api_id=api.id,
    name="$default",
    auto_deploy=True,
)

aws.lambda_.Permission(
    f"{project_name}-apigw-permission",
    action="lambda:InvokeFunction",
    function=web_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=pulumi.Output.concat(api.execution_arn, "/*/*"),
)

if custom_domain:
    certificate = aws.acm.Certificate(
        f"{project_name}-cert",
        domain_name=custom_domain,
        validation_method="DNS",
        tags=base_tags,
    )

    domain_name = aws.apigatewayv2.DomainName(
        f"{project_name}-domain",
        domain_name=custom_domain,
        domain_name_configuration=aws.apigatewayv2.DomainNameDomainNameConfigurationArgs(
            certificate_arn=certificate.arn,
            endpoint_type="REGIONAL",
            security_policy="TLS_1_2",
        ),
    )

    aws.apigatewayv2.ApiMapping(
        f"{project_name}-mapping",
        api_id=api.id,
        domain_name=domain_name.id,
        stage=api_stage.id,
    )

    pulumi.export("cert_validation_domain",
                  certificate.domain_validation_options[0].resource_record_name)
    pulumi.export("cert_validation_value",
                  certificate.domain_validation_options[0].resource_record_value)
    pulumi.export("custom_domain_url", pulumi.Output.concat(
        "https://", custom_domain))
    pulumi.export("api_gateway_domain_name_target",
                  domain_name.domain_name_configuration.target_domain_name)

pulumi.export("web_url", api.api_endpoint)
