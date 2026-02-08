output "s3_bucket_name" {
  value = module.static_site.s3_bucket_name
}

output "s3_bucket_website_endpoint" {
  value = module.static_site.s3_bucket_website_endpoint
}

output "cloudfront_distribution_id" {
  value = module.static_site.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  value = module.static_site.cloudfront_domain_name
}

output "website_url" {
  value = module.static_site.website_url
}

output "acm_certificate_validation_records" {
  value = module.static_site.acm_certificate_validation_records
}

output "custom_domain" {
  value = module.static_site.custom_domain
}

output "acm_certificate_arn" {
  value = module.static_site.acm_certificate_arn
}
