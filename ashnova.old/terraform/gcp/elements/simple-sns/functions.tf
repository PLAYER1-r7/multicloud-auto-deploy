# Upload function source archive
resource "google_storage_bucket_object" "functions_zip" {
  name         = "simple-sns-functions.zip"
  bucket       = google_storage_bucket.logs.name
  source       = abspath(var.functions_zip_path)
  content_type = "application/zip"
}

# Cloud Function: Create Post
resource "google_cloudfunctions2_function" "create_post" {
  name     = "${var.project_name}-create-post"
  location = var.gcp_region

  build_config {
    runtime     = var.functions_runtime
    entry_point = "createPost"
    source {
      storage_source {
        bucket     = google_storage_bucket.logs.name
        object     = google_storage_bucket_object.functions_zip.name
        generation = google_storage_bucket_object.functions_zip.generation
      }
    }
  }

  service_config {
    max_instance_count    = var.functions_max_instance_count
    min_instance_count    = var.functions_min_instance_count
    timeout_seconds       = var.functions_timeout_seconds
    service_account_email = google_service_account.functions_runtime.email
    environment_variables = {
      STORAGE_BUCKET = google_storage_bucket.images.name
      ALLOWED_ORIGIN = join(",", local.allowed_origins_final)
    }
  }

  depends_on = [google_project_service.cloudfunctions]
}

# Cloud Function: List Posts
resource "google_cloudfunctions2_function" "list_posts" {
  name     = "${var.project_name}-list-posts"
  location = var.gcp_region

  build_config {
    runtime     = var.functions_runtime
    entry_point = "listPosts"
    source {
      storage_source {
        bucket     = google_storage_bucket.logs.name
        object     = google_storage_bucket_object.functions_zip.name
        generation = google_storage_bucket_object.functions_zip.generation
      }
    }
  }

  service_config {
    max_instance_count    = var.functions_max_instance_count
    min_instance_count    = var.functions_min_instance_count
    timeout_seconds       = var.functions_timeout_seconds
    service_account_email = google_service_account.functions_runtime.email
    environment_variables = {
      STORAGE_BUCKET = google_storage_bucket.images.name
      ALLOWED_ORIGIN = join(",", local.allowed_origins_final)
    }
  }

  depends_on = [google_project_service.cloudfunctions]
}

# Cloud Function: Delete Post
resource "google_cloudfunctions2_function" "delete_post" {
  name     = "${var.project_name}-delete-post"
  location = var.gcp_region

  build_config {
    runtime     = var.functions_runtime
    entry_point = "deletePost"
    source {
      storage_source {
        bucket     = google_storage_bucket.logs.name
        object     = google_storage_bucket_object.functions_zip.name
        generation = google_storage_bucket_object.functions_zip.generation
      }
    }
  }

  service_config {
    max_instance_count    = var.functions_max_instance_count
    min_instance_count    = var.functions_min_instance_count
    timeout_seconds       = var.functions_timeout_seconds
    service_account_email = google_service_account.functions_runtime.email
    environment_variables = {
      STORAGE_BUCKET = google_storage_bucket.images.name
      ALLOWED_ORIGIN = join(",", local.allowed_origins_final)
    }
  }

  depends_on = [google_project_service.cloudfunctions]
}

# Cloud Function: Get Upload URLs
resource "google_cloudfunctions2_function" "get_upload_urls" {
  name     = "${var.project_name}-get-upload-urls"
  location = var.gcp_region

  build_config {
    runtime     = var.functions_runtime
    entry_point = "getUploadUrls"
    source {
      storage_source {
        bucket     = google_storage_bucket.logs.name
        object     = google_storage_bucket_object.functions_zip.name
        generation = google_storage_bucket_object.functions_zip.generation
      }
    }
  }

  service_config {
    max_instance_count    = var.functions_max_instance_count
    min_instance_count    = var.functions_min_instance_count
    timeout_seconds       = var.functions_timeout_seconds
    service_account_email = google_service_account.functions_runtime.email
    environment_variables = {
      STORAGE_BUCKET = google_storage_bucket.images.name
      ALLOWED_ORIGIN = join(",", local.allowed_origins_final)
    }
  }

  depends_on = [google_project_service.cloudfunctions]
}

# Cloud Function: Profile
resource "google_cloudfunctions2_function" "profile" {
  name     = "${var.project_name}-profile"
  location = var.gcp_region

  build_config {
    runtime     = var.functions_runtime
    entry_point = "profile"
    source {
      storage_source {
        bucket     = google_storage_bucket.logs.name
        object     = google_storage_bucket_object.functions_zip.name
        generation = google_storage_bucket_object.functions_zip.generation
      }
    }
  }

  service_config {
    max_instance_count    = var.functions_max_instance_count
    min_instance_count    = var.functions_min_instance_count
    timeout_seconds       = var.functions_timeout_seconds
    service_account_email = google_service_account.functions_runtime.email
    environment_variables = {
      STORAGE_BUCKET = google_storage_bucket.images.name
      ALLOWED_ORIGIN = join(",", local.allowed_origins_final)
    }
  }

  depends_on = [google_project_service.cloudfunctions]
}
