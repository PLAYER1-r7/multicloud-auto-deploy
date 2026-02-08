# API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name  = "${var.serverless_app_project_name}-api"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.serverless_app_tags
}

# API Gateway Authorizer
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "CognitoAuthorizer"
  rest_api_id     = aws_api_gateway_rest_api.main.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [aws_cognito_user_pool.main.arn]
  identity_source = "method.request.header.Authorization"
}

# API Gateway Resources
resource "aws_api_gateway_resource" "posts" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "posts"
}

resource "aws_api_gateway_resource" "profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "profile"
}

# GET /profile
resource "aws_api_gateway_method" "get_profile" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.profile.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_profile" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.profile.id
  http_method             = aws_api_gateway_method.get_profile.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.profile.invoke_arn
}

resource "aws_api_gateway_method_response" "get_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.get_profile.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# POST /profile
resource "aws_api_gateway_method" "post_profile" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.profile.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "post_profile" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.profile.id
  http_method             = aws_api_gateway_method.post_profile.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.profile.invoke_arn
}

resource "aws_api_gateway_method_response" "post_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.post_profile.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# OPTIONS /profile (CORS)
resource "aws_api_gateway_method" "options_profile" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.profile.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.options_profile.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.options_profile.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "options_profile" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.profile.id
  http_method = aws_api_gateway_method.options_profile.http_method
  status_code = aws_api_gateway_method_response.options_profile.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.options_profile]
}

# POST /posts
resource "aws_api_gateway_method" "create_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.posts.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "create_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.posts.id
  http_method             = aws_api_gateway_method.create_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.create_post.invoke_arn
}

resource "aws_api_gateway_method_response" "create_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.posts.id
  http_method = aws_api_gateway_method.create_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# OPTIONS /posts (CORS)
resource "aws_api_gateway_method" "options_posts" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.posts.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_posts" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.posts.id
  http_method = aws_api_gateway_method.options_posts.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_posts" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.posts.id
  http_method = aws_api_gateway_method.options_posts.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "options_posts" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.posts.id
  http_method = aws_api_gateway_method.options_posts.http_method
  status_code = aws_api_gateway_method_response.options_posts.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.options_posts]
}

# OPTIONS /upload-urls (CORS)
resource "aws_api_gateway_method" "options_upload_urls" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload_urls.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_upload_urls" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload_urls.id
  http_method = aws_api_gateway_method.options_upload_urls.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_upload_urls" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload_urls.id
  http_method = aws_api_gateway_method.options_upload_urls.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "options_upload_urls" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload_urls.id
  http_method = aws_api_gateway_method.options_upload_urls.http_method
  status_code = aws_api_gateway_method_response.options_upload_urls.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.options_upload_urls]
}

# GET /posts
resource "aws_api_gateway_method" "list_posts" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.posts.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "list_posts" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.posts.id
  http_method             = aws_api_gateway_method.list_posts.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.list_posts.invoke_arn
}

resource "aws_api_gateway_method_response" "list_posts" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.posts.id
  http_method = aws_api_gateway_method.list_posts.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# DELETE /posts/{postId}
resource "aws_api_gateway_resource" "post_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.posts.id
  path_part   = "{postId}"
}

# /upload-urls
resource "aws_api_gateway_resource" "upload_urls" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "upload-urls"
}

resource "aws_api_gateway_method" "get_upload_urls" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload_urls.id
  http_method   = "POST"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "get_upload_urls" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.upload_urls.id
  http_method             = aws_api_gateway_method.get_upload_urls.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.get_upload_urls.invoke_arn
}

resource "aws_api_gateway_method_response" "get_upload_urls" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.upload_urls.id
  http_method = aws_api_gateway_method.get_upload_urls.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# DELETE /posts/{postId}
resource "aws_api_gateway_method" "delete_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.post_id.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_integration" "delete_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.post_id.id
  http_method             = aws_api_gateway_method.delete_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.delete_post.invoke_arn
}

resource "aws_api_gateway_method_response" "delete_post" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.post_id.id
  http_method = aws_api_gateway_method.delete_post.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
}

