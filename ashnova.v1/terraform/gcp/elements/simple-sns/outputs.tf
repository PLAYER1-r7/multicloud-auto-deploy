output "project_id" {
  description = "GCP Project ID"
  value       = var.gcp_project_id
}

output "region" {
  description = "GCP Region"
  value       = var.gcp_region
}

# output "firestore_database" {
#   description = "Firestore Database Name"
#   value       = google_firestore_database.simple_sns.name
# }

output "images_bucket" {
  description = "Images Storage Bucket Name"
  value       = google_storage_bucket.images.name
}

output "frontend_bucket" {
  description = "Frontend Storage Bucket Name"
  value       = google_storage_bucket.frontend.name
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://storage.googleapis.com/${google_storage_bucket.frontend.name}/index.html"
}

output "create_post_url" {
  description = "Create Post Cloud Function URL"
  value       = google_cloudfunctions2_function.create_post.service_config[0].uri
}

output "list_posts_url" {
  description = "List Posts Cloud Function URL"
  value       = google_cloudfunctions2_function.list_posts.service_config[0].uri
}

output "delete_post_url" {
  description = "Delete Post Cloud Function URL"
  value       = google_cloudfunctions2_function.delete_post.service_config[0].uri
}

output "get_upload_urls_url" {
  description = "Get Upload URLs Cloud Function URL"
  value       = google_cloudfunctions2_function.get_upload_urls.service_config[0].uri
}

output "profile_url" {
  description = "Profile Cloud Function URL"
  value       = google_cloudfunctions2_function.profile.service_config[0].uri
}
