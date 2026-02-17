terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
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
  region  = var.aws_region
  profile = "satoshi"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "simple-sns"
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

variable "cognito_domain_prefix" {
  description = "Cognito domain prefix"
  type        = string
  default     = "simple-sns-2026-kr070001"
}

locals {
  tags = {
    Application = "simple-sns"
    Environment = "production"
  }
}
