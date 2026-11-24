"""Génération du MNT de référence 0.5 m depuis la classification sol IGN.

Chaîne par dalle (1 km²) :

1. Lecture des points sol (classes 2 + 65) de la dalle **et** d'un tampon de 20 m pris sur
   les dalles voisines (lecture spatiale COPC) → pas d'artefact aux raccords.
2. Décimation : moyenne des points par cellule de 0.5 m (mémoire de la triangulation ÷ ~3).
3. Interpolation TIN linéaire (triangulation de Delaunay) aux centres des pixels.
4. Masque nodata des triangles dont une arête dépasse 20 m (plans d'eau, points isolés).
5. Écriture GeoTIFF Lambert 93, puis mosaïque virtuelle `.vrt` de toutes les dalles.

Usage : ``python -m lidar_arch.data.dtm [--tile 0860_6265 ...] [--overwrite]``

Choix justifiés dans `meta/DECISIONS.md` (2026-11 — MNT de référence : TIN linéaire).
"""

import argparse
import re
import time
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import rasterio
from laspy import Bounds, CopcReader
from rasterio.crs import CRS
from rasterio.transform import from_origin
from scipy.spatial import Delaunay
from tqdm import tqdm

from lidar_arch.constants import (
    CRS_EPSG,
    DECIMATION_CELL_M,
    DTM_DIR,
    DTM_NODATA,
    DTM_RESOLUTION_M,
    DTM_VRT_NAME,
    GROUND_CLASSES,
    KM_TO_M,
    MAX_TIN_EDGE_M,
    RAW_LIDAR_DIR,
    TILE_BUFFER_M,
    TILE_GLOB,
    TILE_SIZE_M,
)
from lidar_arch.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

FloatArray = npt.NDArray[np.float64]

_TILE_NAME_RE = re.compile(r"LHD_FXX_(?P<x>\d{4})_(?P<y>\d{4})_")
_MIN_TIN_POINTS = 3  # une triangulation nécessite au moins 3 points


@dataclass(frozen=True)
class TileBounds:
    """Emprise rectangulaire en Lambert 93 (mètres)."""

    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def buffered(self, distance: float) -> "TileBounds":
        """Emprise agrandie de ``distance`` mètres de chaque côté."""
        return TileBounds(
            self.xmin - distance, self.ymin - distance, self.xmax + distance, self.ymax + distance
        )

    def intersects(self, other: "TileBounds") -> bool:
        """Vrai si les deux emprises se chevauchent (bords exclus)."""
        return (
            self.xmin < other.xmax
            and other.xmin < self.xmax
            and self.ymin < other.ymax
            and other.ymin < self.ymax
        )

    def contains(self, x: FloatArray, y: FloatArray) -> npt.NDArray[np.bool_]:
        """Masque des points (x, y) situés dans l'emprise (bords inclus)."""
        return (x >= self.xmin) & (x <= self.xmax) & (y >= self.ymin) & (y <= self.ymax)


def tile_id(path: Path) -> str:
    """Identifiant ``XXXX_YYYY`` d'une dalle IGN, extrait de son nom de fichier.

    Raises
    ------
    ValueError
        Si le nom ne suit pas la convention IGN LiDAR HD.
    """
    match = _TILE_NAME_RE.search(path.name)
    if match is None:
        raise ValueError(f"Nom de dalle IGN non reconnu : {path.name}")
    return f"{match['x']}_{match['y']}"


def tile_bounds_from_name(path: Path) -> TileBounds:
    """Emprise d'une dalle déduite de son nom (coin haut-gauche en km).

    Examples
    --------
    >>> tile_bounds_from_name(Path("LHD_FXX_0860_6265_PTS_C_LAMB93_IGN69.copc.laz"))
    TileBounds(xmin=860000.0, ymin=6264000.0, xmax=861000.0, ymax=6265000.0)
    """
    x_km, y_km = (int(v) for v in tile_id(path).split("_"))
    xmin, ymax = x_km * KM_TO_M, y_km * KM_TO_M
    return TileBounds(xmin, ymax - TILE_SIZE_M, xmin + TILE_SIZE_M, ymax)


