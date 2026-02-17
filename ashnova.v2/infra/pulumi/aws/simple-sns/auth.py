import pulumi_aws as aws
from config import (
    project_name,
    base_tags,
    hosted_ui_callback_url,
    hosted_ui_callback_debug_url,
    hosted_ui_logout_url,
    additional_callback_urls,
    additional_logout_urls
)


def create_auth_resources():
    user_pool = aws.cognito.UserPool(
        f"{project_name}-users",
        name=f"{project_name}-users",
        auto_verified_attributes=["email"],
        username_attributes=["email"],
        tags=base_tags,
    )

    user_pool_client = aws.cognito.UserPoolClient(
        f"{project_name}-client",
        name=f"{project_name}-client",
        user_pool_id=user_pool.id,
        generate_secret=False,
        allowed_oauth_flows_user_pool_client=True,
        allowed_oauth_flows=["implicit"],
        allowed_oauth_scopes=["openid", "email", "profile"],
        supported_identity_providers=["COGNITO"],
        callback_urls=[hosted_ui_callback_url,
                       hosted_ui_callback_debug_url] + additional_callback_urls,
        logout_urls=[hosted_ui_logout_url] + additional_logout_urls,
        explicit_auth_flows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_USER_SRP_AUTH",
        ],
    )

    hosted_ui_domain = aws.cognito.UserPoolDomain(
        f"{project_name}-domain",
        domain="sns-ashnova-dev",
        user_pool_id=user_pool.id,
    )

    # --- GCP Dedicated Pool ---
    user_pool_gcp = aws.cognito.UserPool(
        f"{project_name}-users-gcp",
        name=f"{project_name}-users-gcp",
        auto_verified_attributes=["email"],
        username_attributes=["email"],
        tags=base_tags,
    )

    user_pool_client_gcp = aws.cognito.UserPoolClient(
        f"{project_name}-client-gcp",
        name=f"{project_name}-client-gcp",
        user_pool_id=user_pool_gcp.id,
        generate_secret=False,
        allowed_oauth_flows_user_pool_client=True,
        allowed_oauth_flows=["implicit"],
        allowed_oauth_scopes=["openid", "email", "profile"],
        supported_identity_providers=["COGNITO"],
        # Allow all additional URLs (which contains GCP URL)
        callback_urls=additional_callback_urls,
        logout_urls=additional_logout_urls,
        explicit_auth_flows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH",
            "ALLOW_USER_SRP_AUTH",
        ],
    )

    hosted_ui_domain_gcp = aws.cognito.UserPoolDomain(
        f"{project_name}-domain-gcp",
        domain="sns-ashnova-gcp-dev",
        user_pool_id=user_pool_gcp.id,
    )

    return {
        "user_pool": user_pool,
        "user_pool_client": user_pool_client,
        "hosted_ui_domain": hosted_ui_domain,
        "user_pool_gcp": user_pool_gcp,
        "user_pool_client_gcp": user_pool_client_gcp,
        "hosted_ui_domain_gcp": hosted_ui_domain_gcp
    }
