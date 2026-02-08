output "api_url" {
  value = module.serverless_app.api_url
}

output "cognito_user_pool_id" {
  value = module.serverless_app.cognito_user_pool_id
}

output "cognito_client_id" {
  value = module.serverless_app.cognito_client_id
}

output "cognito_domain" {
  value = module.serverless_app.cognito_domain
}

output "dynamodb_table_name" {
  value = module.serverless_app.dynamodb_table_name
}

output "images_bucket_name" {
  value = module.serverless_app.images_bucket_name
}

output "frontend_bucket_name" {
  value = module.serverless_app.frontend_bucket_name
}

output "frontend_website_endpoint" {
  value = module.serverless_app.frontend_website_endpoint
}

output "cloudfront_distribution_id" {
  value = module.serverless_app.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  value = module.serverless_app.cloudfront_domain_name
}

output "lambda_layer_arn" {
  value = module.serverless_app.lambda_layer_arn
}

output "lambda_layer_version" {
  value = module.serverless_app.lambda_layer_version
}

output "static_site_s3_bucket_name" {
  value = module.serverless_app.static_site_s3_bucket_name
}

output "static_site_s3_bucket_website_endpoint" {
  value = module.serverless_app.static_site_s3_bucket_website_endpoint
}

output "static_site_cloudfront_distribution_id" {
  value = module.serverless_app.static_site_cloudfront_distribution_id
}

output "static_site_cloudfront_domain_name" {
  value = module.serverless_app.static_site_cloudfront_domain_name
}

output "static_site_website_url" {
  value = module.serverless_app.static_site_website_url
}

output "static_site_acm_certificate_validation_records" {
  value = module.serverless_app.static_site_acm_certificate_validation_records
}

output "static_site_custom_domain" {
  value = module.serverless_app.static_site_custom_domain
}

output "static_site_acm_certificate_arn" {
  value = module.serverless_app.static_site_acm_certificate_arn
}
