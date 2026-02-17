import pulumi
import pulumi_gcp as gcp
from config import (
    project_name,
    environment,
    stack,
    suffix,
    region,
    project,
    custom_tags,
    resource_name
)


def create_storage_resources(opts: pulumi.ResourceOptions) -> dict:
    """Creates Storage (Buckets), Database (Firestore), and Artifact Registry."""

    # 1. Artifact Registry
    repository = gcp.artifactregistry.Repository(
        "api-repo",
        location=region,
        repository_id=resource_name(
            project_name, environment, stack, f"api-{suffix}"),
        format="DOCKER",
        opts=opts,
    )

    # 2. GCS Bucket for Images
    bucket = gcp.storage.Bucket(
        "images-bucket",
        name=resource_name(project_name, environment,
                           stack, f"images-{suffix}"),
        location=region,
        uniform_bucket_level_access=True,
        force_destroy=True,
        cors=[gcp.storage.BucketCorArgs(
            origins=["*"],
            methods=["GET", "PUT", "HEAD"],
            response_headers=["ETag"],
            max_age_seconds=3000,
        )],
        labels=custom_tags,
        opts=opts,
    )

    # Make bucket public readable (since we switched to public URLs)
    gcp.storage.BucketIAMMember(
        "images-public-read",
        bucket=bucket.name,
        role="roles/storage.objectViewer",
        member="allUsers",
        opts=opts,
    )

    # 3. Firestore
    # Firestore Database resource
    # Note: protect=True is often good for databases, but for this demo/refactor we might leave it or keep strict.
    firestore_db = gcp.firestore.Database(
        "firestore-db",
        app_engine_integration_mode="DISABLED",
        concurrency_mode="PESSIMISTIC",
        database_edition="STANDARD",
        delete_protection_state="DELETE_PROTECTION_DISABLED",
        name="(default)",
        location_id=region,
        project=project,
        type="FIRESTORE_NATIVE",
        opts=pulumi.ResourceOptions(protect=True),
    )

    return {
        "repository": repository,
        "bucket": bucket,
        "firestore_db": firestore_db,
    }
