terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.us-east-1]
    }
  }
}

locals {
  enable_cloudfront = var.enable_static_site && var.enable_cloudfront
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}
