# --- GCP ---
variable "project_id" {
  description = "GCP project ID (requiert un compte GCP avec facturation)"
  type        = string
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
