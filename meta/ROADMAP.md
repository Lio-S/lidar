# Roadmap — LiDAR Archéologie PACA

Feuille de route par phases. Chaque phase a un critère de sortie clair.
Mise à jour au fil de l'eau — versionné dans Git.

---

## Phase 0 : Setup ⬜

**Objectif** : environnement de développement opérationnel, CI/CD fonctionnelle.

### Tâches
- [x] Créer repo GitHub `lidar`
- [x] Pousser les fichiers `.md` (CLAUDE.md, README, ROADMAP, THEORY, DATA, DECISIONS)
- [x] Initialiser projet uv (`uv init`, `pyproject.toml`, Python 3.12)
- [x] Configurer ruff + mypy + pytest dans `pyproject.toml`
- [x] Installer WSL2 Ubuntu + uv sur Legion Pro 7
- [x] Installer Claude Code (CC)
- [x] Installer Docker Engine dans WSL2
- [x] Configurer Dev Container (Dockerfile multi-stage + .devcontainer/)
- [ ] Configurer GitHub Actions CI (`ruff → mypy → pytest → build`)
- [ ] Créer compte GCP + activer crédits 300$
- [ ] Créer bucket GCS pour DVC remote
- [ ] Initialiser DVC (`dvc init`, remote GCS)
- [ ] Setup minikube local
- [ ] Installer Terraform + écrire infra GCP de base
- [ ] Déployer MLflow sur K8s local (minikube)
- [ ] Initialiser DuckDB schema (`dalles`, `sites`, `detections`)

### Critère de sortie
> `uv run pytest` passe en vert, CI/CD GitHub Actions verte, MLflow accessible sur minikube, DVC remote GCS opérationnel.

---

## Phase 1 : Data ⬜

**Objectif** : pipeline de téléchargement et traitement LiDAR opérationnel sur la zone Saint-Blaise.

### Tâches
- [x] Télécharger les dalles IGN LiDAR HD zone Saint-Blaise (**54 dalles, 5.23 Go**)
- [ ] Pousser les dalles vers GCS via DVC
- [ ] Écrire `src/lidar_arch/data/download.py` — téléchargement automatisé IGN
- [x] Résoudre installation PDAL — `pdal` apt (PPA ubuntugis-unstable) + CLI subprocess
- [x] Tester re-classification CSF → abandonné (résultat similaire à IGN, trous inland)
- [ ] Générer MNT multi-échelle (0.25m / 0.5m / 1m) depuis classification IGN (Sol classe 2 + classe 65) — pleine étendue
- [ ] Stocker métadonnées dalles dans DuckDB (table `dalles`)
- [ ] Écrire tests unitaires `tests/test_data.py`
- [ ] Visualiser MNT Saint-Blaise dans QGIS — vérification visuelle
- [ ] Identifier zones archéologiques connues → table `sites` DuckDB

### Critère de sortie
> MNT Saint-Blaise généré, visualisé et validé visuellement. Dalles dans GCS, métadonnées dans DuckDB.

---

## Phase 2 : Features ⬜

**Objectif** : calcul des indicateurs morphologiques pertinents pour la détection archéologique.

### Tâches
- [ ] Écrire `src/lidar_arch/features/morphology.py` :
  - [ ] Pente (slope)
  - [ ] Aspect
  - [ ] Courbure (curvature)
  - [ ] TPI (Topographic Position Index) — multi-échelles
  - [ ] TRI (Terrain Ruggedness Index)
  - [ ] Sky View Factor (SVF)
  - [ ] Openness (positive + negative)
- [ ] Stocker rasters dérivés (GeoTIFF) → GCS via DVC
- [ ] Analyse exploratoire des features (notebook `01_exploration.ipynb`)
- [ ] Sélection features pertinentes (corrélation, importance)
- [ ] Écrire tests unitaires `tests/test_features.py`

### Critère de sortie
> 7+ indicateurs morphologiques calculés, stockés, visualisés. Features sélectionnées et justifiées dans DECISIONS.md.

---

## Phase 3 : Baseline ML ⬜

**Objectif** : premiers modèles ML classiques, comparaison trackée dans MLflow.

