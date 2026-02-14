# Artifact Registry repository for container images
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  repository_id = "${local.resource_prefix}-repo"
  description   = "Docker repository for multicloud-auto-deploy"
  format        = "DOCKER"
  labels        = local.common_labels
}

# Cloud Run service for API
resource "google_cloud_run_v2_service" "api" {
  name     = "${local.resource_prefix}-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.main.repository_id}/multicloud-auto-deploy-api:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "CLOUD_PROVIDER"
        value = "gcp"
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "FIRESTORE_DATABASE"
        value = google_firestore_database.main.name
      }
    }
  }

  labels = local.common_labels

  depends_on = [
    google_firestore_database.main
  ]
}

# Make Cloud Run service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
