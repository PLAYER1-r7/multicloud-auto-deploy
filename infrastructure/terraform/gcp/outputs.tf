# Outputs
output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

output "frontend_bucket_name" {
  description = "Frontend storage bucket name"
  value       = google_storage_bucket.frontend.name
}

output "frontend_bucket_url" {
  description = "Frontend storage bucket URL"
  value       = "https://storage.googleapis.com/${google_storage_bucket.frontend.name}/index.html"
}

output "frontend_url" {
  description = "Frontend URL (Cloud Storage static website)"
  value       = google_storage_bucket.frontend.url
}

output "frontend_cdn_ip" {
  description = "Frontend CDN global IP address"
  value       = google_compute_global_address.frontend.address
}

output "frontend_cdn_url" {
  description = "Frontend CDN URL"
  value       = "http://${google_compute_global_address.frontend.address}"
}

output "api_url" {
  description = "Cloud Run API URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "cloud_run_service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.api.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.main.name
}

output "firestore_database" {
  description = "Firestore database name"
  value       = google_firestore_database.main.name
}
