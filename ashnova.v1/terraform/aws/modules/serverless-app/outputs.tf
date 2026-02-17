output "api_url" {
  value = module.serverless_app.serverless_app_api_url
}

output "cognito_user_pool_id" {
  value = module.serverless_app.serverless_app_cognito_user_pool_id
}

output "cognito_client_id" {
  value = module.serverless_app.serverless_app_cognito_client_id
}

output "cognito_domain" {
  value = module.serverless_app.serverless_app_cognito_domain
}

output "dynamodb_table_name" {
  value = module.serverless_app.serverless_app_dynamodb_table_name
}

output "images_bucket_name" {
  value = module.serverless_app.serverless_app_images_bucket_name
}

output "frontend_bucket_name" {
  value = module.serverless_app.serverless_app_frontend_bucket_name
}

output "frontend_website_endpoint" {
  value = module.serverless_app.serverless_app_frontend_website_endpoint
}

output "cloudfront_distribution_id" {
  value = module.serverless_app.serverless_app_cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  value = module.serverless_app.serverless_app_cloudfront_domain_name
}

output "lambda_layer_arn" {
  value = module.serverless_app.serverless_app_lambda_layer_arn
}

output "lambda_layer_version" {
  value = module.serverless_app.serverless_app_lambda_layer_version
}

output "static_site_s3_bucket_name" {
  value = module.static_site.s3_bucket_name
}

output "static_site_s3_bucket_website_endpoint" {
  value = module.static_site.s3_bucket_website_endpoint
}

output "static_site_cloudfront_distribution_id" {
  value = module.static_site.cloudfront_distribution_id
}

output "static_site_cloudfront_domain_name" {
  value = module.static_site.cloudfront_domain_name
}

output "static_site_website_url" {
  value = module.static_site.website_url
}

output "static_site_acm_certificate_validation_records" {
  value = module.static_site.acm_certificate_validation_records
}

output "static_site_custom_domain" {
  value = module.static_site.custom_domain
}

output "static_site_acm_certificate_arn" {
  value = module.static_site.acm_certificate_arn
}
