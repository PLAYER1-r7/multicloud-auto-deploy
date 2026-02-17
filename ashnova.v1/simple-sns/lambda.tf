# IAM Role for Lambda Functions
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.tags
}

# Managed Policy for Lambda Functions
resource "aws_iam_policy" "lambda" {
  name        = "${var.project_name}-lambda-policy"
  description = "Managed policy for simple-sns Lambda functions"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.posts.arn,
          "${aws_dynamodb_table.posts.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.images.arn}/*"
      }
    ]
  })

  tags = local.tags
}

# Attach Managed Policy to Lambda Role
resource "aws_iam_role_policy_attachment" "lambda" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "create_post" {
  name              = "/aws/lambda/${var.project_name}-CreatePostFunction"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "list_posts" {
  name              = "/aws/lambda/${var.project_name}-ListPostsFunction"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "delete_post" {
  name              = "/aws/lambda/${var.project_name}-DeletePostFunction"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "get_upload_urls" {
  name              = "/aws/lambda/${var.project_name}-GetUploadUrlsFunction"
  retention_in_days = 30
  tags              = local.tags
}

resource "aws_cloudwatch_log_group" "profile" {
  name              = "/aws/lambda/${var.project_name}-ProfileFunction"
  retention_in_days = 30
  tags              = local.tags
}

# Lambda Functions - Code only (dependencies in layer)
data "archive_file" "lambda_create" {
  type        = "zip"
  source_dir  = "${path.module}/dist"
  output_path = "${path.module}/.terraform/lambda/create.zip"
  excludes    = ["node_modules"]
}

data "archive_file" "lambda_list" {
  type        = "zip"
  source_dir  = "${path.module}/dist"
  output_path = "${path.module}/.terraform/lambda/list.zip"
  excludes    = ["node_modules"]
}

data "archive_file" "lambda_delete" {
  type        = "zip"
  source_dir  = "${path.module}/dist"
  output_path = "${path.module}/.terraform/lambda/delete.zip"
  excludes    = ["node_modules"]
}

data "archive_file" "lambda_get_upload_urls" {
  type        = "zip"
  source_dir  = "${path.module}/dist"
  output_path = "${path.module}/.terraform/lambda/getuploadurls.zip"
  excludes    = ["node_modules"]
}

data "archive_file" "lambda_profile" {
  type        = "zip"
  source_dir  = "${path.module}/dist"
  output_path = "${path.module}/.terraform/lambda/profile.zip"
  excludes    = ["node_modules"]
}

resource "aws_lambda_function" "create_post" {
  filename         = data.archive_file.lambda_create.output_path
  function_name    = "${var.project_name}-CreatePostFunction"
  role             = aws_iam_role.lambda.arn
  handler          = "createPost.handler"
  source_code_hash = data.archive_file.lambda_create.output_base64sha256
  runtime          = "nodejs22.x"
  timeout          = 15
  memory_size      = 128
  architectures    = ["x86_64"]
  layers           = [aws_lambda_layer_version.nodejs_dependencies.arn]

  environment {
    variables = {
      POSTS_TABLE_NAME   = aws_dynamodb_table.posts.name
      ALLOWED_USERS      = "userA,userB"
      IMAGES_BUCKET_NAME = aws_s3_bucket.images.bucket
      LOG_LEVEL          = "info"
      NODE_ENV           = "production"
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "list_posts" {
  filename         = data.archive_file.lambda_list.output_path
  function_name    = "${var.project_name}-ListPostsFunction"
  role             = aws_iam_role.lambda.arn
  handler          = "listPosts.handler"
  source_code_hash = data.archive_file.lambda_list.output_base64sha256
  runtime          = "nodejs22.x"
  timeout          = 15
  memory_size      = 128
  architectures    = ["x86_64"]
  layers           = [aws_lambda_layer_version.nodejs_dependencies.arn]

  environment {
    variables = {
      POSTS_TABLE_NAME   = aws_dynamodb_table.posts.name
      ALLOWED_USERS      = "userA,userB"
      IMAGES_BUCKET_NAME = aws_s3_bucket.images.bucket
      LOG_LEVEL          = "info"
      NODE_ENV           = "production"
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "delete_post" {
  filename         = data.archive_file.lambda_delete.output_path
  function_name    = "${var.project_name}-DeletePostFunction"
  role             = aws_iam_role.lambda.arn
  handler          = "deletePost.handler"
  source_code_hash = data.archive_file.lambda_delete.output_base64sha256
  runtime          = "nodejs22.x"
  timeout          = 15
  memory_size      = 128
  architectures    = ["x86_64"]
  layers           = [aws_lambda_layer_version.nodejs_dependencies.arn]

  environment {
    variables = {
      POSTS_TABLE_NAME   = aws_dynamodb_table.posts.name
      ALLOWED_USERS      = "userA,userB"
      IMAGES_BUCKET_NAME = aws_s3_bucket.images.bucket
      LOG_LEVEL          = "info"
      NODE_ENV           = "production"
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "get_upload_urls" {
  filename         = data.archive_file.lambda_get_upload_urls.output_path
  function_name    = "${var.project_name}-GetUploadUrlsFunction"
  role             = aws_iam_role.lambda.arn
  handler          = "getUploadUrls.handler"
  source_code_hash = data.archive_file.lambda_get_upload_urls.output_base64sha256
  runtime          = "nodejs22.x"
  timeout          = 10
  memory_size      = 128
  architectures    = ["x86_64"]
  layers           = [aws_lambda_layer_version.nodejs_dependencies.arn]

  environment {
    variables = {
      IMAGES_BUCKET_NAME = aws_s3_bucket.images.bucket
      LOG_LEVEL          = "info"
      NODE_ENV           = "production"
    }
  }

  tags = local.tags
}

resource "aws_lambda_function" "profile" {
  filename         = data.archive_file.lambda_profile.output_path
  function_name    = "${var.project_name}-ProfileFunction"
  role             = aws_iam_role.lambda.arn
  handler          = "profile.handler"
  source_code_hash = data.archive_file.lambda_profile.output_base64sha256
  runtime          = "nodejs22.x"
  timeout          = 15
  memory_size      = 128
  architectures    = ["x86_64"]
  layers           = [aws_lambda_layer_version.nodejs_dependencies.arn]

  environment {
    variables = {
      POSTS_TABLE_NAME   = aws_dynamodb_table.posts.name
      ALLOWED_USERS      = "userA,userB"
      IMAGES_BUCKET_NAME = aws_s3_bucket.images.bucket
      LOG_LEVEL          = "info"
      NODE_ENV           = "production"
    }
  }

  tags = local.tags
}