def read_tile_points(path: Path, bounds: TileBounds) -> FloatArray:
    """Points (x, y, z, classe) d'une dalle COPC situés dans ``bounds``.

    La requête COPC renvoie des nœuds entiers de l'octree : un filtrage exact suit.
    """
    query = Bounds(
        mins=np.array([bounds.xmin, bounds.ymin]), maxs=np.array([bounds.xmax, bounds.ymax])
    )
    with CopcReader.open(path) as reader:
        points = reader.query(query)
    xyzc = np.column_stack(
        [
            np.asarray(points.x, dtype=np.float64),
            np.asarray(points.y, dtype=np.float64),
            np.asarray(points.z, dtype=np.float64),
            np.asarray(points.classification, dtype=np.float64),
        ]
    )
    return xyzc[bounds.contains(xyzc[:, 0], xyzc[:, 1])]


def read_ground_points(tiles: Mapping[Path, TileBounds], bounds: TileBounds) -> FloatArray:
    """Points sol (x, y, z) de toutes les dalles qui recoupent ``bounds``."""
    chunks = [
        read_tile_points(path, bounds)
        for path, tile_bounds in tiles.items()
        if tile_bounds.intersects(bounds)
    ]
    if not chunks:
        return np.empty((0, 3))
    xyzc = np.concatenate(chunks)
    return xyzc[np.isin(xyzc[:, 3], GROUND_CLASSES), :3]


def decimate_points(points: FloatArray, cell_size: float) -> FloatArray:
    """Remplace les points de chaque cellule carrée par leur barycentre (x, y, z moyens)."""
    if len(points) == 0:
        return points
    ij = np.floor(points[:, :2] / cell_size).astype(np.int64)
    ij -= ij.min(axis=0)
    keys = ij[:, 0] * (ij[:, 1].max() + 1) + ij[:, 1]
    _, inverse, counts = np.unique(keys, return_inverse=True, return_counts=True)
    sums = np.column_stack([np.bincount(inverse, weights=points[:, k]) for k in range(3)])
    result: FloatArray = sums / counts[:, np.newaxis]
    return result


def pixel_centers(bounds: TileBounds, resolution: float) -> tuple[FloatArray, FloatArray]:
    """Coordonnées x (colonnes, ouest → est) et y (lignes, nord → sud) des centres de pixels."""
    n_cols = round((bounds.xmax - bounds.xmin) / resolution)
    n_rows = round((bounds.ymax - bounds.ymin) / resolution)
    xs = bounds.xmin + (np.arange(n_cols, dtype=np.float64) + 0.5) * resolution
    ys = bounds.ymax - (np.arange(n_rows, dtype=np.float64) + 0.5) * resolution
    return xs, ys


