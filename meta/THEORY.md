# Notes théoriques

## 1. LiDAR et archéologie

### Principe
Le LiDAR (Light Detection And Ranging) envoie des impulsions laser depuis un avion.
Chaque impulsion peut avoir plusieurs retours :
- **Premier retour** → cime de végétation, toits
- **Retours intermédiaires** → strates végétation
- **Dernier retour** → sol (ou proche sol)

En ne conservant que le dernier retour et en interpolant, on obtient un
**MNT (Modèle Numérique de Terrain)** qui représente le sol nu, même sous forêt dense.

### IGN LiDAR HD
- Densité : ≥10 points/m²
- Format : LAZ 1.4 (LAS compressé)
- Dalles : 1km × 1km
- CRS : Lambert 93 (EPSG:2154)
- Classification ASPRS 11 classes : sol, végétation basse/moyenne/haute, bâtiment, eau...

---

## 2. Traitement nuages de points

### Pipeline standard
```
.laz → Filtrage sol (CSF/PMF) → Interpolation → MNT raster → Indicateurs
```

### Algorithmes de filtrage sol
- **CSF** (Cloth Simulation Filter) : simule un tissu qui tombe sur le terrain
- **PMF** (Progressive Morphological Filter) : érosion/dilatation progressives
- **SMRF** (Simple Morphological Filter) : variante PMF plus robuste

### Librairies
- **laspy** : lecture/écriture .las/.laz en Python
- **pdal** : pipeline de traitement complet (JSON config)
- **lidR** : package R très utilisé en archéologie (à connaître pour lire les papers)
- **CloudCompare** : visualisation 3D (GUI)
- **QGIS** : visualisation et analyse géospatiale (plugin LiDAR natif depuis v3.34)

---

## 3. Indicateurs morphologiques (features ML)

À partir du MNT raster, on calcule des dérivés qui caractérisent la forme du terrain :

| Indicateur | Description | Pertinence archéo |
|-----------|-------------|-------------------|
| **Pente** | Gradient du MNT | Détecte talus, remparts |
| **Aspect** | Orientation de la pente | Contexte |
| **Courbure** | Dérivée seconde | Bords de fossés, buttes |
| **TPI** (Topographic Position Index) | Élévation relative à voisinage | Tumuli, dépressions |
| **TRI** (Terrain Ruggedness Index) | Rugosité locale | Structures perturbées |
| **openness** | Ouverture angulaire | Relief positif/négatif |
| **Sky View Factor** | Fraction de ciel visible | Très sensible aux micro-reliefs |

Le **Sky View Factor (SVF)** et l'**openness** sont particulièrement utilisés en archéologie LiDAR car très sensibles aux micro-reliefs anthropiques.

---

## 4. Approches ML pour la détection

### Niveau raster (approche recommandée pour commencer)
Chaque pixel du MNT + ses dérivés = vecteur de features → classification

- **RandomForest** : robuste, interprétable, bon point de départ
- **XGBoost/LightGBM** : souvent meilleur que RF sur données tabulaires
- **CNN** : si on traite des patches raster (images 2D) → plus puissant mais nécessite plus de données annotées

### Niveau nuage de points (plus avancé)
- **PointNet / PointNet++** : architecture deep learning native 3D
- Nécessite GPU et beaucoup de données

### Problème de déséquilibre de classes
Les structures archéologiques représentent une infime fraction du terrain.
Techniques à connaître :
- **SMOTE** : sur-échantillonnage synthétique
- **Class weights** : pondération dans la loss
- **Threshold tuning** : ajuster le seuil de décision

---

## 5. Évaluation et métriques

Pour un problème fortement déséquilibré (rare = archéo) :
- **Precision / Recall** plus pertinents que l'accuracy
- **F1-score** : compromis P/R
- **AUC-ROC** : capacité discriminante globale
- **Average Precision** : aire sous courbe P/R

---

## Lectures à faire (priorité décroissante)

À lire au fur et à mesure de l'avancement du projet — non lues à ce jour.

- **Štular et al. (2012)** — *Visualization of lidar-derived relief models for detection of archaeological features*
  → SVF, openness — méthodes pour Phase 2
  → PDF gratuit : https://hal.science/halshs-00743691/
- **Guyot et al. (2021)** — *Objective Comparison of Relief Visualization Techniques with Deep CNN for Archaeology*
  → directement pertinent pour Phase 4 (CNN sur rasters LiDAR)
  → PDF gratuit : https://hal.science/hal-03229809/document
- **Jaturapitpornchai et al. (2024)** — *Impact of LiDAR visualisations on semantic segmentation of archaeological objects*
  → extension récente de Guyot 2021 — segmentation sémantique multi-VT
  → PDF gratuit : https://www.arxiv.org/pdf/2404.05512
- **Opitz & Cowley (2013)** — *Interpreting Archaeological Topography* (ouvrage Oxbow Books)
  → fond théorique, lecture optionnelle
  → Pas gratuit légalement (~50€) — bibliothèque universitaire ou PEB
- **Chase et al. (2011)** — LiDAR Maya, cas d'étude fondateur
  → contexte historique du domaine, optionnel
  → Chercher PDF sur Google Scholar
