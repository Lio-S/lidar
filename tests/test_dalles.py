"""Tests du remplissage de la table `dalles` (lidar_arch.db.dalles)."""

from pathlib import Path

import duckdb
import laspy
import numpy as np
import pytest

from lidar_arch.data.dtm import TileBounds, tile_dtm_path, write_geotiff
from lidar_arch.db import dalles
from lidar_arch.db.dalles import (
    count_classes,
    dalle_record,
    dtm_nodata_pct,
    populate_dalles,
    stable_id,
)

TILE_NAME = "LHD_FXX_0860_6265_PTS_C_LAMB93_IGN69.copc.laz"
# sol ×2, classe 65, végétation basse/moyenne/haute, bâtiment, eau, non classé
CLASSES = [2, 2, 65, 3, 4, 5, 6, 9, 1]
Z_MIN, Z_MAX = -1.5, 42.0


def _write_tile(path: Path, classes: list[int] = CLASSES) -> Path:
    """Petite dalle LAZ synthétique (points au centre de l'emprise 0860_6265)."""
    header = laspy.LasHeader(point_format=6, version="1.4")
    header.offsets = np.array([860_000.0, 6_264_000.0, 0.0])
    header.scales = np.array([0.01, 0.01, 0.01])
    las = laspy.LasData(header)
    n = len(classes)
    las.x = np.full(n, 860_500.0)
    las.y = np.full(n, 6_264_500.0)
    las.z = np.linspace(Z_MIN, Z_MAX, n)
    las.classification = np.array(classes, dtype=np.uint8)
    path.parent.mkdir(parents=True, exist_ok=True)
    las.write(path)
    return path


def _write_dtm(dtm_dir: Path, code: str = "0860_6265") -> Path:
    """MNT 2×2 dont un pixel nodata (25 %)."""
    data = np.array([[1.0, np.nan], [3.0, 4.0]], dtype=np.float32)
    path = tile_dtm_path(dtm_dir, code)
    write_geotiff(data, TileBounds(0.0, 0.0, 1.0, 1.0), 0.5, path)
    return path


def test_stable_id() -> None:
    assert stable_id("0860_6265") == 8_606_265


def test_count_classes_par_blocs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dalles, "LAS_CHUNK_POINTS", 2)  # force plusieurs blocs
    counts = count_classes(_write_tile(tmp_path / TILE_NAME))
    assert counts.sum() == len(CLASSES)
    assert (counts[2], counts[65], counts[6], counts[1]) == (2, 1, 1, 1)


def test_dtm_nodata_pct(tmp_path: Path) -> None:
    assert dtm_nodata_pct(_write_dtm(tmp_path)) == pytest.approx(25.0)


def test_dalle_record_sans_mnt(tmp_path: Path) -> None:
    record = dalle_record(_write_tile(tmp_path / TILE_NAME), tmp_path / "dtm")

    assert record["id"] == 8_606_265
    assert record["code"] == "0860_6265"
    assert (record["x_min"], record["y_max"]) == (860_000.0, 6_265_000.0)
    assert record["z_min"] == pytest.approx(Z_MIN)
    assert record["z_max"] == pytest.approx(Z_MAX)
    assert record["nb_points"] == len(CLASSES)
    assert (record["nb_sol"], record["nb_classe_65"]) == (2, 1)
    assert (record["nb_vegetation"], record["nb_batiment"], record["nb_eau"]) == (3, 1, 1)
    assert record["densite_sol"] == pytest.approx(3 / 1e6)  # 3 points sol sur 1 km²
    assert record["chemin_mnt"] is None
    assert record["pct_nodata_mnt"] is None
    assert record["statut"] == "telecharge"


def test_dalle_record_avec_mnt(tmp_path: Path) -> None:
    tif = _write_dtm(tmp_path / "dtm")
    record = dalle_record(_write_tile(tmp_path / TILE_NAME), tmp_path / "dtm")

    assert record["chemin_mnt"] == str(tif)
    assert record["pct_nodata_mnt"] == pytest.approx(25.0)
    assert record["statut"] == "mnt_genere"


def test_populate_dalles_idempotent_et_mise_a_jour(tmp_path: Path) -> None:
    raw_dir, dtm_dir, db = tmp_path / "raw", tmp_path / "dtm", tmp_path / "test.duckdb"
    _write_tile(raw_dir / TILE_NAME)
    _write_tile(raw_dir / TILE_NAME.replace("0860", "0861"))

    assert populate_dalles(raw_dir, dtm_dir, db) == 2
    with duckdb.connect(str(db)) as conn:
        # une détection référence la dalle : la mise à jour ne doit pas casser la clé étrangère
        conn.execute("INSERT INTO detections (id, dalle_id, score) VALUES (1, 8606265, 0.9)")

    _write_dtm(dtm_dir)  # le MNT de 0860_6265 apparaît entre deux passages
    populate_dalles(raw_dir, dtm_dir, db)

    with duckdb.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT code, statut, pct_nodata_mnt FROM dalles ORDER BY id"
        ).fetchall()
    assert rows == [
        ("0860_6265", "mnt_genere", pytest.approx(25.0)),
        ("0861_6265", "telecharge", None),
    ]


def test_populate_dalles_sans_dalle(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="dvc pull"):
        populate_dalles(tmp_path, tmp_path / "dtm", tmp_path / "test.duckdb")


def test_main(tmp_path: Path) -> None:
    raw_dir, db = tmp_path / "raw", tmp_path / "test.duckdb"
    _write_tile(raw_dir / TILE_NAME)
    dalles.main(["--raw-dir", str(raw_dir), "--dtm-dir", str(tmp_path / "dtm"), "--db", str(db)])

    with duckdb.connect(str(db)) as conn:
        assert conn.execute("SELECT count(*) FROM dalles").fetchone() == (1,)
