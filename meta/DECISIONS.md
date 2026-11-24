# Décisions techniques

## 2026-11 — MNT de référence : interpolation TIN linéaire, dalle par dalle avec tampon

**Décision** : le MNT 0.5m est interpolé par TIN linéaire (triangulation de Delaunay, `scipy`) des points sol IGN (classes 2 + 65), dalle par dalle, puis assemblé en mosaïque virtuelle `.vrt`. Code : `src/lidar_arch/data/dtm.py`, paramètres dans `src/lidar_arch/constants.py`.

**Pourquoi TIN plutôt que binning + remplissage ou IDW (PDAL)** :
- Méthode de référence des MNT IGN (RGE ALTI) : résultat comparable aux produits officiels
- Interpolation exacte entre points mesurés → préserve les ruptures de pente (talus, remparts, fossés)
- Comble naturellement les trous sous végétation, sans lissage arbitraire (`fillnodata`) ni artefacts en « bulles » (IDW)
- Pas de binaire PDAL à ajouter à l'image : `scipy` + `rasterio` (wheels avec GDAL intégré)

**Paramètres** :
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| Résolution | 0.5 m | Décision 2026-11 (MNT de référence) |
| Tampon dalles voisines | 20 m | Triangulation continue aux raccords → pas de couture visible ; lecture spatiale COPC (seule la bande utile est lue) |
| Décimation | moyenne par cellule de 0.5 m | 10-13 pts sol/m² → ~4 pts/m² : mémoire de la triangulation ÷ ~3 (14 M → ~4,5 M points par dalle), bruit de mesure réduit, sans perte à la résolution du MNT |
| Distance max d'interpolation | 10 m | Au-delà → nodata : évite des triangles géants sur l'Étang de Berre et les grands trous ; un trou < 10 m (sous un arbre) reste interpolé |
| Nodata | -9999 | Convention GDAL/QGIS |

**Mosaïque `.vrt` plutôt qu'un GeoTIFF unique** : 54 km² à 0.5 m = ~216 M pixels ; le `.vrt` référence les 54 GeoTIFF sans dupliquer les données, ouvrable directement dans QGIS. Les dalles déjà générées sont conservées (reprise après interruption, `--overwrite` pour forcer).

---

## 2026-11 — Dev Container non-root (utilisateur `ubuntu`, uid 1000)

**Constat** : le Dev Container tournait en root. Le workspace étant un montage du dossier WSL2, tout fichier créé dans le container (objets `.git`, `.venv`, caches, `.duckdb`, fichiers de tests) appartenait à `root` côté hôte. Un commit fait ensuite depuis WSL2 (ou VS Code hors container) échouait : `insufficient permission for adding an object to repository database .git/objects`.

