# Allow unauthenticated access to Cloud Run services (Cloud Functions Gen2)
resource "google_cloud_run_service_iam_member" "create_post_invoker" {
  project  = google_cloudfunctions2_function.create_post.project
  location = google_cloudfunctions2_function.create_post.location
  service  = google_cloudfunctions2_function.create_post.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "list_posts_invoker" {
  project  = google_cloudfunctions2_function.list_posts.project
  location = google_cloudfunctions2_function.list_posts.location
  service  = google_cloudfunctions2_function.list_posts.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "delete_post_invoker" {
  project  = google_cloudfunctions2_function.delete_post.project
  location = google_cloudfunctions2_function.delete_post.location
  service  = google_cloudfunctions2_function.delete_post.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "get_upload_urls_invoker" {
  project  = google_cloudfunctions2_function.get_upload_urls.project
  location = google_cloudfunctions2_function.get_upload_urls.location
  service  = google_cloudfunctions2_function.get_upload_urls.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "profile_invoker" {
  project  = google_cloudfunctions2_function.profile.project
  location = google_cloudfunctions2_function.profile.location
  service  = google_cloudfunctions2_function.profile.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

data "google_project" "current" {}

resource "google_service_account" "functions_runtime" {
  account_id   = "${var.project_name}-${var.environment}-functions"
  display_name = "${var.project_name} ${var.environment} Cloud Functions"
  project      = var.gcp_project_id
}

resource "google_project_iam_member" "functions_firestore_user" {
  project = var.gcp_project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.functions_runtime.email}"
}

resource "google_storage_bucket_iam_member" "functions_images_object_admin" {
  bucket = google_storage_bucket.images.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.functions_runtime.email}"
}

resource "google_service_account_iam_member" "functions_runtime_signer" {
  service_account_id = google_service_account.functions_runtime.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.functions_runtime.email}"
}

# Allow Cloud Functions service account to sign URLs
resource "google_service_account_iam_member" "functions_signer" {
  service_account_id = "projects/${data.google_project.current.project_id}/serviceAccounts/${data.google_project.current.number}-compute@developer.gserviceaccount.com"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${data.google_project.current.number}-compute@developer.gserviceaccount.com"
}
