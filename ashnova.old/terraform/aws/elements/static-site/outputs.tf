output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = var.enable_static_site ? aws_s3_bucket.static_site[0].id : null
}

output "s3_bucket_website_endpoint" {
  description = "S3 bucket website endpoint"
  value       = var.enable_static_site ? aws_s3_bucket_website_configuration.static_site[0].website_endpoint : null
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = local.enable_cloudfront ? aws_cloudfront_distribution.static_site[0].id : null
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = local.enable_cloudfront ? aws_cloudfront_distribution.static_site[0].domain_name : null
}

output "website_url" {
  description = "Website URL"
  value       = var.enable_static_site ? (local.enable_cloudfront ? (var.domain_name != "" && var.use_custom_domain_in_cloudfront ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.static_site[0].domain_name}") : "http://${aws_s3_bucket_website_configuration.static_site[0].website_endpoint}") : null
}

output "acm_certificate_validation_records" {
  description = "DNS records for ACM certificate validation"
  value = local.enable_cloudfront && var.domain_name != "" ? {
    for dvo in aws_acm_certificate.cloudfront_cert[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  } : {}
}

output "custom_domain" {
  description = "Custom domain name"
  value       = var.enable_static_site ? var.domain_name : null
}

output "acm_certificate_arn" {
  description = "ACM certificate ARN"
  value       = local.enable_cloudfront && var.domain_name != "" ? aws_acm_certificate.cloudfront_cert[0].arn : null
}
