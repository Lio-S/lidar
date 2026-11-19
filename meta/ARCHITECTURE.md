# Architecture — LiDAR Archéologie PACA

Vue d'ensemble de l'architecture technique du projet, à jour après les décisions Phase 0.
Justifications des choix → `DECISIONS.md`.

---

## Vue globale

```
╔══════════════════════════════════════════════════════════════════════╗
║  DEV LOCAL (WSL2 Ubuntu 24.04 — Legion Pro 7)                        ║
║                                                                      ║
║  ┌────────────────────────────────────────────────────────────────┐  ║
║  │  DevContainer (Docker — stage "dev")                          │  ║
║  │  Python 3.12 · uv · ruff · mypy · pytest                      │  ║
║  │  laspy · DVC · DuckDB · MLflow client · Prefect               │  ║
║  └───────────────────────────┬────────────────────────────────────┘  ║
║                              │ kubectl / minikube service             ║
║  ┌───────────────────────────▼────────────────────────────────────┐  ║
║  │  minikube (K8s local)                                         │  ║
║  │                                                                │  ║
║  │  namespace: mlflow              namespace: monitoring          │  ║
║  │  ├─ pod: mlflow-server :5000    ├─ pod: prometheus :9090      │  ║
║  │  └─ pod: postgres      :5432    └─ pod: grafana    :3000      │  ║
║  └────────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════╝
         │ git push                        │ dvc push
         ▼                                 ▼
╔══════════════════════╗    ╔══════════════════════════════════════════╗
║  GitHub              ║    ║  Google Drive (15 Go gratuit, sans CB)   ║
║  repo: lidar         ║    ║  dossier: lidar-dvc/                     ║
║  branch: main        ║    ║  contenu: dalles .laz · rasters MNT      ║
║                      ║    ║           features GeoTIFF               ║
║  ┌────────────────┐  ║    ╚══════════════════════════════════════════╝
║  │  GitHub Actions║  ║
║  │  CI pipeline   │  ║    ╔══════════════════════════════════════════╗
║  └────────────────┘  ║    ║  Terraform (IaC — sans CB)               ║
╚══════════════════════╝    ║  ├─ GitHub branch protection (main)      ║
                            ║  ├─ GitHub Actions secret: GDRIVE_CREDS  ║
                            ║  └─ GCS bucket (conditionnel, si GCP)    ║
                            ╚══════════════════════════════════════════╝

                              Phase 6 uniquement ↓

                            ╔══════════════════════════════════════════╗
                            ║  Hugging Face Spaces (gratuit, permanent)║
                            ║  app Gradio : raster → détections carte  ║
                            ║  modèle BentoML exporté sur HF Hub       ║
                            ╚══════════════════════════════════════════╝
```

---

## Pipeline CI/CD (GitHub Actions)

```
git push
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Job: ci  (ubuntu-24.04)                            │
│                                                     │
│  1. Checkout                                        │
│  2. Install uv                                      │
│  3. uv sync --extra dev --frozen  (via uv.lock)     │
│  4. ruff check .          ← lint                    │
│  5. ruff format --check . ← format                  │
│  6. mypy src/             ← types                   │
│  7. pytest                ← tests                   │
│  8. docker build --target dev  ← vérifie l'image    │
└─────────────────────────────────────────────────────┘

Note Phase 1 : migrer pytest vers docker run (fidélité env GDAL/laspy)
→ voir DECISIONS.md
```

---

## Flux de données

```
IGN OVH (source publique)
    │  urllib / requests
    ▼
data/raw/lidar/*.copc.laz   ← 54 dalles, 5.23 Go, bloc OQ LAMB93
    │  dvc add + dvc push
    ▼
Google Drive lidar-dvc/     ← versioning DVC (hash content-addressable)
    │
    ├─ Phase 1 → MNT 0.25m / 0.5m / 1m  (laspy + scipy)
    ├─ Phase 2 → Features morpho (slope, TPI, TRI, SVF…)
    ├─ Phase 3 → Dataset tabulaire ML + labels sites
    └─ Phase 4 → Patches 64×64 CNN

DuckDB (data/lidar_arch.duckdb)
    ├─ table dalles     : métadonnées dalles IGN (coords LAMB93, statut)
    ├─ table sites      : ground truth archéologique (WKT, époque, source)
    └─ table detections : prédictions ML (score, run_id MLflow, géométrie)
```

---

## Stack ML

