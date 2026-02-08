variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "ap-northeast-1" # Tokyo
}

# Serverless App specific variables
variable "serverless_app_project_name" {
  description = "Project name for Serverless App"
  type        = string
  default     = "serverless-app"
}

variable "serverless_app_web_callback_url" {
  description = "Web callback URL for Serverless App Cognito"
  type        = string
  default     = "https://sns.aws.ashnova.jp/"
}

variable "serverless_app_web_logout_url" {
  description = "Web logout URL for Serverless App Cognito"
  type        = string
  default     = "https://sns.aws.ashnova.jp/"
}

variable "serverless_app_web_origin" {
  description = "Web origin for Serverless App (used in CORS for uploads)"
  type        = string
  default     = "https://sns.aws.ashnova.jp"
}

variable "serverless_app_cognito_domain_prefix" {
  description = "Cognito domain prefix for Serverless App"
  type        = string
  default     = "serverless-app-2026-kr070001"
}

variable "serverless_app_api_execution_arn_override" {
  description = "Override API Gateway execution ARN for Lambda permissions"
  type        = string
  default     = ""
}

variable "serverless_app_cloudfront_source_arn_override" {
  description = "Override CloudFront distribution ARN for Serverless App bucket policies"
  type        = string
  default     = ""
}

variable "serverless_app_cloudfront_aliases" {
  description = "CloudFront aliases for Serverless App distribution"
  type        = list(string)
  default     = ["sns.aws.ashnova.jp"]
}

variable "serverless_app_cloudfront_web_acl_id" {
  description = "CloudFront Web ACL ID (optional)"
  type        = string
  default     = ""
}

variable "enable_serverless_app_cloudfront_security_headers" {
  description = "Enable CloudFront security headers policy for Serverless App (requires non-Free tier)"
  type        = bool
  default     = false
}

variable "enable_serverless_app_cloudfront_logging" {
  description = "Enable CloudFront access logging for Serverless App (requires non-Free tier)"
  type        = bool
  default     = false
}

variable "serverless_app_frontend_bucket_name" {
  description = "Frontend S3 bucket name override"
  type        = string
  default     = ""
}

variable "serverless_app_primary_domain" {
  description = "Primary domain for ACM certificate"
  type        = string
  default     = ""
}

variable "serverless_app_source_dir" {
  description = "Source directory for Lambda code and package.json"
  type        = string
  default     = ""
}

variable "serverless_app_dist_dir" {
  description = "Built Lambda artifact directory"
  type        = string
  default     = ""
}

variable "serverless_app_tags" {
  description = "Tags applied to Serverless App resources"
  type        = map(string)
  default = {
    Application = "serverless-app"
    Environment = "production"
  }
}
