output "github_repo" {
  description = "Dépôt GitHub géré par Terraform"
  value       = "${var.github_owner}/${var.github_repo}"
}

output "dvc_bucket_url" {
  description = "URL GCS à renseigner dans .dvc/config (vide si project_id non fourni)"
  value       = length(google_storage_bucket.dvc_remote) > 0 ? "gs://${google_storage_bucket.dvc_remote[0].name}/lidar" : "non activé — renseigner project_id"
}
