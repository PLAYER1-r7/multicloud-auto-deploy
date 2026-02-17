resource "random_string" "suffix" {
  length  = var.bucket_name_suffix_length
  special = false
  upper   = false
}

locals {
  bucket_suffix          = coalesce(var.bucket_name_suffix, random_string.suffix.result)
  images_bucket_name     = "${var.project_name}-images-${local.bucket_suffix}"
  frontend_bucket_name   = "${var.project_name}-frontend-${local.bucket_suffix}"
  logs_bucket_name       = "${var.project_name}-logs-${local.bucket_suffix}"
  frontend_bucket_origin = "https://${local.frontend_bucket_name}.storage.googleapis.com"
  allowed_origins_final = distinct(compact(concat(
    var.allowed_origins,
    var.include_gcs_origin ? ["https://storage.googleapis.com"] : [],
    var.include_frontend_bucket_origin ? [local.frontend_bucket_origin] : []
  )))
}
