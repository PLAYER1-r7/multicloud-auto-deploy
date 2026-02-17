terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region  = local.aws_region
  profile = local.aws_profile
}

# CloudFront requires ACM certificate in us-east-1
provider "aws" {
  alias   = "us-east-1"
  region  = "us-east-1"
  profile = local.aws_profile
}

module "serverless_app" {
  source = "../../modules/serverless-app"

  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1
  }

  aws_region                                        = local.aws_region
  project_name                                      = local.project_name
  web_callback_url                                  = local.web_callback_url
  web_logout_url                                    = local.web_logout_url
  web_origin                                        = local.web_origin
  cognito_domain_prefix                             = local.cognito_domain_prefix
  serverless_app_api_execution_arn_override         = local.serverless_app_api_execution_arn_override
  serverless_app_cloudfront_source_arn_override     = local.serverless_app_cloudfront_source_arn_override
  serverless_app_cloudfront_aliases                 = local.serverless_app_cloudfront_aliases
  serverless_app_cloudfront_web_acl_id              = local.serverless_app_cloudfront_web_acl_id
  enable_serverless_app_cloudfront_security_headers = local.enable_serverless_app_cloudfront_security_headers
  enable_serverless_app_cloudfront_logging          = local.enable_serverless_app_cloudfront_logging
  serverless_app_frontend_bucket_name               = local.serverless_app_frontend_bucket_name
  serverless_app_primary_domain                     = local.serverless_app_primary_domain
  serverless_app_source_dir                         = local.serverless_app_source_dir
  serverless_app_dist_dir                           = local.serverless_app_dist_dir
  serverless_app_tags                               = local.serverless_app_tags

  static_site_project_name                    = local.static_site_project_name
  static_site_domain_name                     = local.static_site_domain_name
  static_site_use_custom_domain_in_cloudfront = local.static_site_use_custom_domain_in_cloudfront
  static_site_enable_cloudfront               = local.static_site_enable_cloudfront
  static_site_enable_static_site              = local.static_site_enable_static_site
  static_site_tags                            = local.static_site_tags
  static_site_enable_access_analyzer          = local.static_site_enable_access_analyzer
}
