# S3 Access Logs Bucket
resource "aws_s3_bucket" "serverless_app_logs" {
  bucket = "${var.serverless_app_project_name}-access-logs"
  tags   = local.serverless_app_tags
}

resource "aws_s3_bucket_ownership_controls" "serverless_app_logs" {
  bucket = aws_s3_bucket.serverless_app_logs.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# ACL is not supported for this bucket configuration
# resource "aws_s3_bucket_acl" "serverless_app_logs" {
#   count = var.enable_serverless_app ? 1 : 0
#   bucket = aws_s3_bucket.serverless_app_logs.id
#   acl    = "log-delivery-write"
#
#   depends_on = [aws_s3_bucket_ownership_controls.logs]
# }

resource "aws_s3_bucket_public_access_block" "serverless_app_logs" {
  bucket = aws_s3_bucket.serverless_app_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "serverless_app_logs" {
  bucket = aws_s3_bucket.serverless_app_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "serverless_app_logs" {
  bucket = aws_s3_bucket.serverless_app_logs.id

  rule {
    id     = "DeleteOldLogs"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# S3 Access Logs Bucket Policy - Enforce SSL/TLS and Allow CloudFront Logging
resource "aws_s3_bucket_policy" "serverless_app_logs" {
  bucket = aws_s3_bucket.serverless_app_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontLogging"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.serverless_app_logs.arn}/cloudfront/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = local.serverless_app_cloudfront_source_arn
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.serverless_app_logs.arn,
          "${aws_s3_bucket.serverless_app_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [
    aws_cloudfront_distribution.serverless_app_frontend
  ]
}

# Images S3 Bucket
resource "aws_s3_bucket" "serverless_app_images" {
  bucket = "${var.serverless_app_project_name}-images"
  tags   = local.serverless_app_tags
}

resource "aws_s3_bucket_logging" "serverless_app_images" {
  bucket = aws_s3_bucket.serverless_app_images.id

  target_bucket = aws_s3_bucket.serverless_app_logs.id
  target_prefix = "images/"
}

resource "aws_s3_bucket_public_access_block" "serverless_app_images" {
  bucket = aws_s3_bucket.serverless_app_images.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "serverless_app_images" {
  bucket = aws_s3_bucket.serverless_app_images.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "serverless_app_images" {
  bucket = aws_s3_bucket.serverless_app_images.id

  rule {
    id     = "DeleteOldVersions"
    status = "Enabled"

    filter {}

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "serverless_app_images" {
  bucket = aws_s3_bucket.serverless_app_images.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    max_age_seconds = 3600
  }

  # CORS rule for presigned URL uploads
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT"]
    allowed_origins = [var.serverless_app_web_origin, "http://localhost:5173"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_policy" "serverless_app_images" {
  bucket = aws_s3_bucket.serverless_app_images.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.serverless_app_images.arn,
          "${aws_s3_bucket.serverless_app_images.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}
