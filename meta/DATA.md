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
Coordonnées approximatives (Lambert 93) :
- X : 854 000 - 858 000
- Y : 6 264 000 - 6 268 000
→ ~16 dalles pour couvrir la zone élargie

### Espace disque estimé
- Dalles .laz compressées : 500Mo à 2Go/dalle
- Zone Saint-Blaise (~5km²) : ~5-10 Go téléchargement
- Après décompression + traitement : ~30 Go

---

## Données archéologiques de référence

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
│   ├── lidar/
│   │   └── saint_blaise/    ← dalles .laz originales (DVC)
│   └── reference/           ← shapefiles sites connus
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
