"""Masque d'exclusion bâti : emprise du bâti moderne + tampon, sur la grille du MNT.

Chaîne par dalle (1 km²) :

1. Lecture des points classe 6 (bâtiment IGN) de la dalle **et** d'une marge prise sur
   les dalles voisines (tampon + fermeture) → masque continu aux raccords.
2. Rastérisation à 0.5 m : pixel occupé si au moins un point bâtiment.
3. Fermeture morphologique (1 m) : relie les pixels de toit restés vides.
4. Suppression des emprises < 10 m² : points isolés mal classés.
5. Tampon de 10 m (jardins, cours, voirie), puis découpe à l'emprise de la dalle.
6. Écriture GeoTIFF ``uint8`` (1 = exclu, 0 = conservé) et mosaïque ``.vrt``.

Le masque n'est **pas** appliqué au MNT : il sert à la construction du dataset
(Phase 3). Voir `meta/DECISIONS.md` (2026-11 — Zones urbaines).

Usage : ``python -m lidar_arch.data.building_mask [--tile 0860_6265 ...] [--overwrite]``
"""

import argparse
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from scipy import ndimage
from tqdm import tqdm

from lidar_arch.constants import (
    BUILDING_BUFFER_M,
    BUILDING_CLOSING_M,
    BUILDING_MASK_DIR,
    BUILDING_MASK_VRT_NAME,
    CLASS_BATIMENT,
    CRS_EPSG,
    DTM_OVERVIEW_FACTORS,
    DTM_RESOLUTION_M,
    MASK_EXCLUDED,
    MIN_BUILDING_AREA_M2,
    RAW_LIDAR_DIR,
)
from lidar_arch.data.dtm import (
    FloatArray,
    TileBounds,
    build_vrt,
    read_class_points,
    select_tiles,
    tile_id,
)
from lidar_arch.logging_config import configure_logging, get_logger

logger = get_logger("lidar_arch.data.building_mask")

BoolArray = npt.NDArray[np.bool_]


def building_mask_path(out_dir: Path, code: str) -> Path:
    """Chemin du GeoTIFF masque d'une dalle (``code`` = ``XXXX_YYYY``)."""
    return out_dir / f"masque_bati_{code}.tif"


def rasterize_points(points: FloatArray, bounds: TileBounds, resolution: float) -> BoolArray:
    """Grille booléenne (nord en haut) : pixel vrai s'il contient au moins un point."""
    n_cols = round((bounds.xmax - bounds.xmin) / resolution)
    n_rows = round((bounds.ymax - bounds.ymin) / resolution)
    grid = np.zeros((n_rows, n_cols), dtype=bool)
    cols = np.floor((points[:, 0] - bounds.xmin) / resolution).astype(np.int64)
    rows = np.floor((bounds.ymax - points[:, 1]) / resolution).astype(np.int64)
    inside = (cols >= 0) & (cols < n_cols) & (rows >= 0) & (rows < n_rows)
    grid[rows[inside], cols[inside]] = True
    return grid


def _disk(radius_px: int) -> BoolArray:
    """Élément structurant circulaire de rayon ``radius_px`` pixels."""
    offsets = np.arange(-radius_px, radius_px + 1)
    return np.hypot(*np.meshgrid(offsets, offsets)) <= radius_px


def building_footprint(
    occupancy: BoolArray, resolution: float, closing_m: float, min_area_m2: float
) -> BoolArray:
    """Emprise du bâti : fermeture morphologique puis suppression des petites emprises."""
    closed = ndimage.binary_closing(occupancy, structure=_disk(round(closing_m / resolution)))
    labels, _ = ndimage.label(closed, structure=np.ones((3, 3), dtype=bool))
    areas_m2 = np.bincount(labels.ravel()) * resolution**2
    keep = areas_m2 >= min_area_m2
    keep[0] = False  # étiquette 0 = fond
    return np.asarray(keep[labels], dtype=bool)


def buffer_mask(footprint: BoolArray, resolution: float, buffer_m: float) -> BoolArray:
    """Pixels à moins de ``buffer_m`` mètres d'un pixel de ``footprint`` (inclus)."""
    if not footprint.any():
        return np.zeros_like(footprint)
    distance_m = ndimage.distance_transform_edt(~footprint, sampling=resolution)
    return np.asarray(distance_m <= buffer_m, dtype=bool)


