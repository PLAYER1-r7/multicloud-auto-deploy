terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.us-east-1]
    }
  }
}

# Locals for Serverless App
locals {
  serverless_app_tags = var.serverless_app_tags != null ? var.serverless_app_tags : {
    Application = var.serverless_app_project_name
    Environment = "production"
  }

  repo_root               = "${path.root}/../../../../"
  serverless_app_dir      = var.serverless_app_source_dir != "" ? var.serverless_app_source_dir : "${local.repo_root}/aws/simple-sns"
  serverless_app_dist_dir = var.serverless_app_dist_dir != "" ? var.serverless_app_dist_dir : "${local.serverless_app_dir}/dist"
  terraform_cache_dir     = "${path.root}/.terraform"

  serverless_app_frontend_bucket_name = var.serverless_app_frontend_bucket_name != "" ? var.serverless_app_frontend_bucket_name : "${var.serverless_app_project_name}-frontend"
  serverless_app_primary_domain       = var.serverless_app_primary_domain != "" ? var.serverless_app_primary_domain : (length(var.serverless_app_cloudfront_aliases) > 0 ? var.serverless_app_cloudfront_aliases[0] : "")

  serverless_app_api_execution_arn     = var.serverless_app_api_execution_arn_override != "" ? var.serverless_app_api_execution_arn_override : aws_api_gateway_rest_api.main.execution_arn
  serverless_app_cloudfront_source_arn = var.serverless_app_cloudfront_source_arn_override != "" ? var.serverless_app_cloudfront_source_arn_override : aws_cloudfront_distribution.serverless_app_frontend.arn
}
