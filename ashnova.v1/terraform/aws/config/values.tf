locals {
  aws_region  = "ap-northeast-1"
  aws_profile = "satoshi"

  merged_project_name                    = "ashnova-static-site"
  merged_domain_name                     = ""
  merged_use_custom_domain_in_cloudfront = false
  merged_enable_cloudfront               = true
  merged_tags = {
    Project     = "ashnova"
    ManagedBy   = "OpenTofu"
    Environment = "production"
  }

  merged_enable_access_analyzer                    = false
  simple_sns_domain                                = "sns.aws.ashnova.jp"
  merged_simple_sns_project_name                   = "simple-sns"
  merged_simple_sns_web_callback_url               = "https://${local.simple_sns_domain}/"
  merged_simple_sns_web_logout_url                 = "https://${local.simple_sns_domain}/"
  merged_simple_sns_web_origin                     = "https://${local.simple_sns_domain}"
  merged_simple_sns_cognito_domain_prefix          = "simple-sns-2026-kr070001"
  merged_simple_sns_api_execution_arn_override     = "arn:aws:execute-api:ap-northeast-1:278280499340:8fa5q1pxkl"
  merged_simple_sns_cloudfront_source_arn_override = "arn:aws:cloudfront::278280499340:distribution/E17ZFSUVHSJDWV"

  simple_sns_project_name          = "simple-sns"
  simple_sns_web_callback_url      = "https://${local.simple_sns_domain}/"
  simple_sns_web_logout_url        = "https://${local.simple_sns_domain}/"
  simple_sns_cognito_domain_prefix = "simple-sns-2026-kr070001"
  simple_sns_tags = {
    Application = "simple-sns"
    Environment = "production"
  }
}

output "aws_region" {
  value = local.aws_region
}

output "aws_profile" {
  value = local.aws_profile
}

output "merged_project_name" {
  value = local.merged_project_name
}

output "merged_domain_name" {
  value = local.merged_domain_name
}

output "merged_use_custom_domain_in_cloudfront" {
  value = local.merged_use_custom_domain_in_cloudfront
}

output "merged_enable_cloudfront" {
  value = local.merged_enable_cloudfront
}

output "merged_tags" {
  value = local.merged_tags
}

output "merged_enable_access_analyzer" {
  value = local.merged_enable_access_analyzer
}

output "merged_simple_sns_project_name" {
  value = local.merged_simple_sns_project_name
}

output "merged_simple_sns_web_callback_url" {
  value = local.merged_simple_sns_web_callback_url
}

output "merged_simple_sns_web_logout_url" {
  value = local.merged_simple_sns_web_logout_url
}

output "merged_simple_sns_web_origin" {
  value = local.merged_simple_sns_web_origin
}

output "merged_simple_sns_cognito_domain_prefix" {
  value = local.merged_simple_sns_cognito_domain_prefix
}

output "merged_simple_sns_api_execution_arn_override" {
  value = local.merged_simple_sns_api_execution_arn_override
}

output "merged_simple_sns_cloudfront_source_arn_override" {
  value = local.merged_simple_sns_cloudfront_source_arn_override
}

output "simple_sns_project_name" {
  value = local.simple_sns_project_name
}

output "simple_sns_web_callback_url" {
  value = local.simple_sns_web_callback_url
}

output "simple_sns_web_logout_url" {
  value = local.simple_sns_web_logout_url
}

output "simple_sns_cognito_domain_prefix" {
  value = local.simple_sns_cognito_domain_prefix
}

output "simple_sns_tags" {
  value = local.simple_sns_tags
}
