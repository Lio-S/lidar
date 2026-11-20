# LiDAR Archéologie PACA

Détection automatique de structures archéologiques sur données IGN LiDAR HD
par apprentissage automatique — zone d'étude : Bouches-du-Rhône (PACA, France).

## Objectif

Développer un pipeline ML capable de détecter des anomalies de relief
caractéristiques de structures archéologiques (fossés, remparts, tumuli, villae)
à partir des nuages de points LiDAR haute densité de l'IGN.

## Zone d'étude

- **Site v1** : Saint-Blaise (Saint-Mitre-les-Remparts, 13) — remparts massifs, ground truth solide
- **Données** : IGN LiDAR HD, résolution 10 pts/m², open data

## Pipeline

```
Dalles .laz IGN → Filtrage végétation → MNT → Indicateurs morphologiques → ML → Détection
```

## Stack

Python 3.12 · uv · laspy · rasterio · scikit-learn · XGBoost · PyTorch · MLflow · DVC · Prefect · BentoML

→ Architecture complète (diagrammes, K8s, Terraform, flux données) : [`meta/ARCHITECTURE.md`](meta/ARCHITECTURE.md)

## Données

Les données LiDAR sont téléchargeables gratuitement sur :
https://geoservices.ign.fr/lidarhd

Non incluses dans ce dépôt (trop volumineuses) — voir `DATA.md` pour les instructions.

## Démarrage rapide

```bash
git clone https://github.com/Lio-S/lidar
cd lidar
```

Ouvrir dans VS Code → **Reopen in Container** (Dev Container requis).

**Récupérer les données LiDAR (5.23 Go, dossier Drive public en lecture) :**
```bash
dvc pull          # dans le terminal du container
```

**Lancer le pipeline :**
```bash
dvc repro         # génère les MNT et features depuis les données brutes
uv run pytest     # vérifie l'installation
```

> Contributeur (push de données) : demander l'accès Éditeur au dossier Drive,
> puis configurer ses propres credentials OAuth — voir [`meta/DATA.md`](meta/DATA.md).

## Structure

```
├── data/           # Données (non versionnées, gérées par DVC → Google Drive)
├── meta/           # Documentation (ARCHITECTURE.md, ROADMAP.md, DECISIONS.md)
├── notebooks/      # Exploration et prototypage
├── src/            # Code source
├── k8s/            # Manifests Kubernetes (MLflow, Prometheus, Grafana)
├── terraform/      # Infrastructure as Code (GitHub + GCS conditionnel)
├── configs/        # Hyperparamètres
└── reports/        # Résultats et figures (commitées dans Git)
```

## Références

- [IGN LiDAR HD](https://geoservices.ign.fr/lidarhd)
- [open-archaeo.info](https://open-archaeo.info)
- [Computer Applications in Archaeology (CAA)](https://caa-international.org)

## Licence

MIT
