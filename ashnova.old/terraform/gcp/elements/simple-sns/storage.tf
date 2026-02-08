# Cloud Storage Bucket for Images
resource "google_storage_bucket" "images" {
  name          = local.images_bucket_name
  location      = var.gcp_region
  force_destroy = true

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  cors {
    origin          = local.allowed_origins_final
    method          = ["GET", "PUT", "POST"]
    response_header = ["*"]
    max_age_seconds = 3600
  }

  versioning {
    enabled = true
  }

  logging {
    log_bucket        = google_storage_bucket.logs.name
    log_object_prefix = "images/"
  }

  labels = var.labels
}

# Cloud Storage Bucket for Frontend
resource "google_storage_bucket" "frontend" {
  name          = local.frontend_bucket_name
  location      = var.gcp_region
  force_destroy = true

  uniform_bucket_level_access = true

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  logging {
    log_bucket        = google_storage_bucket.logs.name
    log_object_prefix = "frontend/"
  }

  labels = var.labels
}

# Access logs bucket
resource "google_storage_bucket" "logs" {
  name          = local.logs_bucket_name
  location      = var.gcp_region
  force_destroy = true

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels
}

# Make frontend bucket publicly readable
resource "google_storage_bucket_iam_member" "frontend_public" {
  count  = var.frontend_public ? 1 : 0
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
