# Bucket GCS pour remote DVC — activé uniquement si project_id est fourni.
# Sans compte GCP, laisser project_id = "" dans terraform.tfvars → ce fichier est ignoré.
# Quand GCP disponible : renseigner project_id et relancer terraform apply.

resource "google_storage_bucket" "dvc_remote" {
  count         = var.project_id != "" ? 1 : 0
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