def interpolate_tin(
    points: FloatArray, xs: FloatArray, ys: FloatArray, max_edge: float
) -> npt.NDArray[np.float32]:
    """Interpolation TIN linéaire de z aux nœuds de la grille ``xs`` × ``ys``.

    Les pixels hors de l'enveloppe convexe des points, ou situés dans un triangle dont
    une arête dépasse ``max_edge``, valent NaN : un point isolé (retour parasite sur
    l'eau) n'est relié que par de longs triangles et disparaît, sans créer de plage plate.

    Returns
    -------
    numpy.ndarray
        Grille float32 de forme ``(len(ys), len(xs))``.
    """
    shape = (len(ys), len(xs))
    if len(points) < _MIN_TIN_POINTS:
        return np.full(shape, np.nan, dtype=np.float32)
    # Coordonnées recentrées : Lambert 93 (~10⁶ m) dégrade la précision de Qhull
    origin = points[:, :2].min(axis=0)
    xy = points[:, :2] - origin
    grid_x, grid_y = np.meshgrid(xs - origin[0], ys - origin[1])
    query = np.column_stack([grid_x.ravel(), grid_y.ravel()])

    tri = Delaunay(xy)
    corners = xy[tri.simplices]  # (triangles, 3 sommets, 2)
    longest_edge = np.linalg.norm(corners - np.roll(corners, 1, axis=1), axis=2).max(axis=1)

    simplex = tri.find_simplex(query)
    inside = simplex >= 0
    inside[inside] = longest_edge[simplex[inside]] <= max_edge
    kept = simplex[inside]

    # Coordonnées barycentriques (transformation affine précalculée par scipy)
    transform = tri.transform[kept]
    bary2 = np.einsum("nij,nj->ni", transform[:, :2], query[inside] - transform[:, 2])
    bary = np.column_stack([bary2, 1.0 - bary2.sum(axis=1)])

    z = np.full(len(query), np.nan)
    z[inside] = (points[tri.simplices[kept], 2] * bary).sum(axis=1)
    return z.astype(np.float32).reshape(shape)