**Décision** : la session VS Code tourne en `ubuntu` (uid 1000, utilisateur fourni par l'image `ubuntu:24.04`, même uid que l'utilisateur WSL2 par défaut).
- `Dockerfile` (stage dev) : `/app/.venv` installé par `ubuntu` ; `ENTRYPOINT` [`docker/dev-entrypoint.sh`](../docker/dev-entrypoint.sh) exécuté en root au démarrage.
- L'entrypoint lit le GID du socket Docker monté (variable selon la machine : 989 sur ce WSL2, 0 avec Docker Desktop) et y ajoute `ubuntu` → minikube et `docker` utilisables sans root.
- `devcontainer.json` : `"remoteUser": "ubuntu"` ; `"overrideCommand": false` (sinon VS Code remplace l'`ENTRYPOINT` de l'image par `/bin/sh` et le script ne s'exécute jamais — piège rencontré au premier essai) + `CMD ["sleep", "infinity"]` dans l'image ; `"init": true` ; volumes minikube/kube renommés `lidar-minikube-ubuntu` / `lidar-kube-ubuntu` (les anciens contenaient un état root, chemins `/root/...` codés dans le kubeconfig).
- `minikube start` sans `--force` ; `git config safe.directory` supprimé (plus de conflit de propriétaire).
- `post-start.sh` applique aussi les manifests K8s (`kubectl apply`, idempotent) → un cluster neuf est redéployé automatiquement.
---

## 2026-11 — MNT : référence 0.5m en Phase 1, multi-échelle déplacé en Phase 2

**Décision** : la Phase 1 produit un seul MNT de référence à 0.5m (pleine étendue, validé dans QGIS). Les autres échelles sont dérivées en Phase 2, uniquement celles requises par les indicateurs morphologiques. Amende la décision « Résolution MNT : multi-échelle » (2026-04).

**Pourquoi** :
- Validation isolée : un défaut du MNT (trous sous végétation, raccords de dalles) doit être détecté avant le calcul des indicateurs, sinon impossible de savoir si une anomalie vient du MNT ou de l'indicateur
- Les échelles utiles dépendent des indicateurs (fenêtres TPI, rayon SVF, taille des structures) → choix possible seulement en Phase 2
- 0.25m : densité de points sol sous couvert végétal souvent insuffisante → risque de bruit d'interpolation, à confirmer avant de générer sur toute l'étendue
- Évite de produire et stocker des rasters pleine étendue inutilisés

---

## 2026-11 — Orchestration pipeline : Prefect au lieu de Airflow

**Décision** : Prefect pour l'orchestration des pipelines (téléchargement → traitement → entraînement → évaluation).

**Pourquoi pas Airflow** :
- Setup lourd : serveur dédié, base de données, scheduler, workers séparés — Docker Compose de 5+ services
- DAGs verbeux, config YAML, debugging difficile (logs dispersés)
- Kubernetes Executor = très lourd pour minikube local
- Standard des grandes équipes data (Spotify, Airbnb) — surdimensionné à l'échelle de ce projet

**Pourquoi Prefect** :
- `pip install prefect` + `prefect server start` → pipeline opérationnel en 10 minutes
- Décorateurs Python natifs (`@flow`, `@task`) — stack trace normale, debugging simple
- 1 agent léger sur minikube suffit
- Écosystème actif, en forte adoption depuis 2022

---

## 2026-07 — DVC remote : Google Drive au lieu de GCS ; Terraform gère GitHub

**Constat** : un compte GCP nécessite un moyen de paiement. GCS était le seul service GCP utilisé en Phase 0-5. Contrainte retenue : aucun coût d'infrastructure, projet reproductible sans compte payant.

**Décision** :
- **DVC remote** → Google Drive (`dvc[gdrive]`, 15 Go gratuits, OAuth, sans compte payant). Même usage : `dvc push` envoie les dalles .laz sur Drive, `dvc pull` les récupère.
- **Terraform** → gère le repo GitHub (branch protection sur `main` + secret OAuth DVC dans Actions) au lieu du bucket GCS.
- **Bucket GCS** → code conservé dans une config Terraform séparée `terraform/gcs/`, non appliquée par défaut. Un `count` conditionnel dans la config principale ne suffisait pas : le provider `google` exige des credentials GCP même sans ressource à créer.
- **CI → Drive** : compte de service `dvc-ci` (lecteur du dossier Drive), clé JSON dans le secret `GDRIVE_CREDENTIALS_DATA`. Le token OAuth utilisateur expire après 7 jours tant que l'app OAuth est en mode « Test ».

**Terraform conservé** : branch protection et secrets CI restent déclarés en IaC, sans infrastructure payante.

---

## 2026-07 — Phase 6 : Hugging Face Spaces au lieu de GKE

**Constat** : les crédits GCP de 300$ expirent après 90 jours. GKE coûte ~50-100€/mois après l'essai — incompatible avec la contrainte « aucun coût d'infrastructure ». Un VPS Hetzner ajoutait une deuxième infrastructure à maintenir sans valeur ajoutée réelle.

**Décision** : Hugging Face Spaces uniquement pour la démo, Google Drive (DVC) pour les données (voir décision « DVC remote »).

| Composant | Avant (GKE) | Après |
|---|---|---|
| Démo modèle | API sur GKE | **Hugging Face Spaces** (gratuit, permanent) |
| MLflow résultats | Pod K8s sur GKE | **`reports/` sur GitHub** (figures + metrics.json) |
| PostGIS prod | Cloud SQL GCP | **Supprimé** — DuckDB suffisant au volume actuel |
| Données | GCS | **Google Drive via DVC** (gratuit) |
| IaC | Terraform GCP complet | **Terraform GitHub** (GCS optionnel dans `terraform/gcs/`) |

**Pourquoi HF Spaces suffit** : les résultats MLflow sont déjà exposés via `reports/phase3/` et `reports/phase4/` commitées dans Git — on peut observer les métriques sans accéder à une UI MLflow. La démo Gradio sur HF Spaces est gratuite, permanente, indexée par les moteurs de recherche et utilisable sans installation.

**Minikube** : conservé pour le développement local (MLflow, Prometheus, Grafana) — mêmes manifests K8s, sans cluster payant.

**Ce qu'on perd** : MLflow public en temps réel, PostGIS en prod. Ce qu'on gagne : zéro infrastructure à maintenir, démo accessible en permanence, stack maintenable à l'échelle du projet.

---

## 2026-06 — CI : tests sur runner GitHub Actions, pas dans le container Docker

**Décision** : Le CI exécute `ruff`, `mypy` et `pytest` directement sur le runner `ubuntu-24.04` via `uv sync --frozen`, et build l'image Docker séparément en fin de pipeline.

**Pourquoi pas dans le container** :
- Build Docker trop lent à chaque push (résolution + installation de ~200 packages)
- Cache uv natif GitHub Actions beaucoup plus efficace que le cache Docker
- Tests actuels (Phase 0) n'utilisent pas les libs système (GDAL, PROJ, libspatialindex) → risque de divergence nul pour l'instant

**Limite acceptée** : divergence possible entre l'environnement CI (libs système GitHub) et le container (libs système Dockerfile). Acceptable tant que les tests sont purement Python.

**Migration prévue en Phase 1** : dès que les tests touchent GDAL ou laspy sur des données réelles, migrer vers `docker build` + `docker run pytest` dans le CI pour garantir la fidélité de l'environnement.

---

## 2026-06 — Abandon re-classification CSF : classification IGN conservée avec classe 65

**Constat** : Tests visuels dans QGIS montrent que CSF (threshold=0.1m) produit
un résultat similaire à IGN Sol + classe 65, mais avec des trous en zone intérieure
(threshold trop agressif, points sol légitimes rejetés).

**Décision** : Conserver la classification IGN telle quelle, y compris la classe 65.

**Pourquoi garder la classe 65** : correspond aux zones de marais salants (salins
de l'Étang de Berre). Activité humaine historique attestée → vestiges archéologiques
possibles. Exclure ces points serait une perte d'information.

**Gestion des artefacts côtiers** : masque spatial sur l'emprise Saint-Blaise lors
de la génération du MNT. Les dalles côtières problématiques sortent naturellement
du périmètre d'intérêt archéologique.

**`pipeline.py` supprimé** — classification IGN utilisée directement, sans re-traitement.

---

## 2026-06 — Re-classification sol : PDAL CSF plutôt que classification IGN

**Constat** : Analyse visuelle de la dalle `LHD_FXX_0860_6265` révèle que la
classe Sol IGN contient des artefacts côtiers : points dans l'eau de l'Étang de
Berre, plage mélangée à des affleurements aquatiques. Ces erreurs propagent du
bruit dans le MNT et rendraient la détection archéologique peu fiable.

**Décision** : Ignorer la classe Sol IGN. Re-classifier le sol indépendamment
avec PDAL filtre CSF (Cloth Simulation Filter) via `src/lidar_arch/data/pipeline.py`.
PDAL utilisé via CLI subprocess (`pdal pipeline --stdin`) — le package PyPI `pdal`
nécessite une compilation CMake absente dans l'image de base.

**Pourquoi CSF et pas SMRF** :
- CSF préserve mieux les micro-reliefs archéologiques sur terrain accidenté
- SMRF plus adapté aux terrains plats uniformes (marais, plaines agricoles)
- Saint-Blaise = promontoire calcaire avec pentes → CSF plus approprié

**Paramètres retenus** :
| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `threshold` | 0.1 m | Serré pour préserver structures < 50 cm (murets, fossés) |
| `window` | 10 m | Taille max non-sol : arbres garrigue, petits bâtiments |
| `resolution` | 0.5 m | Cohérent avec résolution MNT principale |
| `smooth` | True | Post-traitement pentes (paramètre PDAL 2.6 : `smooth`, pas `slope`) |

---

## 2026-06 — Version de la classification IGN des dalles téléchargées

**Constat** : Les 54 dalles (source : imagerie.esrifrance.fr) utilisent la spec IGN **pré-2024-09-09**.
La version actuelle du DC_LiDAR_HD_1-0.pdf (màj 2024-09-09) mentionne "suppression de la classe 65",
mais la classe 65 ("Points aberrants") est bien présente dans les données.

**Décision** : Conserver la classification telle quelle — les données sont valides, simplement classifiées
selon l'ancienne spec. Le dictionnaire `CLASSIFICATIONS` du projet reflète cette version.

**Référence spec actuelle** : `data/reference/saint_blaise/DC_LiDAR_HD_1-0.pdf`

---

## 2026-04 — Périmètre v1 : Saint-Blaise uniquement

**Décision** : Le projet v1 se concentre sur Saint-Blaise (Saint-Mitre-les-Remparts, 13).
Miouvin et Abri Cornille = élargissements potentiels en v2.

**Pourquoi Saint-Blaise** :
- Sites bien documentés (remparts massifs ~6m hauteur = ground truth fiable)
- Couverture IGN LiDAR HD disponible (54 dalles téléchargées, 5.23 Go)

**Emprise du site — dalles IGN concernées** :
- `LHD_FXX_0860_6265` — partie centrale/nord (Ville basse, remparts archaïques et hellénistiques)
- `LHD_FXX_0860_6264` — partie sud (Tour I, Saillant sud, carrière principale)
- Emprise estimée : ~800m N-S × ~400m E-W (à affiner dans QGIS en Phase 1)

**Référence cartographique** :
- `data/reference/saint_blaise/plan_archeologique.jpg` — plan archéologique détaillé
- Source : Bulletin de Correspondance Hellénique — https://journals.openedition.org/bch/822
- Rôle : ground truth pour l'annotation des labels ML (table `sites` DuckDB)
- Structures massives → validation plus facile du pipeline avant micro-structures

**Pourquoi pas Miouvin en v1** :
- Murets en pierres sèches (~0.5m) → micro-structures, plus difficiles à valider
- Sera testé en v2 une fois le pipeline validé sur Saint-Blaise

**Pourquoi pas Abri Cornille** :
- Abri sous roche, intrinsèquement peu adapté à la détection LiDAR aérienne

---

## 2026-04 — Approche ML : raster avant nuage de points

**Décision** : Classification sur rasters MNT + dérivés (pas PointNet en v1).

**Pourquoi** :
- Plus simple (2D vs 3D)
- RandomForest/XGBoost suffisants pour valider le concept
- Moins gourmand en données annotées
- Littérature archéologique majoritairement sur rasters

**Évolution prévue** :
- Si résultats insuffisants → patches CNN sur rasters
- Si beaucoup de données → PointNet++ sur nuages de points

---

## 2026-04 — uv vs conda/venv

**Décision** : **uv** comme gestionnaire de dépendances.

**Pourquoi** :
- 10-100× plus rapide que pip
- Lockfile déterministe (`uv.lock`) → reproductibilité CI/CD
- Gère Python lui-même (pas besoin de pyenv séparé)
- Compatible `pyproject.toml` standard

**Conda écarté** : lourd, lent, orienté exploration data science.
**venv écarté** : pas de lockfile fiable natif.

---

## 2026-04 — Notebooks : exploration uniquement

**Décision** : notebooks pour la phase exploratoire initiale, jamais en prod.

**Pourquoi** :
- Non testables unitairement
- Versioning Git difficile (JSON avec outputs)
- Non réutilisables comme modules
- Dès qu'un traitement est validé → converti en `.py` dans `src/`

---

## 2026-04 — BentoML vs Seldon Core

**Décision** : **BentoML** pour le serving.

**Pourquoi** :
- Seldon Core : opérateur K8s et CRDs, lourd à opérer pour un seul modèle
- BentoML intégration native MLflow → packaging → API → container → K8s
- Couvre packaging, API et containerisation sans surcomplexité opérationnelle

---

## 2026-04 — CNN : ResNet18 + EfficientNet-B0

**Décision** : ResNet18 baseline, EfficientNet-B0 challenger.

**Pourquoi ResNet18 et pas ResNet50+** :
- Patches 64×64 simples (MNT, pente, TPI) → features peu complexes
- ResNet50+ = overfitting probable avec peu de données annotées
- ResNet18 (11M params) suffisant, entraînement rapide sur RTX 5070 Ti

**Pourquoi EfficientNet-B0** :
- Meilleur ratio performance/paramètres que ResNet18
- Weights ImageNet pré-entraînés disponibles via torchvision

---

## 2026-04 — Stack Python vs R

**Décision** : Python principal, R en lecture seule pour comprendre les papers.

**Pourquoi** :
- Python = écosystème de référence ML/MLOps (PyTorch, scikit-learn, MLflow)
- lidR (R) très utilisé en archéologie LiDAR mais pas nécessaire en production
- laspy + pdal couvrent les mêmes besoins en Python

---

## 2026-04 — Résolution MNT : multi-échelle (0.25m / 0.5m / 1m)

**Décision** : Générer le MNT à trois résolutions selon l'usage.

| Résolution | Usage |
|-----------|-------|
| **0.5m** | MNT principal pour la détection |
| **0.25m** | Micro-structures (zoom haute résolution) |
| **1m** | Contexte régional, vue d'ensemble |

**Pourquoi pas 1m seul** :
- IGN LiDAR HD ~10 pts/m² → résolution native ~0.3m exploitable
- À 1m, un muret de 0.5m devient 1 pixel → information perdue
- Fossés défensifs (1-3m), structures domestiques (2-4m) mal résolus à 1m

**Impact stockage** (1km² compressé GeoTIFF) :
- 1m → ~1M pixels
- 0.5m → ~4M pixels
- 0.25m → ~16M pixels

Reste gérable sur SSD 1To.