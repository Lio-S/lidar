output "github_repo" {
  description = "Dépôt GitHub géré par Terraform"
  value       = "${var.github_owner}/${var.github_repo}"
}
