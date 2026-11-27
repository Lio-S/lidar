# Sources et conventions données

## IGN LiDAR HD

### Téléchargement
1. Créer un compte sur https://geoservices.ign.fr
2. Carte de couverture : https://macarte.ign.fr/carte/mThSup/diffusionMNxLiDARHD
3. Cliquer sur la dalle souhaitée → lien de téléchargement
4. Format : `.copc.laz` (nuages classés) ou `.laz` (bruts)

### Nommage des dalles
`LHD_FXX_XXXX_XXXX_PTS_C_LAMB93_IGN69.copc.laz`
- `PTS_C` = nuage classé
- `PTS_B` = nuage brut
- Coordonnées en Lambert 93 (km)

### Zone Saint-Blaise
Coordonnées réelles (Lambert 93) — 54 dalles téléchargées, 5.23 Go :
- X : 857 000 - 866 000
- Y : 6 262 000 - 6 267 000

Dalles couvrant le site archéologique principal :
- `LHD_FXX_0860_6265` — Ville basse, remparts nord
- `LHD_FXX_0860_6264` — Tour I, Saillant sud, carrières
→ Emprise estimée ~800m N-S × ~400m E-W (à affiner QGIS Phase 1)

### Dates
- Période de vol (heure GPS des points, 54 dalles) : **2021-06-13 → 2022-09-01**
- Création des fichiers COPC (en-tête LAS) : 2023-07-21
- 15 mois d'écart → probablement plusieurs missions : la date de vol diffère selon les dalles

### Espace disque estimé
- 54 dalles .laz compressées : 5.23 Go (téléchargées)
- Après décompression + MNT multi-résolution : ~30 Go (local uniquement)

### Stratégie DVC remote (Google Drive 15 Go gratuit)
Seules les données **non-reproductibles** sont pushées sur Drive :

| Données | DVC remote | Raison |
|---|---|---|
| `data/raw/lidar/` (5.23 Go) | ✅ pushé | Non reproductible sans re-télécharger IGN |
| `data/annotations/` (labels ML) | ✅ pushé | Travail manuel, non reproductible |
| `data/processed/` (MNT, features) | ❌ local | Régénérable via `dvc repro` depuis raw (étapes dans `dvc.yaml`) |
| `data/processed/patches/` (CNN) | ❌ local | Régénérable depuis processed |

→ 15 Go Drive suffisant pour ce projet. Un collaborateur fait `dvc pull` (raw) puis `dvc repro` (pipeline) pour regénérer les données processed localement.

### Accès au remote DVC selon le profil

| Profil | Accès Drive | Procédure |
|---|---|---|
| Exécuter / tester (lecture seule) | Dossier public "lecture" | `dvc pull` sans auth |
| Contributeur (push données) | Invitation Drive "Éditeur" | OAuth personnel + credentials DVC |
| Propriétaire | Accès complet | OAuth + `gdrive_client_id/secret` dans `.dvc/config.local` |

**Rendre le dossier public (lecture)** : Drive → dossier `lidar/` → Partager → "Tout le monde avec le lien" → Lecteur.

---

## Données archéologiques de référence

### Saint-Blaise — Plan archéologique
- Fichier : `data/reference/saint_blaise/plan_archeologique.jpg`
- Source : Bulletin de Correspondance Hellénique — https://journals.openedition.org/bch/822
- Contenu : remparts (archaïque, hellénistique, tardo-antique, médiéval), ville basse, ville haute, structures par période
- Rôle : ground truth pour annotation des labels ML
- Géométrie : orienté au nord, barre d'échelle 50 m, courbes de niveau cotées ; **non géoréférencé** (le `.aux.xml` ne contient que des métadonnées EXIF/XMP)

