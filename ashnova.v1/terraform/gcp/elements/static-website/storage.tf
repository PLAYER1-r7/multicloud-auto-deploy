# Cloud Storage Bucket for static website
resource "google_storage_bucket" "static_site" {
  name          = "${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location      = var.bucket_location
  force_destroy = true

  uniform_bucket_level_access = true

  # バージョニング有効化
  versioning {
    enabled = true
  }

  # ライフサイクルルール（古いバージョンの削除）
  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }

  # ログ設定
  logging {
    log_bucket        = google_storage_bucket.logs.name
    log_object_prefix = "gcs-logs/"
  }

  website {
    main_page_suffix = "index.html"
    not_found_page   = "error.html"
  }

  labels = var.labels
}

# ログ用バケット
resource "google_storage_bucket" "logs" {
  name          = "${var.project_name}-logs-${random_string.suffix.result}"
  location      = var.bucket_location
  force_destroy = true

  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels
}

# Make bucket publicly readable
resource "google_storage_bucket_iam_member" "public_read" {
  bucket = google_storage_bucket.static_site.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}
