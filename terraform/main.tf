provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Bucket GCS — remote DVC pour les dalles LiDAR et les rasters dérivés
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
