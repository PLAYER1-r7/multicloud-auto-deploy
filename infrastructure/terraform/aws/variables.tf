variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "environment" {
  description = "Environment (staging, production)"
  type        = string
  default     = "staging"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "multicloud-auto-deploy"
}

variable "domain_name" {
  description = "Custom domain name (optional)"
  type        = string
  default     = ""
}