```
Données (DVC + Google Drive)
    │
    ▼
Prefect (orchestration pipeline)
    ├─ Flow 1: download → preprocess → store
    ├─ Flow 2: features → train → evaluate
    └─ Flow 3: (Phase 6) predict → export

MLflow (tracking — minikube local)
    ├─ backend-store : PostgreSQL (pod K8s)
    ├─ artifact-store: /mlflow/artifacts (PVC local)
    └─ UI             : http://localhost:30500

Modèles (Phase 3 → 4)
    ├─ RandomForest / XGBoost / LightGBM  (sklearn/xgboost)
    ├─ ResNet18 / EfficientNet-B0          (PyTorch + torchvision)
    └─ Explicabilité SHAP
         ├─ TreeExplainer  (Phase 3 — features morpho)
         └─ DeepExplainer  (Phase 4 — pixels CNN)

Reports (commitées dans Git)
    ├─ reports/phase3/ : metrics.json · comparison.png · shap_summary.png
    └─ reports/phase4/ : metrics.json · comparison.png · shap_pixels.png
```

---

## Infrastructure Kubernetes (minikube)

```
Namespace: mlflow
┌─────────────────────────────────────────────────────┐
│  Deployment: postgres                               │
│  Image: postgres:16                                 │
│  PVC: 1 Gi  (données PostgreSQL)                    │
│  Service: ClusterIP :5432                           │
│  → DNS interne: postgres.mlflow.svc.cluster.local   │
├─────────────────────────────────────────────────────┤
│  Deployment: mlflow                                 │
│  Image: ghcr.io/mlflow/mlflow:v2.22.0               │
│  PVC: 5 Gi  (artifacts modèles)                     │
│  Service: NodePort 30500                            │
│  Cmd: mlflow server --backend-store-uri postgresql  │
│       --default-artifact-root /mlflow/artifacts     │
└─────────────────────────────────────────────────────┘

Namespace: monitoring
┌─────────────────────────────────────────────────────┐
│  Deployment: prometheus                             │
│  Image: prom/prometheus:v3.4.1                      │
│  PVC: 5 Gi  (séries temporelles, 30j rétention)     │
│  Service: NodePort 30900                            │
│  Scrape: pods annotés + mlflow.mlflow:5000          │
├─────────────────────────────────────────────────────┤
│  Deployment: grafana                                │
│  Image: grafana/grafana:12.0.1                      │
│  PVC: 1 Gi                                          │
│  Service: NodePort 30300                            │
│  Datasource: Prometheus (préconfigurée via ENV)     │
└─────────────────────────────────────────────────────┘

Accès local :
  minikube service mlflow     -n mlflow     → http://...30500
  minikube service grafana    -n monitoring → http://...30300
  minikube service prometheus -n monitoring → http://...30900
```

---

## Terraform

```
terraform/
├── versions.tf   — providers: github ~6.0 + google ~6.0
├── variables.tf  — github_token (sensitive), github_owner, github_repo
│                   gdrive_credentials_data (sensitive)
│                   project_id (optionnel, défaut "")
├── main.tf       — provider github
│                   github_branch_protection.main (CI doit passer)
│                   github_actions_secret.gdrive_credentials
├── gcs.tf        — google_storage_bucket.dvc_remote
│                   count = project_id != "" ? 1 : 0  ← conditionnel
│                   activé sans modifier le code si GCP dispo
└── outputs.tf    — github_repo, dvc_bucket_url

Usage sans CB :
  echo 'github_token = "ghp_..."'      > terraform.tfvars
  echo 'github_owner = "ton-login"'   >> terraform.tfvars
  echo 'gdrive_credentials_data = ""' >> terraform.tfvars
  terraform init && terraform apply
```

---

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `pyproject.toml` | Dépendances uv + config ruff/mypy/pytest |
| `uv.lock` | Lockfile déterministe (214 packages) |
| `Dockerfile` | Multi-stage : base → dev (devcontainer) → prod (Phase 6) |
| `.devcontainer/devcontainer.json` | Config VS Code Dev Container |
| `.github/workflows/ci.yml` | CI : lint → types → tests → docker build |
| `.dvc/config` | Remote DVC → Google Drive (GDRIVE_FOLDER_ID à renseigner) |
| `src/lidar_arch/db/schema.py` | Création tables DuckDB |
| `terraform/` | IaC GitHub + GCS conditionnel |
| `k8s/mlflow/` | Manifests MLflow + PostgreSQL (minikube) |
| `k8s/monitoring/` | Manifests Prometheus + Grafana (minikube) |
| `meta/DECISIONS.md` | Justifications de tous les choix techniques |
| `meta/ROADMAP.md` | Tâches par phase avec statut |
