import pulumi_azure_native as azure_native
from config import (
    project_name,
    environment,
    stack,
    base_tags,
    resource_group,
    azure_tenant_id,
    azure_client_id,
    auth_provider,
    cognito_user_pool_id,
    cognito_client_id,
    deploy_service
)


def create_compute_resources(storage, auth=None):
    images_storage = storage["images_storage"]
    images_container = storage["images_container"]
    cosmos_account = storage["cosmos_account"]
    registry = storage["registry"]

    current_client_id = azure_client_id
    current_tenant_id = azure_tenant_id

    if auth:
        current_client_id = auth["client_id"]
        current_tenant_id = auth["tenant_id"]

    images_keys = azure_native.storage.list_storage_account_keys_output(
        resource_group_name=resource_group.name,
        account_name=images_storage.name,
    )

    cosmos_keys = azure_native.cosmosdb.list_database_account_keys_output(
        resource_group_name=resource_group.name,
        account_name=cosmos_account.name,
    )

    registry_credentials = azure_native.containerregistry.list_registry_credentials_output(
        resource_group_name=resource_group.name,
        registry_name=registry.name,
    )

    api_image_name = registry.login_server.apply(
        lambda server: f"{server}/{project_name}-api:latest"
    )

    log_workspace = azure_native.operationalinsights.Workspace(
        f"{project_name}-logs",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        sku=azure_native.operationalinsights.WorkspaceSkuArgs(
            name="PerGB2018"),
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

    api_secrets = [
        azure_native.app.SecretArgs(
            name="acr-pwd", value=registry_credentials.passwords[0].value
        ),
        azure_native.app.SecretArgs(
            name="cosmos-key", value=cosmos_keys.primary_master_key
        ),
        azure_native.app.SecretArgs(
            name="storage-key", value=images_keys.keys[0].value
        ),
    ]

    api_container_app = None
    if deploy_service or (deploy_service is None):
        api_container_app = azure_native.app.ContainerApp(
            f"{project_name}-api",
            resource_group_name=resource_group.name,
            managed_environment_id=app_environment.id,
            configuration=azure_native.app.ConfigurationArgs(
                ingress=azure_native.app.IngressArgs(
                    external=True,
                    target_port=8080,
                    transport="auto",
                ),
                registries=[
                    azure_native.app.RegistryCredentialsArgs(
                        server=registry.login_server,
                        username=registry_credentials.username,
                        password_secret_ref="acr-pwd",
                    )
                ],
                secrets=api_secrets,
            ),
            template=azure_native.app.TemplateArgs(
                containers=[
                    azure_native.app.ContainerArgs(
                        name="api",
                        image=api_image_name,
                        resources=azure_native.app.ContainerResourcesArgs(
                            cpu=0.25,
                            memory="0.5Gi",
                        ),
                        env=[
                            azure_native.app.EnvironmentVarArgs(
                                name="CLOUD_PROVIDER", value="azure"
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="AUTH_PROVIDER", value=auth_provider
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="COGNITO_USER_POOL_ID", value=cognito_user_pool_id
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="COGNITO_CLIENT_ID", value=cognito_client_id
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="AZURE_TENANT_ID", value=current_tenant_id
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="AZURE_CLIENT_ID", value=current_client_id
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="COSMOS_DB_ENDPOINT",
                                value=cosmos_account.document_endpoint,
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="COSMOS_DB_KEY", secret_ref="cosmos-key"
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="COSMOS_DB_DATABASE", value="simple-sns"
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="COSMOS_DB_CONTAINER", value="items"
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="AZURE_STORAGE_ACCOUNT_NAME",
                                value=images_storage.name,
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="AZURE_STORAGE_ACCOUNT_KEY",
                                secret_ref="storage-key",
                            ),
                            azure_native.app.EnvironmentVarArgs(
                                name="AZURE_STORAGE_CONTAINER",
                                value=images_container.name,
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

    return {
        "api_container_app": api_container_app,
    }