### Saint-Blaise — Plan de visite (dépliant 2012)
- Fichier : `data/external/saint_blaise/depliant_visite_2012.pdf` (non versionné : photos et maquette sous droits — Communauté d'Agglomération du Pays de Martigues, conception ville de Martigues)
- Contenu : plan de visite (p. 3) avec 20 points numérotés et légendés (p. 4 : portes, poternes, église paléochrétienne, puits-citerne, tombes rupestres, voie à ornières, carrières, silos, mur d'enceinte de Castelveyre daté de 1231), courbes de niveau, repères modernes (D51, piste DFCI, bergerie Graille, ancien canal de Martigues, clôture) ; **nord vers la gauche**
- Chiffres de contrôle (texte) : habitat dans un triangle de 5,5 ha ; rempart grec en ligne brisée de plus de 400 m (3 tours, 3 saillants, 11 courtines larges de 2 à 3 m) ; habitat dégagé sur ~7 000 m² ; classé Monument historique depuis 1943
- Bibliographie citée : Bouloumié 1984 (*Histoire et Archéologie, Les dossiers* n° 84) ; Trément 1999, *Archéologie d'un paysage. Les étangs de Saint-Blaise* (DAF n° 74) ; Chausserie-Laprée 2005, *Martigues, terre gauloise* (Errance)
- Rôle : points et attributs (nom, période) pour la table `sites`, structures hors enceinte ; chiffres de contrôle du géoréférencement

### Patriarche (Ministère Culture)
Base nationale des sites archéologiques — accès chercheurs.
Alternative publique : https://data.culture.gouv.fr

### Géoportail IGN
Couche "Patrimoine culturel" — sites classés visibles.

### OpenStreetMap
Tag `historic=archaeological_site` — données contributives.

---

## Conventions stockage local

```
data/
├── raw/
│   └── lidar/
│       └── saint_blaise/    ← dalles .laz originales (DVC)
├── reference/
│   └── saint_blaise/        ← plans, cartes, références scientifiques (Git)
├── external/
│   ├── bdtopo/              ← BD TOPO 2023-03-15, D013 (non versionné, voir « Données externes »)
│   ├── merimee/             ← export Mérimée 2026-11-26 + points Lambert 93 dérivés (non versionné)
│   └── saint_blaise/        ← dépliant de visite 2012 (non versionné, droits)
├── processed/
│   ├── dtm/                 ← MNT .tif 0.5m par dalle + mosaïque .vrt (non versionné)
│   ├── masque_bati/         ← masque d'exclusion bâti .tif (uint8, grille du MNT) + .vrt (non versionné)
│   ├── features/            ← rasters dérivés (pente, TPI...)
│   └── patches/             ← patches 64x64 pour CNN
└── annotations/
    ├── positive/             ← zones archéologiques confirmées
    └── negative/             ← zones sans structures
```

## Données externes

Données publiques retéléchargeables, non versionnées (`data/external/`, ignoré par Git).
Règle : prendre l'édition **la plus proche après la fin du vol LiDAR** (cohérence de date).

### BD TOPO (IGN) — masque bâti et couche de protection
- Édition retenue : **v3.3 du 2023-03-15** (première après le 2022-09-01), département 13, GeoPackage Lambert 93
- Téléchargement (343 Mo, archive `.7z`, MD5 annoncé `798a721f3e59f15f59d6a2fdc0c0c63d`) :
  ```bash
  mkdir -p data/external/bdtopo && cd data/external/bdtopo
  curl -LO https://data.geopf.fr/telechargement/download/BDTOPO/BDTOPO_3-3_TOUSTHEMES_GPKG_LAMB93_D013_2023-03-15/BDTOPO_3-3_TOUSTHEMES_GPKG_LAMB93_D013_2023-03-15.7z
  ```
  puis extraire (7-Zip sous Windows) dans `data/external/bdtopo/`
- Autres éditions : https://data.geopf.fr/telechargement/resource/BDTOPO?zone=D013&format=GPKG
- Inventaire sur l'emprise : `uv run python explore/02_bdtopo_inventaire.py`

### Monuments historiques (Ministère de la Culture, base Mérimée)
- https://www.data.gouv.fr/datasets/immeubles-proteges-au-titre-des-monuments-historiques-2
- Points uniquement (pas d'emprise), certains sans coordonnées : liste à contrôler, pas un masque
- Export utilisé : `data/external/merimee/merimee_2026-11-26.csv` (non versionné), lien de la ressource donné par l'API data.gouv.fr :
  ```bash
  curl -f -o data/external/merimee/merimee_2026-11-26.csv \
    https://ministere-culture.s3.sbg.io.cloud.ovh.net/POP/merimee.csv
  ```
  MD5 `ff4de08728cf18f125619f694787d02c`, 100 222 717 octets, Licence Ouverte 2.0. Le fichier est **remplacé à chaque mise à jour** de la base : un nouveau téléchargement donnera un autre MD5 (date de l'export dans le nom, constante `MERIMEE_CSV`)
- Format : séparateur `|`, 78 colonnes, 46 785 notices (2 278 sans coordonnées) ; coordonnées `lat,lon` WGS84 dans `coordonnees_au_format_WGS84`, code INSEE dans `COG_Insee_lors_de_la_protection` (plusieurs codes séparés par `;` pour les monuments à cheval sur des communes)
- Analyse : `explore/03_merimee.py` (rapport `explore/reports/merimee.txt`, points Lambert 93 pour QGIS dans `data/external/merimee/merimee_emprise_l93.gpkg`)

## Système de coordonnées
- **Stockage** : Lambert 93 (EPSG:2154) — système natif IGN
- **Visualisation** : WGS84 (EPSG:4326) pour affichage web
- Conversion avec `pyproj` ou `rasterio`