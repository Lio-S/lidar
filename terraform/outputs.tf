output "dvc_bucket_url" {
  description = "URL GCS à renseigner dans .dvc/config"
  value       = "gs://${google_storage_bucket.dvc_remote.name}/lidar"
}
