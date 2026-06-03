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

### Espace disque estimé
- 54 dalles .laz compressées : 5.23 Go (téléchargées)
- Après décompression + MNT multi-résolution : ~30 Go

---

## Données archéologiques de référence

### Saint-Blaise — Plan archéologique
- Fichier : `data/reference/saint_blaise/plan_archeologique.jpg`
- Source : Bulletin de Correspondance Hellénique — https://journals.openedition.org/bch/822
- Contenu : remparts (archaïque, hellénistique, tardo-antique, médiéval), ville basse, ville haute, structures par période
- Rôle : ground truth pour annotation des labels ML

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
├── processed/
│   ├── dtm/                 ← MNT .tif (1m résolution)
│   ├── features/            ← rasters dérivés (pente, TPI...)
│   └── patches/             ← patches 64x64 pour CNN
└── annotations/
    ├── positive/             ← zones archéologiques confirmées
    └── negative/             ← zones sans structures
```

## Système de coordonnées
- **Stockage** : Lambert 93 (EPSG:2154) — système natif IGN
- **Visualisation** : WGS84 (EPSG:4326) pour affichage web
- Conversion avec `pyproj` ou `rasterio`
