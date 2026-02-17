import hashlib

import pulumi
import pulumi_gcp as gcp

config = pulumi.Config()
project_name = config.get("project_name") or "simple-sns-web"
environment = config.get("environment") or "prod"
region = gcp.config.region or "asia-northeast1"
project = gcp.config.project or config.get("gcp:project")
api_base_url = config.get("api_base_url") or ""
client_id = config.get("gcp_client_id") or ""
redirect_uri = config.get("gcp_redirect_uri") or ""
logout_uri = config.get("gcp_logout_uri") or ""
auth_provider = config.get("auth_provider") or "gcp"
cognito_user_pool_id = config.get("cognito_user_pool_id") or ""
cognito_client_id = config.get("cognito_client_id") or ""
cognito_domain = config.get("cognito_domain") or ""
firebase_api_key = config.get("firebase_api_key")
firebase_app_id = config.get("firebase_app_id")
web_image_override = config.get("web_image") or ""
deploy_service = config.get_bool("deploy_service")
custom_domain = config.get("custom_domain")

if not project:
    raise ValueError("gcp:project is required")

if deploy_service is None:
    deploy_service = True


def name_suffix(base: str, env: str, stack: str) -> str:
    return hashlib.sha1(f"{base}-{env}-{stack}".encode("utf-8")).hexdigest()[:6]


def resource_name(base: str, env: str, stack: str, suffix: str) -> str:
    return f"{base}-{env}-{suffix}".lower().replace("_", "-")


stack = pulumi.get_stack()
suffix = name_suffix(project_name, environment, stack)

required_services = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "identitytoolkit.googleapis.com",
    "firebase.googleapis.com",
    "apikeys.googleapis.com",
]

service_apis = [
    gcp.projects.Service(
        f"web-{service.replace('.', '-')}",
        service=service,
        project=project,
        disable_on_destroy=False,
    )
    for service in required_services
]

service_api_opts = pulumi.ResourceOptions(depends_on=service_apis)

# Create API Key for Firebase if not provided (Skipped due to permission issues, user must provide via config)
final_firebase_api_key = pulumi.Output.from_input(
    firebase_api_key or "CHANGE_ME_TO_FIREBASE_API_KEY")

repository = gcp.artifactregistry.Repository(
    "web-repo",
    location=region,
    repository_id=resource_name(
        project_name, environment, stack, f"web-{suffix}"),
    format="DOCKER",
    opts=service_api_opts,
)

web_image_name = (
    pulumi.Output.from_input(web_image_override)
    if web_image_override
    else pulumi.Output.concat(
        region,
        "-docker.pkg.dev/",
        project,
        "/",
        repository.repository_id,
        "/simple-sns-web:latest",
    )
)

service = None
if deploy_service:
    service = gcp.cloudrun.Service(
        "web-service",
        location=region,
        template=gcp.cloudrun.ServiceTemplateArgs(
            metadata=gcp.cloudrun.ServiceTemplateMetadataArgs(
                annotations={
                    "autoscaling.knative.dev/minScale": "0",
                    "autoscaling.knative.dev/maxScale": "1",
                }
            ),
            spec=gcp.cloudrun.ServiceTemplateSpecArgs(
                containers=[gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                    image=web_image_name,
                    envs=[
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="API_BASE_URL", value=api_base_url),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="AUTH_PROVIDER", value=auth_provider),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="GCP_CLIENT_ID", value=client_id),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="GCP_REDIRECT_URI", value=redirect_uri),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="GCP_LOGOUT_URI", value=logout_uri),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="COGNITO_USER_POOL_ID", value=cognito_user_pool_id),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="COGNITO_CLIENT_ID", value=cognito_client_id),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="COGNITO_DOMAIN", value=cognito_domain),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="FIREBASE_API_KEY", value=final_firebase_api_key),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="FIREBASE_AUTH_DOMAIN", value=pulumi.Output.concat(project, ".firebaseapp.com")),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="FIREBASE_PROJECT_ID", value=project),
                        gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                            name="FIREBASE_APP_ID", value=firebase_app_id or ""),
                    ],
                )],
            ),
        ),
        traffics=[gcp.cloudrun.ServiceTrafficArgs(
            percent=100, latest_revision=True)],
        opts=service_api_opts,
    )

    invoker = gcp.cloudrun.IamMember(
        "web-invoker",
        service=service.name,
        location=service.location,
        role="roles/run.invoker",
        member="allUsers",
    )

    if custom_domain:
        domain_mapping = gcp.cloudrun.DomainMapping(
            "web-domain-mapping",
            location=region,
            name=custom_domain,
            metadata=gcp.cloudrun.DomainMappingMetadataArgs(
                namespace=project,
            ),
            spec=gcp.cloudrun.DomainMappingSpecArgs(
                route_name=service.name,
            ),
        )

web_url = (
    service.statuses.apply(
        lambda statuses: statuses[0].url if statuses else None)
    if service
    else None
)
pulumi.export("web_url", web_url)
pulumi.export("web_image_name", web_image_name)
pulumi.export("web_repository", repository.repository_id)
