"""Constantes du projet (pas de magic numbers dans le code).

Justifications : `meta/DECISIONS.md`.
"""

from pathlib import Path

# --- Chemins ---------------------------------------------------------------
RAW_LIDAR_DIR = Path("data/raw/lidar/saint_blaise")
DTM_DIR = Path("data/processed/dtm")
DTM_VRT_NAME = "mnt_saint_blaise.vrt"
EXTERNAL_DIR = Path("data/external")
BDTOPO_DIR = EXTERNAL_DIR / "bdtopo"
# Première édition BD TOPO publiée après la fin du vol LiDAR (2022-09-01), voir DATA.md
BDTOPO_EDITION = "BDTOPO_3-3_TOUSTHEMES_GPKG_LAMB93_D013_2023-03-15"

# --- Dalles IGN LiDAR HD ---------------------------------------------------
# Nom : LHD_FXX_<xmin km>_<ymax km>_PTS_C_LAMB93_IGN69.copc.laz (coin haut-gauche)
TILE_GLOB = "LHD_FXX_*.copc.laz"
TILE_SIZE_M = 1000.0
KM_TO_M = 1000.0
CRS_EPSG = 2154  # Lambert 93

# Classes sol retenues : 2 = Sol, 65 = points des salins (voir DECISIONS.md, 2026-06)
GROUND_CLASSES = (2, 65)

# Classification IGN (spec pré-2024-09, voir DECISIONS.md) — utilisée pour la table `dalles`
CLASS_SOL = 2
CLASS_65 = 65
VEGETATION_CLASSES = (3, 4, 5)  # basse, moyenne, haute
CLASS_BATIMENT = 6
CLASS_EAU = 9
LAS_CLASS_COUNT = 256  # classification LAS sur 8 bits
BYTES_PER_MB = 1024 * 1024
LAS_CHUNK_POINTS = 5_000_000  # lecture par blocs : mémoire bornée sur les dalles denses

# --- Base DuckDB -------------------------------------------------------------
IGN_BLOC = "OQ"
# id stable d'une dalle : XXXX_YYYY → XXXX × 10⁴ + YYYY (ex. 0860_6265 → 8606265)
TILE_ID_FACTOR = 10_000

# --- MNT de référence ------------------------------------------------------
DTM_RESOLUTION_M = 0.5
# Tampon lu sur les dalles voisines : évite les artefacts TIN aux raccords de dalles
TILE_BUFFER_M = 20.0
# Décimation : moyenne des points sol par cellule (= pixel) avant triangulation
DECIMATION_CELL_M = DTM_RESOLUTION_M
# Triangle TIN avec une arête plus longue → nodata (plans d'eau, points isolés sur l'eau)
MAX_TIN_EDGE_M = 20.0
DTM_NODATA = -9999.0
# Aperçus internes des GeoTIFF (affichage QGIS fluide en vue d'ensemble) : 2000 px → 125 px
DTM_OVERVIEW_FACTORS = (2, 4, 8, 16)
