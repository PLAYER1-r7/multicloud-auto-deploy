import pulumi
import pulumi_aws as aws

config = pulumi.Config()
project_name = config.get("project_name") or "simple-sns"
custom_tags = config.get_object("tags") or {}

region = aws.config.region or "ap-northeast-1"
hosted_ui_callback_url = config.get("hosted_ui_callback_url") or (
    "https://es3pj6sv44.execute-api.ap-northeast-1.amazonaws.com/prod/"
)
hosted_ui_callback_debug_url = f"{hosted_ui_callback_url}?debug=1"
hosted_ui_logout_url = config.get(
    "hosted_ui_logout_url") or hosted_ui_callback_url

additional_callback_urls = (config.get(
    "additional_callback_urls") or "").split(",")
additional_callback_urls = [url.strip()
                            for url in additional_callback_urls if url.strip()]
additional_logout_urls = (config.get(
    "additional_logout_urls") or "").split(",")
additional_logout_urls = [url.strip()
                          for url in additional_logout_urls if url.strip()]

base_tags = {
    "Project": project_name,
    "ManagedBy": "Pulumi",
    **custom_tags,
}
