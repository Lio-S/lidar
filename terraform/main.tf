provider "github" {
  token = var.github_token
  owner = var.github_owner
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Protection de la branche main — le job CI doit passer avant tout merge
resource "github_branch_protection" "main" {
  repository_id = var.github_repo
  pattern       = "main"

  required_status_checks {
    strict   = true               # la branche doit être à jour avec main avant le merge
    contexts = ["CI / ci"]        # nom du job dans .github/workflows/ci.yml
  }

  required_pull_request_reviews {
    dismiss_stale_reviews = true  # invalide l'approbation si de nouveaux commits sont poussés
  }

  force_push_allowed = false
}

# Secret GitHub Actions — credentials DVC Google Drive
resource "github_actions_secret" "gdrive_credentials" {
  repository      = var.github_repo
  secret_name     = "GDRIVE_CREDENTIALS_DATA"
  plaintext_value = var.gdrive_credentials_data
}
