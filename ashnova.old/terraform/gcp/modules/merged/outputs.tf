output "simple_sns_project_id" {
  value = var.enable_simple_sns ? module.simple_sns[0].project_id : null
}

output "simple_sns_region" {
  value = var.enable_simple_sns ? module.simple_sns[0].region : null
}

output "simple_sns_images_bucket" {
  value = var.enable_simple_sns ? module.simple_sns[0].images_bucket : null
}

output "simple_sns_frontend_bucket" {
  value = var.enable_simple_sns ? module.simple_sns[0].frontend_bucket : null
}

output "simple_sns_frontend_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].frontend_url : null
}

output "simple_sns_create_post_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].create_post_url : null
}

output "simple_sns_list_posts_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].list_posts_url : null
}

output "simple_sns_delete_post_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].delete_post_url : null
}

output "simple_sns_get_upload_urls_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].get_upload_urls_url : null
}

output "simple_sns_profile_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].profile_url : null
}

output "static_site_bucket_name" {
  value = var.enable_static_site ? module.static_website[0].bucket_name : null
}

output "static_site_bucket_url" {
  value = var.enable_static_site ? module.static_website[0].bucket_url : null
}

output "static_site_bucket_website_url" {
  value = var.enable_static_site ? module.static_website[0].bucket_website_url : null
}

output "static_site_load_balancer_ip" {
  value = var.enable_static_site ? module.static_website[0].load_balancer_ip : null
}

output "static_site_website_url" {
  value = var.enable_static_site ? module.static_website[0].website_url : null
}

output "static_site_dns_configuration" {
  value = var.enable_static_site ? module.static_website[0].dns_configuration : null
}

output "static_site_custom_domain" {
  value = var.enable_static_site ? module.static_website[0].custom_domain : null
}

output "static_site_ssl_certificate_id" {
  value = var.enable_static_site ? module.static_website[0].ssl_certificate_id : null
}
