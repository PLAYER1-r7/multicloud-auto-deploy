import pulumi
import pulumi_gcp as gcp
from config import (
    project_name,
    environment,
    stack,
    suffix,
    region,
    project,
    client_id,
    api_image_override,
    deploy_service,
    resource_name,
    auth_provider,
    cognito_user_pool_id,
    cognito_client_id
)


def create_compute_resources(storage_resources: dict, opts: pulumi.ResourceOptions) -> dict:
    """Creates Compute (Cloud Run), Service Accounts, and IAM bindings."""

    repository = storage_resources["repository"]
    bucket = storage_resources["bucket"]

    # 1. Service Account for API
    service_account = gcp.serviceaccount.Account(
        "api-sa",
        account_id=resource_name(project_name, environment,
                                 stack, f"api-sa-{suffix}")[:28],
        display_name="Simple SNS API",
        opts=opts,
    )

    # 2. Determine Image Name
    api_image_name = (
        pulumi.Output.from_input(api_image_override)
        if api_image_override
        else pulumi.Output.concat(
            region,
            "-docker.pkg.dev/",
            project,
            "/",
            repository.repository_id,
            "/simple-sns-api:latest",
        )
    )

    # 3. Cloud Run Service
    service = None
    if deploy_service or (deploy_service is None):  # Default to true if None
        service = gcp.cloudrun.Service(
            "api-service",
            location=region,
            template=gcp.cloudrun.ServiceTemplateArgs(
                metadata=gcp.cloudrun.ServiceTemplateMetadataArgs(
                    annotations={
                        "autoscaling.knative.dev/minScale": "0",
                        "autoscaling.knative.dev/maxScale": "1",
                    }
                ),
                spec=gcp.cloudrun.ServiceTemplateSpecArgs(
                    service_account_name=service_account.email,
                    containers=[gcp.cloudrun.ServiceTemplateSpecContainerArgs(
                        image=api_image_name,
                        envs=[
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="CLOUD_PROVIDER", value="gcp"),
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="AUTH_PROVIDER", value=auth_provider),
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="COGNITO_USER_POOL_ID", value=cognito_user_pool_id),
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="COGNITO_CLIENT_ID", value=cognito_client_id),
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="GCP_PROJECT_ID", value=project),
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="GCP_CLIENT_ID", value=client_id),
                            gcp.cloudrun.ServiceTemplateSpecContainerEnvArgs(
                                name="GCP_STORAGE_BUCKET", value=bucket.name),
                        ],
                    )],
                ),
            ),
            traffics=[gcp.cloudrun.ServiceTrafficArgs(
                percent=100, latest_revision=True)],
            opts=opts,
        )

        # Allow public access
        gcp.cloudrun.IamMember(
            "api-invoker",
            service=service.name,
            location=service.location,
            role="roles/run.invoker",
            member="allUsers",
        )

    # 4. IAM Bindings
    # Firestore User
    gcp.projects.IAMMember(
        "firestore-user",
        project=project,
        role="roles/datastore.user",
        member=service_account.email.apply(
            lambda email: f"serviceAccount:{email}"),
    )

    # Storage Admin (for uploads)
    gcp.projects.IAMMember(
        "storage-admin",
        project=project,
        role="roles/storage.objectAdmin",
        member=service_account.email.apply(
            lambda email: f"serviceAccount:{email}"),
    )

    # Service Account Token Creator (if needed for signing blobs - though we moved to public,
    # some legacy code might check permissions, or we might keep it usage agnostic)
    gcp.serviceaccount.IAMMember(
        "signer",
        service_account_id=service_account.name,
        role="roles/iam.serviceAccountTokenCreator",
        member=service_account.email.apply(
            lambda email: f"serviceAccount:{email}"),
    )

    return {
        "service": service,
        "service_account": service_account,
        "api_image_name": api_image_name
    }
