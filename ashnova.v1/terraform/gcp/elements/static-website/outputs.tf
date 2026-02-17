output "bucket_name" {
  description = "Storage bucket name"
  value       = google_storage_bucket.static_site.name
}

output "bucket_url" {
  description = "Storage bucket URL"
  value       = google_storage_bucket.static_site.url
}

output "bucket_website_url" {
  description = "Bucket website URL (without CDN)"
  value       = "https://storage.googleapis.com/${google_storage_bucket.static_site.name}/index.html"
}

output "load_balancer_ip" {
  description = "Load Balancer IP address"
  value       = var.enable_cdn ? google_compute_global_address.static_site[0].address : null
}

output "website_url" {
  description = "Website URL"
  value = var.enable_cdn ? (
    length(local.custom_domains) > 0 ? "https://${local.custom_domains[0]}" : "http://${google_compute_global_address.static_site[0].address}"
  ) : "https://storage.googleapis.com/${google_storage_bucket.static_site.name}/index.html"
}

output "dns_configuration" {
  description = "DNS configuration for custom domains"
  value = var.enable_cdn && length(local.custom_domains) > 0 ? {
    domains = local.custom_domains
    type    = "A"
    value   = google_compute_global_address.static_site[0].address
  } : null
}

output "custom_domain" {
  description = "Primary custom domain name"
  value       = length(local.custom_domains) > 0 ? local.custom_domains[0] : null
}

output "custom_domains" {
  description = "Custom domain names"
  value       = local.custom_domains
}

output "ssl_certificate_id" {
  description = "SSL certificate resource ID"
  value       = var.enable_cdn && length(local.custom_domains) > 0 ? google_compute_managed_ssl_certificate.static_site[0].id : null
}
