# S3 Bucket for static website
resource "aws_s3_bucket" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = "${var.project_name}-${random_string.bucket_suffix.result}"

  tags = merge(var.tags, {
    Name = "${var.project_name}-bucket"
  })
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.static_site[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.static_site[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Logging
resource "aws_s3_bucket" "logs" {
  count  = var.enable_static_site ? 1 : 0
  bucket = "${var.project_name}-logs-${random_string.bucket_suffix.result}"

  tags = merge(var.tags, {
    Name = "${var.project_name}-logs"
  })
}

# S3 Logs Bucket Ownership Controls (CloudFrontログ用)
resource "aws_s3_bucket_ownership_controls" "logs" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  rule {
    object_ownership = "ObjectWriter"
  }
}

# S3 Logs Bucket Policy for CloudFront Logging
resource "aws_s3_bucket_policy" "logs" {
  count  = local.enable_cloudfront ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontLogs"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.logs[0].arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = local.enable_cloudfront ? aws_cloudfront_distribution.static_site[0].arn : ""
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.logs[0].arn,
          "${aws_s3_bucket.logs[0].arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.logs]
}

resource "aws_s3_bucket_logging" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.static_site[0].id

  target_bucket = aws_s3_bucket.logs[0].id
  target_prefix = "s3-access-logs/"
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.static_site[0].id

  block_public_acls       = local.enable_cloudfront ? true : false
  block_public_policy     = local.enable_cloudfront ? true : false
  ignore_public_acls      = local.enable_cloudfront ? true : false
  restrict_public_buckets = local.enable_cloudfront ? true : false
}

# S3 Logs Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "logs" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.logs[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Website Configuration
resource "aws_s3_bucket_website_configuration" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.static_site[0].id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "error.html"
  }
}

# S3 Bucket Policy for CloudFront or Public Access
resource "aws_s3_bucket_policy" "static_site" {
  count  = var.enable_static_site ? 1 : 0
  bucket = aws_s3_bucket.static_site[0].id

  policy = local.enable_cloudfront ? data.aws_iam_policy_document.cloudfront_oac[0].json : data.aws_iam_policy_document.public_read[0].json

  depends_on = [aws_s3_bucket_public_access_block.static_site]
}

# Policy for CloudFront OAC
data "aws_iam_policy_document" "cloudfront_oac" {
  count = local.enable_cloudfront ? 1 : 0
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.static_site[0].arn}/*"
    ]

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [local.enable_cloudfront ? aws_cloudfront_distribution.static_site[0].arn : ""]
    }
  }

  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = [
      aws_s3_bucket.static_site[0].arn,
      "${aws_s3_bucket.static_site[0].arn}/*"
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

# Policy for public read (without CloudFront)
data "aws_iam_policy_document" "public_read" {
  count = var.enable_static_site ? 1 : 0
  statement {
    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.static_site[0].arn}/*"
    ]
  }

  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    resources = [
      aws_s3_bucket.static_site[0].arn,
      "${aws_s3_bucket.static_site[0].arn}/*"
    ]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}
