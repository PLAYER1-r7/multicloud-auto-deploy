locals {
  custom_domains          = length(var.custom_domains) > 0 ? var.custom_domains : (var.custom_domain != "" ? [var.custom_domain] : [])
  host_backend_bucket_map = var.enable_cdn && var.backend_type == "bucket" ? var.host_backend_bucket_map : {}
  use_cloudrun            = var.backend_type == "cloudrun"
  lb_scheme               = local.use_cloudrun ? "EXTERNAL_MANAGED" : "EXTERNAL"
  default_host            = var.default_host != "" ? var.default_host : (length(local.custom_domains) > 0 ? local.custom_domains[0] : "")
  cloudrun_hosts          = local.use_cloudrun ? var.cloudrun_images : {}
  cloudrun_extra_hosts    = local.use_cloudrun ? { for host, image in var.cloudrun_images : host => image if host != local.default_host } : {}
  cloudrun_service_account_email = var.cloudrun_service_account_email != "" ? var.cloudrun_service_account_email : (
    local.use_cloudrun && var.create_cloudrun_service_account ? google_service_account.cloudrun_frontend[0].email : null
  )
}

resource "google_service_account" "cloudrun_frontend" {
  count = local.use_cloudrun && var.create_cloudrun_service_account && var.cloudrun_service_account_email == "" ? 1 : 0

  account_id   = "${var.project_name}-${var.environment}-frontend"
  display_name = "${var.project_name} ${var.environment} Cloud Run Frontend"
  project      = var.gcp_project_id
}

# Reserve a global static IP address for Load Balancer
resource "google_compute_global_address" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name = "${var.project_name}-${var.environment}-ip"
}

# Backend bucket for Load Balancer
resource "google_compute_backend_bucket" "static_site" {
  count = var.enable_cdn && !local.use_cloudrun ? 1 : 0

  name        = "${var.project_name}-${var.environment}-backend"
  bucket_name = google_storage_bucket.static_site.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    client_ttl        = 3600
    default_ttl       = 3600
    max_ttl           = 86400
    negative_caching  = true
    serve_while_stale = 86400
  }

  # 注意: Backend BucketではCloud Armorセキュリティポリシーは使用できません
  # セキュリティはCloud Storageのバージョニング、ログ、IAMで管理します
}

resource "google_compute_backend_bucket" "extra" {
  for_each = local.host_backend_bucket_map

  name        = "${var.project_name}-${var.environment}-backend-${replace(each.key, ".", "-")}"
  bucket_name = each.value
  enable_cdn  = true
}

resource "google_cloud_run_v2_service" "static_site" {
  for_each = local.cloudrun_hosts

  name     = "${var.project_name}-${var.environment}-${replace(each.key, ".", "-")}"
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = local.cloudrun_service_account_email
    containers {
      image = each.value
    }
  }
}

resource "google_cloud_run_v2_service_iam_member" "static_site_invoker" {
  for_each = local.cloudrun_hosts

  project  = var.gcp_project_id
  location = var.gcp_region
  name     = google_cloud_run_v2_service.static_site[each.key].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_compute_region_network_endpoint_group" "serverless" {
  for_each = local.cloudrun_hosts

  name                  = "${var.project_name}-${var.environment}-neg-${replace(each.key, ".", "-")}"
  region                = var.gcp_region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.static_site[each.key].name
  }
}

resource "google_compute_backend_service" "cloudrun_default" {
  count = var.enable_cdn && local.use_cloudrun ? 1 : 0

  name                  = "${var.project_name}-${var.environment}-backend-service"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = true

  backend {
    group = google_compute_region_network_endpoint_group.serverless[local.default_host].id
  }
}

resource "google_compute_backend_service" "cloudrun_extra" {
  for_each = local.cloudrun_extra_hosts

  name                  = "${var.project_name}-${var.environment}-backend-service-${replace(each.key, ".", "-")}"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  enable_cdn            = true

  backend {
    group = google_compute_region_network_endpoint_group.serverless[each.key].id
  }
}

# 注意: Cloud ArmorはBackend Bucketではサポートされていません
# Backend Service（より複雑な構成）を使用する場合のみCloud Armorが利用可能です
# 静的サイトのセキュリティはCloud Storageレベルで管理します：
# - バージョニング有効化
# - アクセスログ記録
# - IAM権限管理

# URL Map
resource "google_compute_url_map" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name            = "${var.project_name}-${var.environment}-url-map"
  default_service = local.use_cloudrun ? google_compute_backend_service.cloudrun_default[0].self_link : google_compute_backend_bucket.static_site[0].self_link

  depends_on = [
    google_compute_backend_bucket.static_site,
    google_compute_backend_bucket.extra
  ]

  dynamic "host_rule" {
    for_each = local.use_cloudrun ? local.cloudrun_extra_hosts : local.host_backend_bucket_map
    content {
      hosts        = [host_rule.key]
      path_matcher = "pm-${replace(host_rule.key, ".", "-")}"
    }
  }

  dynamic "path_matcher" {
    for_each = local.use_cloudrun ? local.cloudrun_extra_hosts : local.host_backend_bucket_map
    content {
      name            = "pm-${replace(path_matcher.key, ".", "-")}"
      default_service = local.use_cloudrun ? google_compute_backend_service.cloudrun_extra[path_matcher.key].self_link : google_compute_backend_bucket.extra[path_matcher.key].self_link
    }
  }
}

# HTTP proxy
resource "google_compute_target_http_proxy" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name    = "${var.project_name}-${var.environment}-http-proxy"
  url_map = google_compute_url_map.static_site[0].self_link
}

# Global forwarding rule (HTTP)
resource "google_compute_global_forwarding_rule" "http" {
  count = var.enable_cdn ? 1 : 0

  name                  = "${var.project_name}-${var.environment}-http-rule"
  target                = google_compute_target_http_proxy.static_site[0].self_link
  port_range            = "80"
  ip_address            = google_compute_global_address.static_site[0].address
  load_balancing_scheme = local.lb_scheme
}

# HTTPS configuration (requires SSL certificate)
# Managed SSL Certificate (requires custom domain)
resource "google_compute_managed_ssl_certificate" "static_site" {
  count = var.enable_cdn && length(local.custom_domains) > 0 ? 1 : 0

  name = "${var.project_name}-${var.environment}-cert-${random_id.ssl_cert_suffix.hex}"

  managed {
    domains = local.custom_domains
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "random_id" "ssl_cert_suffix" {
  byte_length = 4

  keepers = {
    domains = join(",", local.custom_domains)
  }
}

# HTTPS proxy (only if custom domain is provided)
resource "google_compute_target_https_proxy" "static_site" {
  count = var.enable_cdn && length(local.custom_domains) > 0 ? 1 : 0

  name             = "${var.project_name}-${var.environment}-https-proxy"
  url_map          = google_compute_url_map.static_site[0].self_link
  ssl_certificates = [google_compute_managed_ssl_certificate.static_site[0].self_link]
}

# Global forwarding rule (HTTPS)
resource "google_compute_global_forwarding_rule" "https" {
  count = var.enable_cdn && length(local.custom_domains) > 0 ? 1 : 0

  name                  = "${var.project_name}-${var.environment}-https-rule"
  target                = google_compute_target_https_proxy.static_site[0].self_link
  port_range            = "443"
  ip_address            = google_compute_global_address.static_site[0].address
  load_balancing_scheme = local.lb_scheme
}
