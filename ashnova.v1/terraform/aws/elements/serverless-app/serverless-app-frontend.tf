# Frontend S3 Bucket
resource "aws_s3_bucket" "serverless_app_frontend" {
  bucket = local.serverless_app_frontend_bucket_name

  tags = local.serverless_app_tags
}

# ACM Certificate for Serverless App CloudFront (us-east-1)
resource "aws_acm_certificate" "serverless_app_cert" {

  provider          = aws.us-east-1
  domain_name       = local.serverless_app_primary_domain
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.serverless_app_tags, {
    Name = "${var.serverless_app_project_name}-cloudfront-cert"
  })
}

# Frontend S3 Bucket Logging
resource "aws_s3_bucket_logging" "serverless_app_frontend" {
  bucket = aws_s3_bucket.serverless_app_frontend.id

  target_bucket = aws_s3_bucket.serverless_app_logs.id
  target_prefix = "frontend/"
}

# Frontend S3 Bucket Website Configuration
resource "aws_s3_bucket_website_configuration" "serverless_app_frontend" {
  bucket = aws_s3_bucket.serverless_app_frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Frontend S3 Bucket Public Access Block (Block Public Access)
resource "aws_s3_bucket_public_access_block" "serverless_app_frontend" {
  bucket = aws_s3_bucket.serverless_app_frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Frontend S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "serverless_app_frontend" {
  bucket = aws_s3_bucket.serverless_app_frontend.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Frontend S3 Bucket Lifecycle
resource "aws_s3_bucket_lifecycle_configuration" "serverless_app_frontend" {
  bucket = aws_s3_bucket.serverless_app_frontend.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "serverless_app_frontend" {
  name                              = "${var.serverless_app_project_name}-frontend-oac"
  description                       = "OAC for frontend S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Response Headers Policy for Serverless App
resource "aws_cloudfront_response_headers_policy" "serverless_app_security_headers" {
  name = "${var.serverless_app_project_name}-security-headers"

  security_headers_config {
    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }

    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = true
      override                   = true
    }

    xss_protection {
      mode_block = true
      protection = true
      override   = true
    }

    content_security_policy {
      content_security_policy = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'"
      override                = true
    }
  }
}

# Import existing CloudFront distribution
resource "aws_cloudfront_distribution" "serverless_app_frontend" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  aliases             = var.serverless_app_cloudfront_aliases
  web_acl_id          = var.serverless_app_cloudfront_web_acl_id != "" ? var.serverless_app_cloudfront_web_acl_id : null

  origin {
    domain_name              = aws_s3_bucket.serverless_app_frontend.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.serverless_app_frontend.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.serverless_app_frontend.id
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.serverless_app_frontend.id}"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"

    response_headers_policy_id = var.enable_serverless_app_cloudfront_security_headers ? aws_cloudfront_response_headers_policy.serverless_app_security_headers.id : null

    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  dynamic "logging_config" {
    for_each = var.enable_serverless_app_cloudfront_logging ? [1] : []
    content {
      include_cookies = false
      bucket          = aws_s3_bucket.serverless_app_logs.bucket_domain_name
      prefix          = "cloudfront/"
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.serverless_app_cert.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  tags = local.serverless_app_tags

  lifecycle {
    ignore_changes = [
      web_acl_id
    ]
  }
}

# Frontend S3 Bucket Policy (CloudFront OAC Access Only)
resource "aws_s3_bucket_policy" "serverless_app_frontend" {
  bucket = aws_s3_bucket.serverless_app_frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.serverless_app_frontend.arn}/*"
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
          aws_s3_bucket.serverless_app_frontend.arn,
          "${aws_s3_bucket.serverless_app_frontend.arn}/*"
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
    aws_s3_bucket_public_access_block.serverless_app_frontend,
    aws_cloudfront_distribution.serverless_app_frontend
  ]
}