def write_geotiff(
    dtm: npt.NDArray[np.float32], bounds: TileBounds, resolution: float, path: Path
) -> None:
    """Écrit le MNT en GeoTIFF Lambert 93 compressé (NaN → nodata)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "height": dtm.shape[0],
        "width": dtm.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": CRS.from_epsg(CRS_EPSG),
        "transform": from_origin(bounds.xmin, bounds.ymax, resolution, resolution),
        "nodata": DTM_NODATA,
        "compress": "deflate",
        "predictor": 3,  # prédicteur flottant : meilleure compression des altitudes
        "tiled": True,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(np.where(np.isnan(dtm), DTM_NODATA, dtm).astype(np.float32), 1)


def build_vrt(tif_paths: Sequence[Path], vrt_path: Path) -> None:
    """Mosaïque virtuelle GDAL (.vrt) de GeoTIFF jointifs de même résolution.

    Le .vrt ne contient que des références (chemins relatifs) : ouvrable dans QGIS
    comme un raster unique, sans dupliquer les données.
    """
    metas = []
    for path in tif_paths:
        with rasterio.open(path) as src:
            metas.append((path, src.bounds, src.width, src.height, src.res[0]))
    resolution = metas[0][4]
    xmin = min(m[1].left for m in metas)
    ymax = max(m[1].top for m in metas)
    width = round((max(m[1].right for m in metas) - xmin) / resolution)
    height = round((ymax - min(m[1].bottom for m in metas)) / resolution)

    root = ET.Element("VRTDataset", rasterXSize=str(width), rasterYSize=str(height))
    ET.SubElement(root, "SRS").text = CRS.from_epsg(CRS_EPSG).to_wkt()
    ET.SubElement(root, "GeoTransform").text = f"{xmin}, {resolution}, 0, {ymax}, 0, {-resolution}"
    band = ET.SubElement(root, "VRTRasterBand", dataType="Float32", band="1")
    ET.SubElement(band, "NoDataValue").text = str(DTM_NODATA)
    for path, bounds, src_width, src_height, _ in metas:
        source = ET.SubElement(band, "SimpleSource")
        ET.SubElement(source, "SourceFilename", relativeToVRT="1").text = path.name
        ET.SubElement(source, "SourceBand").text = "1"
        x_size, y_size = str(src_width), str(src_height)
        ET.SubElement(source, "SrcRect", xOff="0", yOff="0", xSize=x_size, ySize=y_size)
        x_off = str(round((bounds.left - xmin) / resolution))
        y_off = str(round((ymax - bounds.top) / resolution))
        ET.SubElement(source, "DstRect", xOff=x_off, yOff=y_off, xSize=x_size, ySize=y_size)

    vrt_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(vrt_path, encoding="utf-8")


def generate_tile_dtm(
    tile_path: Path, tiles: Mapping[Path, TileBounds], out_dir: Path, overwrite: bool = False
) -> Path:
    """Génère le MNT 0.5 m d'une dalle et retourne le chemin du GeoTIFF.

    Parameters
    ----------
    tile_path
        Dalle à traiter.
    tiles
        Toutes les dalles disponibles et leur emprise (sources du tampon).
    out_dir
        Dossier de sortie.
    overwrite
        Si faux, une dalle déjà générée est conservée (reprise après interruption).
    """
    out_path = out_dir / f"mnt_{tile_id(tile_path)}.tif"
    if out_path.exists() and not overwrite:
        logger.info("MNT déjà présent, ignoré : %s", out_path.name)
        return out_path

    start = time.perf_counter()
    bounds = tiles[tile_path]
    ground = read_ground_points(tiles, bounds.buffered(TILE_BUFFER_M))
    decimated = decimate_points(ground, DECIMATION_CELL_M)
    xs, ys = pixel_centers(bounds, DTM_RESOLUTION_M)
    dtm = interpolate_tin(decimated, xs, ys, MAX_TIN_EDGE_M)
    write_geotiff(dtm, bounds, DTM_RESOLUTION_M, out_path)

    logger.info(
        "MNT %s : %d points sol → %d après décimation, %.1f %% nodata, %.0f s",
        out_path.name,
        len(ground),
        len(decimated),
        100 * np.isnan(dtm).mean(),
        time.perf_counter() - start,
    )
    return out_path


def generate_dtm(
    raw_dir: Path,
    out_dir: Path,
    overwrite: bool = False,
    tile_ids: Sequence[str] | None = None,
) -> Path:
    """Génère le MNT des dalles de ``raw_dir`` et la mosaïque .vrt.

    Parameters
    ----------
    raw_dir
        Dossier des dalles COPC.
    out_dir
        Dossier de sortie.
    overwrite
        Régénère les dalles déjà présentes.
    tile_ids
        Dalles à traiter (ex. ``["0860_6265"]``) ; toutes si ``None``. Les voisines
        restent lues pour le tampon.

    Returns
    -------
    pathlib.Path
        Chemin de la mosaïque virtuelle (toutes les dalles présentes dans ``out_dir``).

    Raises
    ------
    FileNotFoundError
        Si aucune dalle n'est trouvée (penser à ``dvc pull``).
    ValueError
        Si un identifiant de ``tile_ids`` ne correspond à aucune dalle.
    """
    all_paths = sorted(raw_dir.glob(TILE_GLOB))
    if not all_paths:
        raise FileNotFoundError(f"Aucune dalle {TILE_GLOB} dans {raw_dir} (dvc pull ?)")
    tiles = {path: tile_bounds_from_name(path) for path in all_paths}

    selected = all_paths
    if tile_ids is not None:
        by_id = {tile_id(path): path for path in all_paths}
        unknown = sorted(set(tile_ids) - by_id.keys())
        if unknown:
            raise ValueError(f"Dalles inconnues dans {raw_dir} : {', '.join(unknown)}")
        selected = [by_id[tid] for tid in tile_ids]

    for path in tqdm(selected, "MNT"):
        generate_tile_dtm(path, tiles, out_dir, overwrite)

    tif_paths = sorted(out_dir.glob("mnt_*.tif"))
    vrt_path = out_dir / DTM_VRT_NAME
    build_vrt(tif_paths, vrt_path)
    logger.info("Mosaïque : %s (%d dalles)", vrt_path, len(tif_paths))
    return vrt_path


def main(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description="MNT de référence 0.5 m (TIN, sol IGN)")
    parser.add_argument("--raw-dir", type=Path, default=RAW_LIDAR_DIR)
    parser.add_argument("--out-dir", type=Path, default=DTM_DIR)
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
    generate_dtm(args.raw_dir, args.out_dir, args.overwrite, args.tile_ids)


if __name__ == "__main__":
    main()
