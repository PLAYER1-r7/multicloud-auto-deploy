output "bucket_name" {
  value = module.static_website.static_site_bucket_name
}

output "bucket_url" {
  value = module.static_website.static_site_bucket_url
}

output "bucket_website_url" {
  value = module.static_website.static_site_bucket_website_url
}

output "load_balancer_ip" {
  value = module.static_website.static_site_load_balancer_ip
}

output "website_url" {
  value = module.static_website.static_site_website_url
}

output "dns_configuration" {
  value = module.static_website.static_site_dns_configuration
}

output "custom_domain" {
  value = module.static_website.static_site_custom_domain
}

output "ssl_certificate_id" {
  value = module.static_website.static_site_ssl_certificate_id
}
