# Glossaire — Projet LiDAR Archéologie

Référence rapide des outils, formats, concepts et librairies utilisés.

---

## Outils SIG (Système d'Information Géographique)

| Terme | Description |
|-------|-------------|
| **QGIS LTR** | Logiciel SIG libre, version Long Term Release (stable). Visualisation cartes, rasters, nuages de points. |
| **OSGeo4W** | Installeur Windows pour l'écosystème géospatial OSGeo (QGIS, GDAL, GRASS...). |
| **OSGeo** | Open Source Geospatial Foundation — fondation qui maintient les outils géo open source. |
| **GDAL** | Geospatial Data Abstraction Library — bibliothèque de référence pour conversion/traitement de données géospatiales (rasters et vecteurs). |
| **GRASS GIS** | SIG avancé orienté analyse scientifique. Pas utilisé dans ce projet. |

## Extensions QGIS installées

| Extension | Usage |
|-----------|-------|
| **QuickMapServices** | Ajoute des fonds de carte (OSM, Google, Bing...) en quelques clics. |
| **Profile Tool** | Trace des profils altimétriques le long d'une ligne — coupes de terrain. |
| **Value Tool** | Affiche en temps réel la valeur du pixel raster sous le curseur. |
| **Relief Visualization Toolbox (RVT)** | Calcule visualisations LiDAR pour archéologie : SVF, openness, hillshade, slope. ⭐ |
| **qgis2threejs** | Export 3D du terrain visualisable dans un navigateur web. |
| **QuickWKT** | Visualisation rapide et temporaire de géométries WKT/WKB. |

## Systèmes de coordonnées

| Terme | Description |
|-------|-------------|
| **CRS** | Coordinate Reference System — système de référence de coordonnées (projection + datum). |
| **EPSG** | European Petroleum Survey Group — catalogue de codes standardisés pour les CRS (ex: EPSG:2154). |
| **Lambert 93** | Projection officielle française métropolitaine. Code EPSG:2154. Coordonnées en mètres. |
| **WGS84** | World Geodetic System 1984 — système mondial en degrés (lat/lon). Code EPSG:4326. Utilisé par GPS, Google Maps. |
| **IGN69** | Référentiel altimétrique français — altitudes en mètres au-dessus du géoïde IGN69. |

## Formats de fichiers

| Format | Description |
|--------|-------------|
| **.las** | LAS (LASer) — format standard nuage de points LiDAR. |
| **.laz** | Version compressée du .las (LAS Zip). Réduction ~80% sans perte. |
| **.copc.laz** | Cloud Optimized Point Cloud — variante optimisée pour accès partiel/streaming. Format des dalles IGN LiDAR HD. |
| **.tif / .geotiff** | Raster géoréférencé. Standard pour MNT, MNS, indicateurs morphologiques. |
| **.shp** | Shapefile — ancien format vecteur ESRI. À éviter pour les nouveaux projets. |
| **.gpkg** | GeoPackage — format vecteur+raster moderne (basé SQLite). Standard OGC, fichier unique. ⭐ |
| **.parquet / .geoparquet** | Format colonnaire optimisé pour gros volumes. Lecture rapide en analytique. |

## Concepts LiDAR / Modèles numériques

| Terme | Description |
|-------|-------------|
| **LiDAR** | Light Detection And Ranging — télédétection par impulsions laser. |
| **Nuage de points** | Ensemble des points XYZ mesurés par le LiDAR, avec attributs (intensité, classe, retour...). |
| **MNT** | Modèle Numérique de Terrain — surface du sol nu (sans végétation ni bâti). |
| **MNS** | Modèle Numérique de Surface — surface du dessus (canopée, toits inclus). |
| **MNH** | Modèle Numérique de Hauteur = MNS − MNT (hauteur végétation/bâti). |
| **Classification** | Attribution d'une catégorie à chaque point (sol, végétation, bâti...). |
| **Dalle** | Pavé de 1km × 1km couvrant une zone — unité de découpage IGN LiDAR HD. |

