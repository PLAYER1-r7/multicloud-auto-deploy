terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.us-east-1]
    }
  }
}

module "serverless_app" {
  source = "../../elements/serverless-app"

  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1
  }

  aws_region                                        = var.aws_region
  serverless_app_project_name                       = var.project_name
  serverless_app_web_callback_url                   = var.web_callback_url
  serverless_app_web_logout_url                     = var.web_logout_url
  serverless_app_web_origin                         = var.web_origin
  serverless_app_cognito_domain_prefix              = var.cognito_domain_prefix
  serverless_app_api_execution_arn_override         = var.serverless_app_api_execution_arn_override
  serverless_app_cloudfront_source_arn_override     = var.serverless_app_cloudfront_source_arn_override
  serverless_app_cloudfront_aliases                 = var.serverless_app_cloudfront_aliases
  serverless_app_cloudfront_web_acl_id              = var.serverless_app_cloudfront_web_acl_id
  enable_serverless_app_cloudfront_security_headers = var.enable_serverless_app_cloudfront_security_headers
  enable_serverless_app_cloudfront_logging          = var.enable_serverless_app_cloudfront_logging
  serverless_app_frontend_bucket_name               = var.serverless_app_frontend_bucket_name
  serverless_app_primary_domain                     = var.serverless_app_primary_domain
  serverless_app_source_dir                         = var.serverless_app_source_dir
  serverless_app_dist_dir                           = var.serverless_app_dist_dir
  serverless_app_tags                               = var.serverless_app_tags
}

module "static_site" {
  source = "../../modules/static-site"

  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1
  }

  project_name                    = var.static_site_project_name
  domain_name                     = var.static_site_domain_name
  use_custom_domain_in_cloudfront = var.static_site_use_custom_domain_in_cloudfront
  enable_cloudfront               = var.static_site_enable_cloudfront
  enable_static_site              = var.static_site_enable_static_site
  tags                            = var.static_site_tags
  enable_access_analyzer          = var.static_site_enable_access_analyzer
}
