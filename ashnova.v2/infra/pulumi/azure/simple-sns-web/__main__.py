import hashlib
from pathlib import Path

import pulumi
import pulumi_azure_native as azure_native

config = pulumi.Config()
project_name = config.get("project_name") or "simple-sns-web"
environment = config.get("environment") or "prod"
location = config.get("azure:location") or "japaneast"
custom_tags = config.get_object("tags") or {}
api_base_url = config.get("api_base_url") or ""
azure_tenant_id = config.get("azure_tenant_id") or ""
azure_client_id = config.get("azure_client_id") or ""
azure_redirect_uri = config.get("azure_redirect_uri") or ""
azure_logout_uri = config.get("azure_logout_uri") or ""
custom_domain = config.get("custom_domain") or ""
enable_managed_cert = (config.get("enable_managed_cert") or "").strip().lower() in (
    "1",
    "true",
    "yes",
)
bind_managed_cert = (config.get("bind_managed_cert") or "").strip().lower() in (
    "1",
    "true",
    "yes",
)

base_tags = {
    "Project": project_name,
    "Environment": environment,
    "ManagedBy": "Pulumi",
    **custom_tags,
}

repo_root = Path(__file__).resolve().parents[4]
web_source_dir = repo_root / "services" / "simple_sns_web"


def sanitize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


stack = pulumi.get_stack()

resource_group = azure_native.resources.ResourceGroup(
    f"{project_name}-rg",
    resource_group_name=f"rg-{project_name}-{environment}",
    location=location,
    tags=base_tags,
)

registry = azure_native.containerregistry.Registry(
    f"{project_name}-registry",
    resource_group_name=resource_group.name,
    registry_name=f"{sanitize_name(project_name)}{sanitize_name(environment)}{sanitize_name(stack)}"[
        :50],
    location=resource_group.location,
    sku=azure_native.containerregistry.SkuArgs(name="Basic"),
    admin_user_enabled=True,
    tags=base_tags,
)

registry_credentials = azure_native.containerregistry.list_registry_credentials_output(
    resource_group_name=resource_group.name,
    registry_name=registry.name,
)

web_image_name = registry.login_server.apply(
    lambda server: f"{server}/{project_name}-web:latest"
)

log_workspace = azure_native.operationalinsights.Workspace(
    f"{project_name}-logs",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=azure_native.operationalinsights.WorkspaceSkuArgs(name="PerGB2018"),
    retention_in_days=30,
    tags=base_tags,
)

log_shared_keys = azure_native.operationalinsights.get_shared_keys_output(
    resource_group_name=resource_group.name,
    workspace_name=log_workspace.name,
)

app_environment = azure_native.app.ManagedEnvironment(
    f"{project_name}-env",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    app_logs_configuration=azure_native.app.AppLogsConfigurationArgs(
        destination="log-analytics",
        log_analytics_configuration=azure_native.app.LogAnalyticsConfigurationArgs(
            customer_id=log_workspace.customer_id,
            shared_key=log_shared_keys.primary_shared_key,
        ),
    ),
    tags=base_tags,
)

verification_id = azure_native.app.get_custom_domain_verification_id_output().value

managed_cert = None
custom_domains = None
if custom_domain:
    if enable_managed_cert:
        managed_cert = azure_native.app.ManagedCertificate(
            f"{project_name}-cert",
            resource_group_name=resource_group.name,
            environment_name=app_environment.name,
            location=resource_group.location,
            properties=azure_native.app.ManagedCertificatePropertiesArgs(
                subject_name=custom_domain,
                domain_control_validation=azure_native.app.ManagedCertificateDomainControlValidation.CNAME,
            ),
            tags=base_tags,
        )
        if bind_managed_cert:
            custom_domains = [
                azure_native.app.CustomDomainArgs(
                    name=custom_domain,
                    binding_type=azure_native.app.BindingType.SNI_ENABLED,
                    certificate_id=managed_cert.id,
                )
            ]
        else:
            custom_domains = [
                azure_native.app.CustomDomainArgs(
                    name=custom_domain,
                    binding_type=azure_native.app.BindingType.DISABLED,
                )
            ]
    else:
        custom_domains = [
            azure_native.app.CustomDomainArgs(
                name=custom_domain,
                binding_type=azure_native.app.BindingType.DISABLED,
            )
        ]

web_secrets = [
    azure_native.app.SecretArgs(
        name="acr-pwd", value=registry_credentials.passwords[0].value
    )
]

web_container_app = azure_native.app.ContainerApp(
    f"{project_name}-web",
    resource_group_name=resource_group.name,
    managed_environment_id=app_environment.id,
    configuration=azure_native.app.ConfigurationArgs(
        ingress=azure_native.app.IngressArgs(
            external=True,
            target_port=8080,
            transport="auto",
            custom_domains=custom_domains,
        ),
        registries=[
            azure_native.app.RegistryCredentialsArgs(
                server=registry.login_server,
                username=registry_credentials.username,
                password_secret_ref="acr-pwd",
            )
        ],
        secrets=web_secrets,
    ),
    template=azure_native.app.TemplateArgs(
        containers=[
            azure_native.app.ContainerArgs(
                name="web",
                image=web_image_name,
                resources=azure_native.app.ContainerResourcesArgs(
                    cpu=0.25,
                    memory="0.5Gi",
                ),
                env=[
                    azure_native.app.EnvironmentVarArgs(
                        name="API_BASE_URL", value=api_base_url
                    ),
                    azure_native.app.EnvironmentVarArgs(
                        name="AUTH_PROVIDER", value="azure"
                    ),
                    azure_native.app.EnvironmentVarArgs(
                        name="AZURE_TENANT_ID", value=azure_tenant_id
                    ),
                    azure_native.app.EnvironmentVarArgs(
                        name="AZURE_CLIENT_ID", value=azure_client_id
                    ),
                    azure_native.app.EnvironmentVarArgs(
                        name="AZURE_REDIRECT_URI", value=azure_redirect_uri
                    ),
                    azure_native.app.EnvironmentVarArgs(
                        name="AZURE_LOGOUT_URI", value=azure_logout_uri
                    ),
                ],
            )
        ],
        scale=azure_native.app.ScaleArgs(
            min_replicas=0,
            max_replicas=1,
        ),
    ),
    tags=base_tags,
)

pulumi.export(
    "web_url",
    web_container_app.latest_revision_fqdn.apply(
        lambda host: f"https://{host}"),
)
pulumi.export("web_custom_domain", custom_domain)
pulumi.export(
    "web_custom_domain_cname_target",
    web_container_app.latest_revision_fqdn,
)
pulumi.export(
    "web_custom_domain_txt_name",
    pulumi.Output.from_input(custom_domain).apply(
        lambda domain: f"asuid.{domain}" if domain else ""
    ),
)
pulumi.export(
    "web_custom_domain_txt_value",
    pulumi.Output.from_input(custom_domain).apply(
        lambda domain: verification_id if domain else ""
    ),
)
