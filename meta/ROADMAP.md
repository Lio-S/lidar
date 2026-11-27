# Roadmap — LiDAR Archéologie PACA

Feuille de route par phases. Chaque phase a un critère de sortie clair.
Mise à jour au fil de l'eau — versionné dans Git.

---

## Phase 0 : Setup ✅

**Objectif** : environnement de développement opérationnel, CI/CD fonctionnelle.

### Tâches
- [x] Créer repo GitHub `lidar`
- [x] Pousser les fichiers `.md` (CLAUDE.md, README, ROADMAP, THEORY, DATA, DECISIONS)
- [x] Initialiser projet uv (`uv init`, `pyproject.toml`, Python 3.12)
- [x] Configurer ruff + mypy + pytest dans `pyproject.toml`
- [x] Installer WSL2 Ubuntu + uv 
- [x] Installer Claude Code (CC)
- [x] Installer Docker Engine dans WSL2
- [x] Configurer Dev Container (Dockerfile multi-stage + .devcontainer/)
- [x] Configurer GitHub Actions CI (`ruff → mypy → pytest → build`)
- [x] Créer un dossier Google Drive `lidar/` + noter son ID dans terraform/terraform.tfvars
- [x] Renseigner `GDRIVE_FOLDER_ID` + `gdrive_client_id/secret` dans `.dvc/config`
- [x] Créer OAuth app GCP (Google Drive API, type "Application de bureau") → télécharger JSON credentials
- [x] Ajouter `votreAdresse@gmail.com` comme utilisateur de test dans GCP → OAuth consent screen → Test users (⚠️ requis tant que l'app est en mode "Test")
- [x] `dvc init` (`.dvc/config` versionné, `data/raw/lidar.dvc` tracké, push validé)
- [x] `dvc push` — 5.23 Go `data/raw/lidar/` envoyés sur Google Drive (dossier public en lecture)
- [x] Setup minikube local (outils dans le Dev Container, driver docker via socket WSL2)
- [x] Écrire infra Terraform GitHub + GCS conditionnel (`terraform/`)
- [x] Créer un GitHub PAT (scope : `repo`) + renseigner `terraform/terraform.tfvars` (⚠️ expire 2027-03-19)
- [x] Installer Terraform CLI + `terraform apply` — branch protection `main` (PR + check `ci`) + secret `GDRIVE_CREDENTIALS_DATA` (compte de service `dvc-ci`)
- [x] Écrire manifests K8s MLflow (`k8s/mlflow/`)
- [x] Déployer MLflow sur minikube (`kubectl apply`) — PostgreSQL backend, métriques Prometheus
- [x] Écrire manifests K8s Prometheus + Grafana (`k8s/monitoring/`)
- [x] Déployer Prometheus + Grafana sur minikube — accès via `kubectl port-forward` (5000 / 3000 / 9090)
- [x] Écrire schéma DuckDB (`src/lidar_arch/db/schema.py`)
- [x] Initialiser la base DuckDB (`python -m lidar_arch.db.schema`) — tables dalles, sites, detections

### Critère de sortie
> `uv run pytest` passe en vert, CI/CD GitHub Actions verte, MLflow + Grafana accessibles sur minikube, DVC remote Google Drive opérationnel.

---

## Phase 1 : Data 🔄

**Objectif** : pipeline de téléchargement et traitement LiDAR opérationnel sur la zone Saint-Blaise.

### Tâches
- [x] Télécharger les dalles IGN LiDAR HD zone Saint-Blaise (**54 dalles, 5.23 Go**)
- [x] Pousser les dalles vers Google Drive via DVC (`dvc push`)
- [x] Écrire `src/lidar_arch/data/download.py` — téléchargement automatisé IGN
- [x] Tester re-classification CSF → abandonné (résultat similaire à IGN, trous inland, classification IGN conservée)
- [x] Générer MNT de référence 0.5m depuis classification IGN (Sol classe 2 + classe 65) — pleine étendue (`src/lidar_arch/data/dtm.py`, TIN, `dvc repro` : 54 dalles, 26 min)
- [ ] Masque d'exclusion bâti — appliqué au dataset (Phase 3), pas au MNT (voir DECISIONS.md) :
  - [x] Période de vol des dalles (heure GPS des points) : 2021-06-13 → 2022-09-01
  - [ ] Inventaire BD TOPO 2023-03-15 sur l'emprise (`explore/02_bdtopo_inventaire.py`) + Monuments historiques des communes couvertes
  - [x] Vérifier la présence de la classe 67 (« divers – bâtis ») : 154 701 points sur les 54 dalles, aucun autour du château de l'Hauture
  - [ ] Contrôle QGIS : oppidum, chapelle Saint-Blaise, château de l'Hauture, remparts de Saint-Mitre
  - [ ] Couche de protection (monuments, vestiges) prioritaire sur l'exclusion
  - [ ] Calibrer le tampon (rugosité du MNT en fonction de la distance au bâti)
- [x] Stocker métadonnées dalles dans DuckDB (table `dalles`) — `python -m lidar_arch.db.dalles` : 54 dalles (emprise, points par classe, densité sol, % nodata MNT)
- [x] Écrire tests unitaires Phase 1 — `test_data.py` (MNT), `test_dalles.py` (table dalles), `test_download.py` (réseau simulé)
- [ ] Migrer CI : exécuter `pytest` dans le container Docker (pas sur le runner) — voir DECISIONS.md
- [x] Visualiser MNT Saint-Blaise dans QGIS — vérification visuelle (raccords, rive de l'étang, oppidum lisible avec RVT)
- [ ] Identifier zones archéologiques connues → table `sites` DuckDB

### Critère de sortie
> MNT de référence 0.5m Saint-Blaise généré, visualisé et validé visuellement. Dalles sur Google Drive (DVC), métadonnées dans DuckDB.

---

## Phase 2 : Features ⬜

**Objectif** : calcul des indicateurs morphologiques pertinents pour la détection archéologique.

### Tâches
- [ ] Rééchantillonner le MNT de référence aux échelles retenues pour les indicateurs (choix justifié dans DECISIONS.md)
- [ ] Écrire `src/lidar_arch/features/morphology.py` :
  - [ ] Pente (slope)
  - [ ] Aspect
  - [ ] Courbure (curvature)
  - [ ] TPI (Topographic Position Index) — multi-échelles
  - [ ] TRI (Terrain Ruggedness Index)
  - [ ] Sky View Factor (SVF)
  - [ ] Openness (positive + negative)
- [ ] Stocker rasters dérivés (GeoTIFF) → Google Drive via DVC
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
- [ ] Explicabilité SHAP (`TreeExplainer`) — importance des features morphologiques par détection
- [ ] Écrire tests `tests/test_models.py`
- [ ] Générer et commiter dans `reports/phase3/` :
  - [ ] `metrics.json` — F1 / AUC-PR / AUC-ROC des 3 modèles
  - [ ] `comparison.png` — graphique comparatif des modèles
  - [ ] `shap_summary.png` — SHAP summary plot (features les plus décisives)
  - [ ] `errors_map.png` — carte des faux positifs/négatifs sur Saint-Blaise
  - [ ] `results.md` — synthèse narrative lisible sur GitHub

### Critère de sortie
> 3 modèles comparés dans MLflow. Meilleur modèle baseline identifié avec métriques justifiées. Résultats visibles sur GitHub dans `reports/phase3/`.

---

## Phase 4 : Deep Learning ⬜

**Objectif** : améliorer la détection avec des CNN sur patches raster.

### Tâches
- [ ] Générer dataset patches 64×64 pixels (MNT + features)
- [ ] Écrire `src/lidar_arch/models/dataset.py` — PyTorch Dataset
- [ ] Fine-tuner ResNet18 (weights ImageNet)
- [ ] Fine-tuner EfficientNet-B0 (weights ImageNet)
- [ ] Logger dans MLflow (comparaison avec baseline Phase 3)
- [ ] Explicabilité SHAP (`DeepExplainer`) — zones de pixels décisives par détection
- [ ] Générer et commiter dans `reports/phase4/` :
  - [ ] `metrics.json` — F1 / AUC-PR des CNN vs baseline Phase 3
  - [ ] `comparison.png` — courbes apprentissage + comparaison ML vs DL
  - [ ] `shap_pixels.png` — SHAP pixel importance sur Saint-Blaise
  - [ ] `results.md` — synthèse narrative lisible sur GitHub

### Critère de sortie
> CNN meilleur que baseline ML sur AUC-PR. Comparaison complète dans MLflow. Résultats visibles sur GitHub dans `reports/phase4/`.

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

**Objectif** : démo permanente et accessible, sans infrastructure complexe.

> Stratégie : Hugging Face Spaces (démo Gradio, gratuit permanent) + Google Drive via DVC (données, déjà en place). Pas de VPS, pas de PostGIS en prod. Voir DECISIONS.md.

### Tâches
- [ ] Packager le meilleur modèle avec BentoML → export vers HF Hub
- [ ] Ajouter stage `prod` au Dockerfile (image minimale pour serving)
- [ ] Écrire app Gradio (`app.py`) — upload raster → prédiction → carte des détections
- [ ] Déployer sur Hugging Face Spaces (push Git → déploiement automatique)
- [ ] Ajouter lien HF Spaces + GIF démo dans le README

### Critère de sortie
> Démo Gradio accessible sur Hugging Face Spaces, lien dans le README. Aucune dépendance aux crédits GCP de 90 jours.

---

## Phase 7 : Diffusion ⬜

**Objectif** : documenter et partager l'approche et les résultats.

### Tâches
- [ ] README complet avec lien HF Spaces + GIF démo
- [ ] Article Medium/blog (FR + EN) sur l'approche
- [ ] Poster/présentation pour communauté CAA ou open-archaeo

### Critère de sortie
> README complet, article publié, communauté contactée.

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
| 2026-06 | 0 | CI build Docker, DVC config, DuckDB schema, Terraform GCP, K8s MLflow manifests |
| 2026-11 | 0 | Terraform migré GitHub (sans GCP), DVC remote → Google Drive, K8s monitoring (Prometheus 30j + Grafana), ARCHITECTURE.md, terraform.tfvars renseigné, PAT créé |
| 2026-11 | 0 | OAuth GCP créé (Drive API, App de bureau), credentials dans .dvc/config — bloqué 403 : ajouter lionelsergent@gmail.com dans GCP Test users (résolu) |
| 2026-11 | 1 | dvc push réussi — 5.23 Go raw LiDAR sur Google Drive (dossier public en lecture) |
| 2026-11 | 0 | Outils infra dans le Dev Container (Terraform, kubectl, minikube, gh), minikube démarré, `terraform apply` (branch protection + secret SA), GCS séparé dans `terraform/gcs/`, cache Docker CI, MLflow + Prometheus + Grafana déployés sur minikube (fix psycopg2, RBAC, datasource) |
| 2026-11 | 1-2 | Multi-échelle MNT déplacé en Phase 2 : Phase 1 = MNT de référence 0.5m seul (voir DECISIONS.md) |
| 2026-11 | 0 | Dev Container non-root (`ubuntu`, uid 1000) : fin des fichiers root dans le workspace (commit cassé), accès socket Docker via entrypoint, redéploiement K8s auto au démarrage (voir DECISIONS.md) |
| 2026-11 | 1 | MNT de référence 0.5m généré (TIN des points sol IGN, tampon 20 m, masque arête max 20 m, aperçus GeoTIFF), étape `dtm` dans `dvc.yaml`, validé dans QGIS (RVT) ; masque bâti prévu pour le dataset (voir DECISIONS.md) |
| 2026-11 | 1 | Table `dalles` remplie (54 dalles) : schéma révisé, id stable `XXXX×10⁴+YYYY`, upsert idempotent, hors pipeline DVC (voir DECISIONS.md) |
| 2026-11 | 1 | `download.py` : logger, dossier `RAW_LIDAR_DIR`, écriture `.part` puis renommage (reprise sûre), code de sortie 1 si échec ; tests réseau simulé |
| 2026-11 | 1 | Masque bâti revu : classe 6 seule inadaptée (château de l'Hauture masqué, courts de tennis non masqués) ; BD TOPO 2023-03-15 (première édition après le vol) + couche de protection des monuments ; inventaire avant code (voir DECISIONS.md) |