def compute_building_mask(points: FloatArray, bounds: TileBounds, resolution: float) -> BoolArray:
    """Masque d'exclusion d'une dalle à partir des points bâtiment (marge comprise).

    ``points`` doit couvrir ``bounds`` élargi de la marge (tampon + fermeture) : la
    grille de calcul est élargie d'autant, puis découpée à ``bounds``.
    """
    margin_px = round((BUILDING_BUFFER_M + BUILDING_CLOSING_M) / resolution)
    extended = bounds.buffered(margin_px * resolution)
    occupancy = rasterize_points(points, extended, resolution)
    footprint = building_footprint(occupancy, resolution, BUILDING_CLOSING_M, MIN_BUILDING_AREA_M2)
    mask = buffer_mask(footprint, resolution, BUILDING_BUFFER_M)
    return mask[margin_px:-margin_px, margin_px:-margin_px]


def write_mask(mask: BoolArray, bounds: TileBounds, resolution: float, path: Path) -> None:
    """Écrit le masque en GeoTIFF ``uint8`` Lambert 93 compressé, avec aperçus internes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": mask.shape[0],
        "width": mask.shape[1],
        "count": 1,
        "dtype": "uint8",
        "crs": CRS.from_epsg(CRS_EPSG),
        "transform": from_origin(bounds.xmin, bounds.ymax, resolution, resolution),
        "compress": "deflate",
        "tiled": True,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.where(mask, MASK_EXCLUDED, 0).astype(np.uint8), 1)
        factors = [f for f in DTM_OVERVIEW_FACTORS if f <= min(mask.shape)]
        if factors:
            dst.build_overviews(factors, Resampling.mode)  # valeur majoritaire : reste 0/1


def generate_tile_mask(
    tile_path: Path, tiles: Mapping[Path, TileBounds], out_dir: Path, overwrite: bool = False
) -> Path:
    """Génère le masque bâti d'une dalle et retourne le chemin du GeoTIFF."""
    out_path = building_mask_path(out_dir, tile_id(tile_path))
    if out_path.exists() and not overwrite:
        logger.info("Masque déjà présent, ignoré : %s", out_path.name)
        return out_path

    start = time.perf_counter()
    bounds = tiles[tile_path]
    margin_m = BUILDING_BUFFER_M + BUILDING_CLOSING_M
    points = read_class_points(tiles, bounds.buffered(margin_m), (CLASS_BATIMENT,))
    mask = compute_building_mask(points, bounds, DTM_RESOLUTION_M)
    write_mask(mask, bounds, DTM_RESOLUTION_M, out_path)

    logger.info(
        "Masque %s : %d points bâtiment, %.1f %% exclu, %.0f s",
        out_path.name,
        len(points),
        100 * mask.mean(),
        time.perf_counter() - start,
    )
    return out_path


def generate_building_mask(
    raw_dir: Path,
    out_dir: Path,
    overwrite: bool = False,
    tile_ids: Sequence[str] | None = None,
) -> Path:
    """Génère le masque bâti des dalles de ``raw_dir`` et la mosaïque .vrt.

    Returns
    -------
    pathlib.Path
        Chemin de la mosaïque virtuelle (tous les masques présents dans ``out_dir``).
    """
    tiles, selected = select_tiles(raw_dir, tile_ids)
    for path in tqdm(selected, "Masque bâti"):
        generate_tile_mask(path, tiles, out_dir, overwrite)

    tif_paths = sorted(out_dir.glob("masque_bati_*.tif"))
    vrt_path = out_dir / BUILDING_MASK_VRT_NAME
    build_vrt(tif_paths, vrt_path)
    logger.info("Mosaïque : %s (%d dalles)", vrt_path, len(tif_paths))
    return vrt_path


def main(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description="Masque d'exclusion bâti (classe 6 + tampon)")
    parser.add_argument("--raw-dir", type=Path, default=RAW_LIDAR_DIR)
    parser.add_argument("--out-dir", type=Path, default=BUILDING_MASK_DIR)
    parser.add_argument("--overwrite", action="store_true", help="régénère les dalles existantes")
    parser.add_argument(
        "--tile",
        dest="tile_ids",
        action="append",
        metavar="XXXX_YYYY",
        help="dalle à traiter (répétable, ex. --tile 0860_6265) ; toutes par défaut",
    )
    args = parser.parse_args(argv)

    configure_logging()
    generate_building_mask(args.raw_dir, args.out_dir, args.overwrite, args.tile_ids)


if __name__ == "__main__":
    main()
