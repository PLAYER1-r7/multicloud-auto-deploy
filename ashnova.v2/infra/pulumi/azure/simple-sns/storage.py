import pulumi_azure_native as azure_native
from config import (
    project_name,
    environment,
    stack,
    base_tags,
    resource_group,
    cosmos_account_suffix,
    sanitize_name,
    storage_account_name,
    cosmos_account_name
)


def create_storage_resources():
    images_storage = azure_native.storage.StorageAccount(
        f"{project_name}-images-storage",
        account_name=storage_account_name(
            f"{project_name}img", environment, stack),
        resource_group_name=resource_group.name,
        location=resource_group.location,
        sku=azure_native.storage.SkuArgs(
            name=azure_native.storage.SkuName.STANDARD_LRS),
        kind=azure_native.storage.Kind.STORAGE_V2,
        enable_https_traffic_only=True,
        allow_blob_public_access=True,
        minimum_tls_version=azure_native.storage.MinimumTlsVersion.TLS1_2,
        tags=base_tags,
    )

    images_container = azure_native.storage.BlobContainer(
        f"{project_name}-images-container",
        account_name=images_storage.name,
        resource_group_name=resource_group.name,
        container_name="images",
        public_access=azure_native.storage.PublicAccess.BLOB,
    )

    azure_native.storage.BlobServiceProperties(
        f"{project_name}-images-cors",
        account_name=images_storage.name,
        resource_group_name=resource_group.name,
        blob_services_name="default",
        cors=azure_native.storage.CorsRulesArgs(
            cors_rules=[
                azure_native.storage.CorsRuleArgs(
                    allowed_origins=["*"],
                    allowed_methods=["GET", "PUT", "HEAD"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"],
                    max_age_in_seconds=3000,
                )
            ]
        ),
    )

    cosmos_account = azure_native.cosmosdb.DatabaseAccount(
        f"{project_name}-cosmos",
        account_name=cosmos_account_name(
            f"{project_name}cos", environment, stack, cosmos_account_suffix),
        resource_group_name=resource_group.name,
        location=resource_group.location,
        kind=azure_native.cosmosdb.DatabaseAccountKind.GLOBAL_DOCUMENT_DB,
        database_account_offer_type="Standard",
        capabilities=[
            azure_native.cosmosdb.CapabilityArgs(name="EnableServerless"),
        ],
        locations=[azure_native.cosmosdb.LocationArgs(
            location_name=resource_group.location, failover_priority=0)],
        consistency_policy=azure_native.cosmosdb.ConsistencyPolicyArgs(
            default_consistency_level="Session"),
        tags=base_tags,
    )

    cosmos_db = azure_native.cosmosdb.SqlResourceSqlDatabase(
        "simple-sns",
        resource_group_name=resource_group.name,
        account_name=cosmos_account.name,
        resource=azure_native.cosmosdb.SqlDatabaseResourceArgs(
            id="simple-sns"),
    )

    cosmos_container = azure_native.cosmosdb.SqlResourceSqlContainer(
        "items",
        resource_group_name=resource_group.name,
        account_name=cosmos_account.name,
        database_name=cosmos_db.name,
        resource=azure_native.cosmosdb.SqlContainerResourceArgs(
            id="items",
            partition_key=azure_native.cosmosdb.ContainerPartitionKeyArgs(
                paths=["/pk"],
                kind="Hash",
            ),
        ),
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

    return {
        "images_storage": images_storage,
        "images_container": images_container,
        "cosmos_account": cosmos_account,
        "cosmos_db": cosmos_db,
        "cosmos_container": cosmos_container,
        "registry": registry,
    }
