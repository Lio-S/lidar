# --- GitHub ---
variable "github_token" {
  description = "GitHub Personal Access Token (scopes : repo, admin:repo_hook)"
  type        = string
  sensitive   = true  # ne s'affiche pas dans les logs terraform
}

variable "github_owner" {
  description = "Nom d'utilisateur ou organisation GitHub"
  type        = string
}

variable "github_repo" {
  description = "Nom du dépôt GitHub"
  type        = string
  default     = "lidar"
}

variable "gdrive_credentials_data" {
  description = "Contenu JSON du token OAuth Google Drive (généré par dvc remote modify)"
  type        = string
  sensitive   = true
}

# --- GCP (optionnel — laisser vide pour ignorer le bucket GCS) ---
variable "project_id" {
  description = "GCP project ID (laisser vide si pas de compte GCP)"
  type        = string
  default     = ""
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west9"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "europe-west9-a"
}
