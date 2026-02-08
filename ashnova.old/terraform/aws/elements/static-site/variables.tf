variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ashnova-static-site"
}

variable "domain_name" {
  description = "Custom domain name (e.g., www.aws.ashnova.jp) - 証明書検証後に設定してください"
  type        = string
  default     = ""
}

variable "use_custom_domain_in_cloudfront" {
  description = "Apply custom domain to CloudFront (証明書が検証済みの場合のみtrueにしてください)"
  type        = bool
  default     = false
}

variable "enable_cloudfront" {
  description = "Enable CloudFront CDN"
  type        = bool
  default     = true
}

variable "enable_static_site" {
  description = "Enable static site (S3 + optional CloudFront)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "ashnova"
    ManagedBy   = "OpenTofu"
    Environment = "production"
  }
}

variable "enable_access_analyzer" {
  description = "Enable IAM Access Analyzer (account-level)"
  type        = bool
  default     = false
}
