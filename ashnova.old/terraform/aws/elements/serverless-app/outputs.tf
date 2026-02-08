output "serverless_app_api_url" {
  description = "Serverless App API endpoint base URL"
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "serverless_app_cognito_user_pool_id" {
  description = "Serverless App Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "serverless_app_cognito_client_id" {
  description = "Serverless App Cognito Client ID"
  value       = aws_cognito_user_pool_client.main.id
}

output "serverless_app_cognito_domain" {
  description = "Serverless App Cognito Domain"
  value       = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "serverless_app_dynamodb_table_name" {
  description = "Serverless App DynamoDB Table Name"
  value       = aws_dynamodb_table.posts.name
}

output "serverless_app_images_bucket_name" {
  description = "Serverless App Images S3 Bucket Name"
  value       = aws_s3_bucket.serverless_app_images.bucket
}

output "serverless_app_frontend_bucket_name" {
  description = "Serverless App Frontend S3 bucket name"
  value       = aws_s3_bucket.serverless_app_frontend.id
}

output "serverless_app_frontend_website_endpoint" {
  description = "Serverless App Frontend S3 website endpoint"
  value       = aws_s3_bucket_website_configuration.serverless_app_frontend.website_endpoint
}

output "serverless_app_cloudfront_distribution_id" {
  description = "Serverless App CloudFront Distribution ID"
  value       = aws_cloudfront_distribution.serverless_app_frontend.id
}

output "serverless_app_cloudfront_domain_name" {
  description = "Serverless App CloudFront Distribution Domain Name"
  value       = aws_cloudfront_distribution.serverless_app_frontend.domain_name
}

output "serverless_app_lambda_layer_arn" {
  description = "Serverless App Lambda Layer ARN"
  value       = aws_lambda_layer_version.nodejs_dependencies.arn
}

output "serverless_app_lambda_layer_version" {
  description = "Serverless App Lambda Layer Version"
  value       = aws_lambda_layer_version.nodejs_dependencies.version
}
