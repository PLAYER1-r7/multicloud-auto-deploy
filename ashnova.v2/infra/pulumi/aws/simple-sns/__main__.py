import pulumi
from build import build_lambda_package
from storage import create_storage_resources
from auth import create_auth_resources
from compute import create_compute_resources

# 1. Build Lambda
zip_path = build_lambda_package()

# 2. Storage
storage = create_storage_resources()

# 3. Auth
auth = create_auth_resources()

# 4. Compute (Lambda + API Gateway)
compute = create_compute_resources(storage, auth, zip_path)

# 5. Exports
pulumi.export("api_url", compute["api"].api_endpoint)
pulumi.export("cognito_user_pool_id", auth["user_pool"].id)
pulumi.export("cognito_client_id", auth["user_pool_client"].id)
pulumi.export("cognito_hosted_ui_domain", auth["hosted_ui_domain"].domain)

pulumi.export("cognito_user_pool_id_gcp", auth["user_pool_gcp"].id)
pulumi.export("cognito_client_id_gcp", auth["user_pool_client_gcp"].id)
pulumi.export("cognito_hosted_ui_domain_gcp",
              auth["hosted_ui_domain_gcp"].domain)

pulumi.export("posts_table_name", storage["posts_table"].name)
pulumi.export("images_bucket_name", storage["images_bucket"].bucket)
