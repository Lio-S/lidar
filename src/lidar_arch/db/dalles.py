"""Remplissage de la table ``dalles`` : métadonnées des dalles IGN et de leur MNT.

Sources, pour chaque dalle :

- nom de fichier → code ``XXXX_YYYY``, emprise Lambert 93, id stable ;
- en-tête LAS → altitudes extrêmes ;
- points (lecture par blocs) → nombre de points par classe, densité sol ;
- MNT GeoTIFF (s'il existe) → pourcentage de nodata.

Idempotent : une dalle déjà présente est mise à jour (``ON CONFLICT (id) DO UPDATE``),
y compris si des détections la référencent.

Usage : ``python -m lidar_arch.db.dalles`` (après ``dvc pull`` et ``dvc repro``).
"""

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path

import duckdb
import laspy
import numpy as np
import numpy.typing as npt
import rasterio
from tqdm import tqdm

from lidar_arch.constants import (
    BYTES_PER_MB,
    CLASS_65,
    CLASS_BATIMENT,
    CLASS_EAU,
    CLASS_SOL,
    DTM_DIR,
    GROUND_CLASSES,
    IGN_BLOC,
    LAS_CHUNK_POINTS,
    LAS_CLASS_COUNT,
    RAW_LIDAR_DIR,
    TILE_GLOB,
    TILE_ID_FACTOR,
    VEGETATION_CLASSES,
)
from lidar_arch.data.dtm import tile_bounds_from_name, tile_dtm_path, tile_id
from lidar_arch.db.schema import DB_PATH, init_db
from lidar_arch.logging_config import configure_logging, get_logger

logger = get_logger("lidar_arch.db.dalles")

DalleRecord = dict[str, object]

# Colonnes dérivées du nom de fichier : identiques à chaque passage, jamais mises à jour
_KEY_COLUMNS = ("id", "nom", "code")


def stable_id(code: str) -> int:
    """Identifiant entier stable d'une dalle.

    Examples
    --------
    >>> stable_id("0860_6265")
    8606265
    """
    x_km, y_km = (int(v) for v in code.split("_"))
    return x_km * TILE_ID_FACTOR + y_km


def count_classes(laz_path: Path) -> npt.NDArray[np.int64]:
    """Nombre de points par code de classification (tableau indexé par la classe)."""
    counts = np.zeros(LAS_CLASS_COUNT, dtype=np.int64)
    with laspy.open(laz_path) as reader:
        for chunk in reader.chunk_iterator(LAS_CHUNK_POINTS):
            classes = np.asarray(chunk.classification, dtype=np.int64)
            counts += np.bincount(classes, minlength=LAS_CLASS_COUNT)
    return counts


def dtm_nodata_pct(tif_path: Path) -> float:
    """Pourcentage de pixels nodata d'un MNT GeoTIFF."""
    with rasterio.open(tif_path) as src:
        valid = src.read_masks(1)  # 0 = nodata, 255 = valeur
    return float(100.0 * np.mean(valid == 0))


def dalle_record(laz_path: Path, dtm_dir: Path) -> DalleRecord:
    """Ligne de la table ``dalles`` pour une dalle LiDAR (et son MNT s'il existe)."""
    code = tile_id(laz_path)
    bounds = tile_bounds_from_name(laz_path)
    with laspy.open(laz_path) as reader:
        z_min, z_max = float(reader.header.mins[2]), float(reader.header.maxs[2])
    counts = count_classes(laz_path)
    area_m2 = (bounds.xmax - bounds.xmin) * (bounds.ymax - bounds.ymin)
    tif_path = tile_dtm_path(dtm_dir, code)
    has_dtm = tif_path.exists()

    return {
        "id": stable_id(code),
        "nom": laz_path.name,
        "code": code,
        "bloc": IGN_BLOC,
        "x_min": bounds.xmin,
        "y_min": bounds.ymin,
        "x_max": bounds.xmax,
        "y_max": bounds.ymax,
        "z_min": z_min,
        "z_max": z_max,
        "nb_points": int(counts.sum()),
        "nb_sol": int(counts[CLASS_SOL]),
        "nb_classe_65": int(counts[CLASS_65]),
        "nb_vegetation": int(counts[list(VEGETATION_CLASSES)].sum()),
        "nb_batiment": int(counts[CLASS_BATIMENT]),
        "nb_eau": int(counts[CLASS_EAU]),
        "densite_sol": float(counts[list(GROUND_CLASSES)].sum() / area_m2),
        "taille_mo": laz_path.stat().st_size / BYTES_PER_MB,
        "chemin_laz": str(laz_path),
        "chemin_mnt": str(tif_path) if has_dtm else None,
        "pct_nodata_mnt": dtm_nodata_pct(tif_path) if has_dtm else None,
        "statut": "mnt_genere" if has_dtm else "telecharge",
    }


def upsert_dalles(conn: duckdb.DuckDBPyConnection, records: Sequence[Mapping[str, object]]) -> None:
    """Insère les dalles, ou met à jour celles déjà présentes (même id)."""
    if not records:
        return
    columns = list(records[0])
    updates = [f"{col} = excluded.{col}" for col in columns if col not in _KEY_COLUMNS]
    sql = (
        f"INSERT INTO dalles ({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))}) "
        f"ON CONFLICT (id) DO UPDATE SET {', '.join(updates)}, date_maj = now()"
    )
    conn.executemany(sql, [[record[col] for col in columns] for record in records])


def populate_dalles(raw_dir: Path, dtm_dir: Path, db_path: Path) -> int:
    """Remplit la table ``dalles`` depuis toutes les dalles de ``raw_dir``.

    Returns
    -------
    int
        Nombre de dalles enregistrées.

    Raises
    ------
    FileNotFoundError
        Si aucune dalle n'est trouvée (penser à ``dvc pull``).
    """
    laz_paths = sorted(raw_dir.glob(TILE_GLOB))
    if not laz_paths:
        raise FileNotFoundError(f"Aucune dalle {TILE_GLOB} dans {raw_dir} (dvc pull ?)")

    records = [dalle_record(path, dtm_dir) for path in tqdm(laz_paths, "Dalles")]
    conn = init_db(db_path)
    try:
        upsert_dalles(conn, records)
    finally:
        conn.close()
    with_dtm = sum(record["statut"] == "mnt_genere" for record in records)
    logger.info("Table dalles : %d dalles (%d avec MNT) → %s", len(records), with_dtm, db_path)
    return len(records)


def main(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description="Remplit la table DuckDB `dalles`")
    parser.add_argument("--raw-dir", type=Path, default=RAW_LIDAR_DIR)
    parser.add_argument("--dtm-dir", type=Path, default=DTM_DIR)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args(argv)

    configure_logging()
    populate_dalles(args.raw_dir, args.dtm_dir, args.db)


if __name__ == "__main__":
    main()
