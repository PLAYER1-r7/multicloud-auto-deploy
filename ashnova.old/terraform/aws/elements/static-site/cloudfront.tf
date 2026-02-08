# ACM Certificate for CloudFront (us-east-1)
resource "aws_acm_certificate" "cloudfront_cert" {
  count = local.enable_cloudfront && var.domain_name != "" ? 1 : 0

  provider          = aws.us-east-1
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-cloudfront-cert"
  })
}

# ACM Certificate Validation
# 注意: 証明書の検証はDNSレコード追加後に自動的に行われます
# このリソースは証明書検証の完了を待機しますが、DNSレコードが追加されるまで
# タイムアウトするため、コメントアウトしています
# resource "aws_acm_certificate_validation" "cloudfront_cert" {
#   count = var.enable_cloudfront && var.domain_name != "" ? 1 : 0
#
#   provider                = aws.us-east-1
#   certificate_arn         = aws_acm_certificate.cloudfront_cert[0].arn
#   validation_record_fqdns = [for record in aws_acm_certificate.cloudfront_cert[0].domain_validation_options : record.resource_record_name]
#
#   timeouts {
#     create = "10m"
#   }
# }

# CloudFront Origin Access Control
resource "aws_cloudfront_origin_access_control" "static_site" {
  count = local.enable_cloudfront ? 1 : 0

  name                              = "${var.project_name}-oac"
  description                       = "OAC for ${var.project_name}"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront Response Headers Policy
resource "aws_cloudfront_response_headers_policy" "security_headers" {
  count = local.enable_cloudfront ? 1 : 0

  name = "${var.project_name}-security-headers"

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

# CloudFront Distribution
resource "aws_cloudfront_distribution" "static_site" {
  count = local.enable_cloudfront ? 1 : 0

  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${var.project_name} distribution"
  price_class         = "PriceClass_100" # Use only North America and Europe

  origin {
    domain_name              = aws_s3_bucket.static_site[0].bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.static_site[0].id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.static_site[0].id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.static_site[0].id}"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy     = "redirect-to-https"
    min_ttl                    = 0
    default_ttl                = 3600
    max_ttl                    = 86400
    compress                   = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security_headers[0].id
  }

  # CloudFront アクセスログ
  logging_config {
    include_cookies = false
    bucket          = aws_s3_bucket.logs[0].bucket_domain_name
    prefix          = "cloudfront-logs/"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 404
    response_page_path = "/error.html"
  }

  custom_error_response {
    error_code         = 403
    response_code      = 404
    response_page_path = "/error.html"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  aliases = var.domain_name != "" && var.use_custom_domain_in_cloudfront ? [var.domain_name] : []

  viewer_certificate {
    cloudfront_default_certificate = var.domain_name == "" || !var.use_custom_domain_in_cloudfront
    acm_certificate_arn            = var.domain_name != "" && var.use_custom_domain_in_cloudfront ? aws_acm_certificate.cloudfront_cert[0].arn : null
    ssl_support_method             = var.domain_name != "" && var.use_custom_domain_in_cloudfront ? "sni-only" : null
    minimum_protocol_version       = var.domain_name != "" && var.use_custom_domain_in_cloudfront ? "TLSv1.2_2021" : null
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-distribution"
  })

  # 注意: 証明書の検証が完了するまでCloudFrontはカスタムドメインを使用できません
  # DNSレコードを追加して証明書が検証されるまで待ってください
  depends_on = [aws_acm_certificate.cloudfront_cert]
}
