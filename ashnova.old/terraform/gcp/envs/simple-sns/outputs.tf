output "project_id" {
  value = module.simple_sns.simple_sns_project_id
}

output "region" {
  value = module.simple_sns.simple_sns_region
}

output "images_bucket" {
  value = module.simple_sns.simple_sns_images_bucket
}

output "frontend_bucket" {
  value = module.simple_sns.simple_sns_frontend_bucket
}

output "frontend_url" {
  value = module.simple_sns.simple_sns_frontend_url
}

output "create_post_url" {
  value = module.simple_sns.simple_sns_create_post_url
}

output "list_posts_url" {
  value = module.simple_sns.simple_sns_list_posts_url
}

output "delete_post_url" {
  value = module.simple_sns.simple_sns_delete_post_url
}

output "get_upload_urls_url" {
  value = module.simple_sns.simple_sns_get_upload_urls_url
}

output "profile_url" {
  value = module.simple_sns.simple_sns_profile_url
}

output "static_site_bucket_name" {
  value = module.simple_sns.static_site_bucket_name
}

output "static_site_load_balancer_ip" {
  value = module.simple_sns.static_site_load_balancer_ip
}

output "static_site_website_url" {
  value = module.simple_sns.static_site_website_url
}
