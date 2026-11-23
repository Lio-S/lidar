# --- GitHub ---
variable "github_token" {
  description = "GitHub Personal Access Token (scope : repo)"
  type        = string
  sensitive   = true # ne s'affiche pas dans les logs terraform
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
  description = "Clé JSON du compte de service dvc-ci (lecture Drive DVC en CI) — via TF_VAR_, jamais dans tfvars"
  type        = string
  sensitive   = true

  validation {
    condition     = can(jsondecode(var.gdrive_credentials_data).client_email)
    error_message = "Clé JSON de compte de service attendue (champ client_email). Vérifier TF_VAR_gdrive_credentials_data."
  }
}