# OPTIONS /posts/{postId} (CORS)
resource "aws_api_gateway_method" "options_post_id" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.post_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "options_post_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.post_id.id
  http_method = aws_api_gateway_method.options_post_id.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "options_post_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.post_id.id
  http_method = aws_api_gateway_method.options_post_id.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "options_post_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.post_id.id
  http_method = aws_api_gateway_method.options_post_id.http_method
  status_code = aws_api_gateway_method_response.options_post_id.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

  depends_on = [aws_api_gateway_integration.options_post_id]
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.profile.id,
      aws_api_gateway_method.get_profile.id,
      aws_api_gateway_method.get_profile.authorization,
      aws_api_gateway_integration.get_profile.id,
      aws_api_gateway_method.post_profile.id,
      aws_api_gateway_method.post_profile.authorization,
      aws_api_gateway_integration.post_profile.id,
      aws_api_gateway_method.options_profile.id,
      aws_api_gateway_integration.options_profile.id,
      aws_api_gateway_resource.posts.id,
      aws_api_gateway_method.create_post.id,
      aws_api_gateway_method.create_post.authorization,
      aws_api_gateway_integration.create_post.id,
      aws_api_gateway_method.list_posts.id,
      aws_api_gateway_method.list_posts.authorization,
      aws_api_gateway_integration.list_posts.id,
      aws_api_gateway_method.options_posts.id,
      aws_api_gateway_integration.options_posts.id,
      aws_api_gateway_resource.post_id.id,
      aws_api_gateway_method.delete_post.id,
      aws_api_gateway_method.delete_post.authorization,
      aws_api_gateway_integration.delete_post.id,
      aws_api_gateway_method.options_post_id.id,
      aws_api_gateway_integration.options_post_id.id,
      aws_api_gateway_resource.upload_urls.id,
      aws_api_gateway_method.get_upload_urls.id,
      aws_api_gateway_method.get_upload_urls.authorization,
      aws_api_gateway_integration.get_upload_urls.id,
      aws_api_gateway_method.options_upload_urls.id,
      aws_api_gateway_integration.options_upload_urls.id,
      aws_api_gateway_gateway_response.unauthorized.id,
      aws_api_gateway_gateway_response.access_denied.id,
      aws_api_gateway_gateway_response.default_4xx.id,
      aws_api_gateway_gateway_response.default_5xx.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.get_profile,
    aws_api_gateway_integration.post_profile,
    aws_api_gateway_integration.options_profile,
    aws_api_gateway_integration_response.options_profile,
    aws_api_gateway_integration.create_post,
    aws_api_gateway_integration.list_posts,
    aws_api_gateway_integration.delete_post,
    aws_api_gateway_integration.options_posts,
    aws_api_gateway_integration_response.options_posts,
    aws_api_gateway_integration.options_post_id,
    aws_api_gateway_integration_response.options_post_id,
    aws_api_gateway_integration.get_upload_urls,
    aws_api_gateway_integration.options_upload_urls,
    aws_api_gateway_integration_response.options_upload_urls,
    aws_api_gateway_gateway_response.unauthorized,
    aws_api_gateway_gateway_response.access_denied,
    aws_api_gateway_gateway_response.default_4xx,
    aws_api_gateway_gateway_response.default_5xx,
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "prod"

  xray_tracing_enabled = true

  tags = local.serverless_app_tags
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.prod.stage_name
  method_path = "*/*"

  settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
    logging_level          = "INFO"
    data_trace_enabled     = false
    metrics_enabled        = true
  }
}

# Lambda Permissions
resource "aws_lambda_permission" "create_post" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_post.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.serverless_app_api_execution_arn}/*/*"
}

resource "aws_lambda_permission" "list_posts" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_posts.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.serverless_app_api_execution_arn}/*/*"
}

resource "aws_lambda_permission" "delete_post" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.delete_post.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.serverless_app_api_execution_arn}/*/*"
}

resource "aws_lambda_permission" "get_upload_urls" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_upload_urls.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.serverless_app_api_execution_arn}/*/*"
}

resource "aws_lambda_permission" "profile" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.profile.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${local.serverless_app_api_execution_arn}/*/*"
}

# Gateway Responses for CORS on errors
resource "aws_api_gateway_gateway_response" "unauthorized" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "UNAUTHORIZED"
  status_code   = "401"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"message\":\"$context.error.messageString\"}"
  }
}

resource "aws_api_gateway_gateway_response" "access_denied" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "ACCESS_DENIED"
  status_code   = "403"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"message\":\"$context.error.messageString\"}"
  }
}

resource "aws_api_gateway_gateway_response" "default_4xx" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"message\":$context.error.messageString}"
  }
}

resource "aws_api_gateway_gateway_response" "default_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,DELETE,OPTIONS'"
  }

  response_templates = {
    "application/json" = "{\"message\":$context.error.messageString}"
  }
}
