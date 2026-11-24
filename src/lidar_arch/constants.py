"""Constantes du projet (pas de magic numbers dans le code).

Justifications : `meta/DECISIONS.md`.
"""

from pathlib import Path

# --- Chemins ---------------------------------------------------------------
RAW_LIDAR_DIR = Path("data/raw/lidar/saint_blaise")
DTM_DIR = Path("data/processed/dtm")
DTM_VRT_NAME = "mnt_saint_blaise.vrt"

# --- Dalles IGN LiDAR HD ---------------------------------------------------
# Nom : LHD_FXX_<xmin km>_<ymax km>_PTS_C_LAMB93_IGN69.copc.laz (coin haut-gauche)
TILE_GLOB = "LHD_FXX_*.copc.laz"
TILE_SIZE_M = 1000.0
KM_TO_M = 1000.0
CRS_EPSG = 2154  # Lambert 93

# Classes sol retenues : 2 = Sol, 65 = points des salins (voir DECISIONS.md, 2026-06)
GROUND_CLASSES = (2, 65)

# --- MNT de référence ------------------------------------------------------
DTM_RESOLUTION_M = 0.5
# Tampon lu sur les dalles voisines : évite les artefacts TIN aux raccords de dalles
TILE_BUFFER_M = 20.0
# Décimation : moyenne des points sol par cellule (= pixel) avant triangulation
DECIMATION_CELL_M = DTM_RESOLUTION_M
# Triangle TIN avec une arête plus longue → nodata (plans d'eau, points isolés sur l'eau)
MAX_TIN_EDGE_M = 20.0
DTM_NODATA = -9999.0
