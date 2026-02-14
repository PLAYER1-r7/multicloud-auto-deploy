# Cloud Storage bucket for frontend
resource "google_storage_bucket" "frontend" {
  name          = "${local.resource_prefix}-frontend"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = false  # Allow fine-grained ACLs

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  labels = local.common_labels
}

# Make bucket objects public
resource "google_storage_default_object_acl" "frontend_public" {
  bucket = google_storage_bucket.frontend.name

  role_entity = [
    "READER:allUsers",
  ]
}

# Reserve a global IP address
resource "google_compute_global_address" "frontend" {
  name = "${local.resource_prefix}-frontend-ip"
}

# Backend bucket for Load Balancer
resource "google_compute_backend_bucket" "frontend" {
  name        = "${local.resource_prefix}-backend"
  bucket_name = google_storage_bucket.frontend.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    client_ttl        = 3600
    negative_caching  = true
  }

  custom_response_headers = [
    "X-Cache-Status: {cdn_cache_status}"
  ]
}

# URL Map
resource "google_compute_url_map" "frontend" {
  name            = "${local.resource_prefix}-urlmap"
  default_service = google_compute_backend_bucket.frontend.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "allpaths"
  }

  path_matcher {
    name            = "allpaths"
    default_service = google_compute_backend_bucket.frontend.id

    path_rule {
      paths   = ["/"]
      service = google_compute_backend_bucket.frontend.id
      route_action {
        url_rewrite {
          path_prefix_rewrite = "/index.html"
        }
      }
    }
  }
}

# HTTP proxy
resource "google_compute_target_http_proxy" "frontend" {
  name    = "${local.resource_prefix}-http-proxy"
  url_map = google_compute_url_map.frontend.id
}

# Forwarding rule (HTTP)
resource "google_compute_global_forwarding_rule" "frontend_http" {
  name       = "${local.resource_prefix}-http-rule"
  target     = google_compute_target_http_proxy.frontend.id
  port_range = "80"
  ip_address = google_compute_global_address.frontend.address
}
