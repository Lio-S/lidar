# Projet LiDAR Archéologie - Contexte Claude Code

## Objectif
Détection automatique de structures archéologiques sur données IGN LiDAR HD via ML.

**Périmètre v1** : Saint-Blaise (Saint-Mitre-les-Remparts, 13).
Élargissements possibles en v2 : Miouvin, Abri Cornille.

→ Justifications dans `meta/DECISIONS.md`.

## Stack technique

### Environnement
- **OS** : Windows 11 + WSL2 Ubuntu 24.04
- **GPU** : NVIDIA RTX 5070 Ti 12Go (CUDA)
- **Python** : 3.12
- **Dépendances** : uv (pas de conda/venv)

### Qualité code
- **ruff** : lint + format
- **mypy** : vérification types
- **pytest + pytest-cov** : tests

### MLOps
- **DVC** : versioning données (remote GCS)
- **MLflow** : tracking expériences
- **Evidently** : métriques qualité, drift
- **BentoML** : serving modèle
- **Prefect** : orchestration pipeline

### Base de données
- **DuckDB** : métadonnées local
- **PostGIS** : prod sur GCP

Tables : `dalles`, `sites`, `detections`. Backend MLflow : PostgreSQL.

### Infrastructure
- **Docker** + **Kubernetes** (minikube → GKE)
- **Terraform** : IaC GCP
- **GitHub Actions** : CI/CD
- **Cloud** : GCP
- **Monitoring** : Prometheus + Grafana

→ Détails librairies : `meta/GLOSSARY.md`.
→ Justifications choix : `meta/DECISIONS.md`.

## Structure du projet
```
lidar-archeologie/
├── CLAUDE.md               ← contexte Claude Code (racine obligatoire)
├── README.md               ← documentation publique (racine obligatoire)
├── pyproject.toml          ← uv + ruff + mypy + pytest
├── meta/
│   ├── ROADMAP.md          ← feuille de route par phases
│   ├── THEORY.md           ← concepts scientifiques
│   ├── DATA.md             ← sources et conventions données
│   ├── DECISIONS.md        ← choix techniques justifiés
│   └── GLOSSARY.md         ← définitions courtes
├── .github/workflows/      ← GitHub Actions CI/CD
├── docker/                 ← Dockerfile + Dockerfile.serve
├── terraform/              ← infrastructure GCP
├── k8s/                    ← manifests Kubernetes
├── data/                   ← raw / processed / annotations (DVC)
├── notebooks/              ← exploration uniquement
├── src/lidar_arch/         ← data / features / models / visualization
├── tests/                  ← pytest
├── configs/                ← hyperparamètres YAML
└── reports/                ← figures, résultats MLflow
```

## Conventions de code
- PEP8 strict (ruff)
- Type hints sur fonctions publiques (mypy)
- Docstrings NumPy style
- Opérations vectorielles numpy/pandas (pas de boucles Python)
- Fonctions courtes, nommage explicite
- Pas de magic numbers → `src/lidar_arch/constants.py`
- Notebooks : exploration uniquement → convertir en `.py` dès validation
