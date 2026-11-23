# Bucket GCS pour remote DVC — configuration Terraform séparée, NON appliquée par défaut
# (pas de compte GCP avec facturation, voir meta/DECISIONS.md).
# Activation : cd terraform/gcs && terraform init && terraform apply -var project_id=<id>

resource "google_storage_bucket" "dvc_remote" {
  name          = "${var.project_id}-dvc"
  location      = var.region
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 3
    }
    action {
      type = "Delete"
    }
  }
}
