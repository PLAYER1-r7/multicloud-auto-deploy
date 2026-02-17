import pulumi
import pulumi_gcp as gcp
from config import project
from storage import create_storage_resources
from compute import create_compute_resources

if not project:
    raise ValueError("gcp:project is required in config or gcp:project")

# 1. Enable Required Services
required_services = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "firestore.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
]

service_apis = [
    gcp.projects.Service(
        f"api-{service.replace('.', '-')}",
        service=service,
        project=project,
        disable_on_destroy=False,
    )
    for service in required_services
]

service_api_opts = pulumi.ResourceOptions(depends_on=service_apis)

# 2. Storage & Database
storage = create_storage_resources(service_api_opts)

# 3. Compute (Cloud Run)
compute = create_compute_resources(storage, service_api_opts)

# 4. Exports
api_url = (
    compute["service"].statuses.apply(
        lambda statuses: statuses[0].url if statuses else None)
    if compute["service"]
    else None
)

pulumi.export("api_url", api_url)
pulumi.export("images_bucket", storage["bucket"].name)
pulumi.export("api_image_name", compute["api_image_name"])
pulumi.export("api_repository", storage["repository"].repository_id)
