provider "github" {
  token = var.github_token
  owner = var.github_owner
}

# Protection de la branche main — le job CI doit passer avant tout merge
resource "github_branch_protection" "main" {
  repository_id  = var.github_repo
  pattern        = "main"
  enforce_admins = true # les règles s'appliquent aussi au propriétaire (sinon contournables)

  required_status_checks {
    strict   = true   # la branche doit être à jour avec main avant le merge
    contexts = ["ci"] # id du job dans .github/workflows/ci.yml (≠ "CI / ci" affiché dans l'UI)
  }

  # PR obligatoire (pas de push direct sur main), sans approbation : GitHub interdit d'approuver sa propre PR
  required_pull_request_reviews {
    required_approving_review_count = 0
  }

  allows_force_pushes = false
}

# Secret GitHub Actions — credentials DVC Google Drive
resource "github_actions_secret" "gdrive_credentials" {
  repository  = var.github_repo
  secret_name = "GDRIVE_CREDENTIALS_DATA"
  value       = var.gdrive_credentials_data
}
