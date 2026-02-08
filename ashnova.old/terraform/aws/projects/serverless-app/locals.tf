locals {
  default_aws_region  = "ap-northeast-1"
  default_aws_profile = "satoshi"

  default_serverless_app_domain     = "sns.aws.ashnova.jp"
  default_project_name              = "serverless-app"
  default_cognito_domain_prefix     = "serverless-app-2026-kr070001"
  default_serverless_app_source_dir = "${path.root}/../../../../aws/simple-sns"

  default_static_site_project_name                    = "ashnova-static-site"
  default_static_site_domain_name                     = ""
  default_static_site_use_custom_domain_in_cloudfront = false
  default_static_site_enable_cloudfront               = true
  default_static_site_enable_static_site              = true
  default_static_site_enable_access_analyzer          = false
  default_static_site_tags = {
    Project     = "ashnova"
    ManagedBy   = "OpenTofu"
    Environment = "production"
  }

  aws_region  = coalesce(var.aws_region, local.default_aws_region)
  aws_profile = coalesce(var.aws_profile, local.default_aws_profile)

  serverless_app_domain = coalesce(var.serverless_app_domain, local.default_serverless_app_domain)
  project_name          = coalesce(var.project_name, local.default_project_name)

  web_callback_url = coalesce(
    var.web_callback_url,
    "https://${local.serverless_app_domain}/"
  )
  web_logout_url = coalesce(
    var.web_logout_url,
    "https://${local.serverless_app_domain}/"
  )
  web_origin = coalesce(
    var.web_origin,
    "https://${local.serverless_app_domain}"
  )

  cognito_domain_prefix = coalesce(
    var.cognito_domain_prefix,
    local.default_cognito_domain_prefix
  )

  serverless_app_api_execution_arn_override = (
    var.serverless_app_api_execution_arn_override == null || var.serverless_app_api_execution_arn_override == ""
  ) ? "" : var.serverless_app_api_execution_arn_override
  serverless_app_cloudfront_source_arn_override = (
    var.serverless_app_cloudfront_source_arn_override == null || var.serverless_app_cloudfront_source_arn_override == ""
  ) ? "" : var.serverless_app_cloudfront_source_arn_override

  serverless_app_cloudfront_aliases                 = var.serverless_app_cloudfront_aliases != null ? var.serverless_app_cloudfront_aliases : [local.serverless_app_domain]
  serverless_app_cloudfront_web_acl_id              = (var.serverless_app_cloudfront_web_acl_id != null && var.serverless_app_cloudfront_web_acl_id != "") ? var.serverless_app_cloudfront_web_acl_id : ""
  enable_serverless_app_cloudfront_security_headers = var.enable_serverless_app_cloudfront_security_headers != null ? var.enable_serverless_app_cloudfront_security_headers : false
  enable_serverless_app_cloudfront_logging          = var.enable_serverless_app_cloudfront_logging != null ? var.enable_serverless_app_cloudfront_logging : false

  serverless_app_frontend_bucket_name = (var.serverless_app_frontend_bucket_name != null && var.serverless_app_frontend_bucket_name != "") ? var.serverless_app_frontend_bucket_name : ""
  serverless_app_primary_domain       = (var.serverless_app_primary_domain != null && var.serverless_app_primary_domain != "") ? var.serverless_app_primary_domain : local.serverless_app_domain
  serverless_app_source_dir           = (var.serverless_app_source_dir != null && var.serverless_app_source_dir != "") ? var.serverless_app_source_dir : local.default_serverless_app_source_dir
  serverless_app_dist_dir             = (var.serverless_app_dist_dir != null && var.serverless_app_dist_dir != "") ? var.serverless_app_dist_dir : "${local.serverless_app_source_dir}/dist"
  serverless_app_tags = var.serverless_app_tags != null ? var.serverless_app_tags : {
    Application = local.project_name
    Environment = "production"
  }

  static_site_project_name                    = coalesce(var.static_site_project_name, local.default_static_site_project_name)
  static_site_domain_name                     = coalesce(var.static_site_domain_name, local.default_static_site_domain_name)
  static_site_use_custom_domain_in_cloudfront = var.static_site_use_custom_domain_in_cloudfront != null ? var.static_site_use_custom_domain_in_cloudfront : local.default_static_site_use_custom_domain_in_cloudfront
  static_site_enable_cloudfront               = var.static_site_enable_cloudfront != null ? var.static_site_enable_cloudfront : local.default_static_site_enable_cloudfront
  static_site_enable_static_site              = var.static_site_enable_static_site != null ? var.static_site_enable_static_site : local.default_static_site_enable_static_site
  static_site_enable_access_analyzer          = var.static_site_enable_access_analyzer != null ? var.static_site_enable_access_analyzer : local.default_static_site_enable_access_analyzer
  static_site_tags                            = var.static_site_tags != null ? var.static_site_tags : local.default_static_site_tags
}
