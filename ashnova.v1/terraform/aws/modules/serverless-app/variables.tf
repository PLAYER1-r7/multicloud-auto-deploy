variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}


variable "project_name" {
  description = "Project name"
  type        = string
  default     = "serverless-app"
}

variable "web_callback_url" {
  description = "Web callback URL"
  type        = string
  default     = "https://sns.adawak.net/"
}

variable "web_logout_url" {
  description = "Web logout URL"
  type        = string
  default     = "https://sns.adawak.net/"
}

variable "web_origin" {
  description = "Web origin (used for CORS)"
  type        = string
  default     = "https://sns.adawak.net"
}

variable "cognito_domain_prefix" {
  description = "Cognito domain prefix"
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
  default     = null
}

variable "static_site_project_name" {
  description = "Static site project name"
  type        = string
  default     = null
}

variable "static_site_domain_name" {
  description = "Static site custom domain"
  type        = string
  default     = null
}

variable "static_site_use_custom_domain_in_cloudfront" {
  description = "Apply custom domain to static site CloudFront"
  type        = bool
  default     = null
}

variable "static_site_enable_cloudfront" {
  description = "Enable static site CloudFront CDN"
  type        = bool
  default     = null
}

variable "static_site_enable_static_site" {
  description = "Enable static site resources"
  type        = bool
  default     = null
}

variable "static_site_tags" {
  description = "Tags applied to static site resources"
  type        = map(string)
  default     = null
}

variable "static_site_enable_access_analyzer" {
  description = "Enable IAM Access Analyzer for static site"
  type        = bool
  default     = null
}