## Indicateurs morphologiques (features ML)

| Terme | Définition courte |
|-------|-------------------|
| **Pente (slope)** | Gradient du MNT |
| **Aspect** | Orientation de la pente |
| **Courbure** | Dérivée seconde du MNT |
| **TPI** | Topographic Position Index — élévation relative au voisinage |
| **TRI** | Terrain Ruggedness Index — rugosité locale |
| **SVF** | Sky View Factor — fraction de ciel visible |
| **Openness** | Ouverture angulaire (positive ou négative) |
| **Hillshade** | Ombrage simulé du relief |

→ Explications détaillées et pertinence archéologique : `meta/THEORY.md § 3`.

## Librairies Python — LiDAR & géospatial

| Librairie | Usage |
|-----------|-------|
| **laspy** | Lecture/écriture fichiers .las/.laz en Python. |
| **PDAL** | Point Data Abstraction Library — pipeline complet traitement nuages de points (filtrage, classification, conversion). |
| **whitebox** | Calcul indicateurs morphologiques (TPI, SVF, openness...). |
| **rasterio** | Lecture/écriture/manipulation rasters (GeoTIFF...). |
| **geopandas** | Pandas pour données vecteur géospatiales (.gpkg, .shp...). |
| **pyproj** | Conversions entre CRS (Lambert 93 ↔ WGS84...). |
| **shapely** | Géométries 2D (points, lignes, polygones). |

## Librairies Python — ML

| Librairie | Usage |
|-----------|-------|
| **scikit-learn** | ML classique (RandomForest, métriques, pipelines). |
| **XGBoost / LightGBM** | Gradient boosting performant. |
| **PyTorch / torchvision** | Deep learning (CNN, PointNet++). |
| **MLflow** | Tracking expériences, comparaison modèles. |
| **Evidently** | Métriques qualité données et modèles, drift. |
| **BentoML** | Packaging modèle → API → container. |

## MLOps & Infrastructure

| Terme | Description |
|-------|-------------|
| **uv** | Gestionnaire dépendances Python moderne. Remplace pip/venv/conda. |
| **DVC** | Data Version Control — versioning des gros fichiers (données, modèles). |
| **MLflow** | Tracking expériences ML + registre de modèles. |
| **Docker** | Containerisation applications. |
| **Kubernetes (K8s)** | Orchestration de containers à l'échelle. |
| **Terraform** | Infrastructure as Code (provisionnement cloud déclaratif). |
| **GCP** | Google Cloud Platform — cloud utilisé pour la prod du projet. |
| **GCS** | Google Cloud Storage — stockage objet (équivalent S3 AWS). |
| **GKE** | Google Kubernetes Engine — K8s managé GCP. |
| **PostGIS** | Extension PostgreSQL pour données géospatiales. |
| **DuckDB** | Base SQL analytique embarquée — alternative locale à PostgreSQL. |

## Sources de données

| Source | Description |
|--------|-------------|
| **IGN** | Institut national de l'information géographique et forestière. |
| **IGN LiDAR HD** | Programme national de couverture LiDAR haute densité (~10 pts/m²). |
| **OSM** | OpenStreetMap — base cartographique collaborative mondiale. |
| **BRGM** | Bureau de Recherches Géologiques et Minières. |

→ URLs, procédures, conventions stockage : `meta/DATA.md`.

## Sites archéologiques de référence

→ Voir `meta/DECISIONS.md § Périmètre v1` pour le détail des sites et justifications.

## Communautés / Ressources

| Ressource | Description |
|-----------|-------------|
| **CAA** | Computer Applications in Archaeology — communauté internationale archéo numérique. |
| **open-archaeo.info** | Répertoire d'outils open source pour l'archéologie. |
| **Communauté LiDAR HD IGN** | Forum technique IGN : expertises-territoires.fr |
