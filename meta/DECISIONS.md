# Décisions techniques

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
- Seldon Core trop complexe pour un projet solo
- BentoML intégration native MLflow → packaging → API → container → K8s
- Montre les compétences serving sans surcompléxité opérationnelle

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
- Python = marché ML/MLOps
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