### Tâches
- [ ] Préparer dataset (features tabulaires + labels sites connus)
- [ ] Gérer déséquilibre de classes (SMOTE ou class weights)
- [ ] Écrire `src/lidar_arch/models/train.py` — pipeline entraînement générique
- [ ] Entraîner et logger dans MLflow :
  - [ ] RandomForest
  - [ ] XGBoost
  - [ ] LightGBM
- [ ] Métriques : F1, AUC-PR, AUC-ROC
- [ ] Rapport Evidently (qualité données + modèle)
- [ ] Analyse erreurs (faux positifs/négatifs sur carte)
- [ ] Écrire tests `tests/test_models.py`
- [ ] Documenter résultats dans `reports/`

### Critère de sortie
> 3 modèles comparés dans MLflow. Meilleur modèle baseline identifié avec métriques justifiées.

---

## Phase 4 : Deep Learning ⬜

**Objectif** : améliorer la détection avec des CNN sur patches raster.

### Tâches
- [ ] Générer dataset patches 64×64 pixels (MNT + features)
- [ ] Écrire `src/lidar_arch/models/dataset.py` — PyTorch Dataset
- [ ] Fine-tuner ResNet18 (weights ImageNet)
- [ ] Fine-tuner EfficientNet-B0 (weights ImageNet)
- [ ] Logger dans MLflow (comparaison avec baseline Phase 3)
- [ ] Analyser saliency maps (zones activées par le CNN)
- [ ] Évaluer sur zone Miouvin (généralisation)

### Critère de sortie
> CNN meilleur que baseline ML sur AUC-PR. Comparaison complète dans MLflow.

---

## Phase 5 : Avancé ⬜

**Objectif** : détection directement sur nuages de points 3D (si données suffisantes).

> ⚠️ Phase conditionnelle — à évaluer après Phase 4 selon volume de données annotées disponibles.

### Tâches
- [ ] Évaluer volume données annotées disponibles
- [ ] Préparer dataset nuages de points (patches 3D)
- [ ] Implémenter PointNet++ (PyTorch)
- [ ] Entraînement sur GPU RTX 5070 Ti
- [ ] Comparer avec CNN Phase 4 dans MLflow

### Critère de sortie
> PointNet++ entraîné et comparé. Décision documentée dans DECISIONS.md.

---

## Phase 6 : Serving ⬜

**Objectif** : déploiement du meilleur modèle en production sur GCP.

### Tâches
- [ ] Packager meilleur modèle avec BentoML
- [ ] Écrire API FastAPI (`/predict` endpoint)
- [ ] Ajouter stage `prod` au Dockerfile (base existante en Phase 0 + BentoML serving)
- [ ] Déployer sur GKE (Google Kubernetes Engine)
- [ ] Terraform infra GCP complète (GKE, GCS, PostgreSQL/PostGIS, MLflow)
- [ ] Migrer DuckDB → PostGIS pour la prod
- [ ] Setup Prometheus + Grafana (monitoring)
- [ ] Tests de charge

### Critère de sortie
> API accessible publiquement sur GCP, monitoring actif, infra 100% Terraform.

---

## Phase 7 : Portfolio ⬜

**Objectif** : valoriser le projet pour la recherche d'emploi.

### Tâches
- [ ] README complet avec démo GIF/screenshots
- [ ] Notebook de démonstration interactif
- [ ] Article Medium/blog (FR + EN) sur l'approche
- [ ] Poster/présentation pour communauté CAA ou open-archaeo
- [ ] Mise à jour CV et LinkedIn avec le projet

### Critère de sortie
> Projet présentable en entretien, article publié, communauté contactée.

---

## Statuts
- ⬜ Non démarré
- 🔄 En cours
- ✅ Terminé
- ⏸️ Bloqué

## Journal
| Date | Phase | Action |
|------|-------|--------|
| 2026-04 | 0 | Initialisation roadmap et fichiers meta/ |
| 2026-05 | 1 | Téléchargement 54 dalles IGN LiDAR HD (5.23 Go, bloc OQ) |
| 2026-05 | 0 | Nettoyage redondances meta/ + dossier `meta/` |
