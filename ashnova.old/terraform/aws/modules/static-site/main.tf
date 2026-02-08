terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      configuration_aliases = [aws.us-east-1]
    }
  }
}

module "static_site" {
  source = "../../elements/static-site"

  providers = {
    aws           = aws
    aws.us-east-1 = aws.us-east-1
  }

  project_name                    = var.project_name
  domain_name                     = var.domain_name
  use_custom_domain_in_cloudfront = var.use_custom_domain_in_cloudfront
  enable_cloudfront               = var.enable_cloudfront
  enable_static_site              = var.enable_static_site
  tags                            = var.tags
  enable_access_analyzer          = var.enable_access_analyzer
}
