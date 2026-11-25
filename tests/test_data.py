"""Tests de la génération du MNT de référence (lidar_arch.data.dtm)."""

from pathlib import Path

import numpy as np
import pytest
import rasterio

from lidar_arch.constants import (
    DTM_NODATA,
    DTM_OVERVIEW_FACTORS,
    DTM_VRT_NAME,
    GROUND_CLASSES,
    RAW_LIDAR_DIR,
)
from lidar_arch.data import dtm
from lidar_arch.data.dtm import (
    TileBounds,
    build_vrt,
    decimate_points,
    generate_dtm,
    interpolate_tin,
    pixel_centers,
    read_ground_points,
    tile_bounds_from_name,
    tile_id,
    write_geotiff,
)

TILE_NAME = "LHD_FXX_0860_6265_PTS_C_LAMB93_IGN69.copc.laz"
NON_GROUND_CLASS = 5  # végétation haute
SLOPE_X, SLOPE_Y, Z0 = 0.01, -0.02, 10.0


def _plane(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Terrain synthétique : plan incliné (le TIN linéaire doit le restituer exactement)."""
    return SLOPE_X * (x - 860_000) + SLOPE_Y * (y - 6_264_000) + Z0


# --- Nom et emprise des dalles ----------------------------------------------


def test_tile_id_extrait_les_coordonnees() -> None:
    assert tile_id(Path(TILE_NAME)) == "0860_6265"


def test_tile_id_nom_invalide() -> None:
    with pytest.raises(ValueError, match="non reconnu"):
        tile_id(Path("dalle.laz"))


def test_tile_bounds_coin_haut_gauche() -> None:
    assert tile_bounds_from_name(Path(TILE_NAME)) == TileBounds(
        860_000.0, 6_264_000.0, 861_000.0, 6_265_000.0
    )


def test_bounds_buffered_intersects_contains() -> None:
    bounds = TileBounds(0.0, 0.0, 10.0, 10.0)
    assert bounds.buffered(2.0) == TileBounds(-2.0, -2.0, 12.0, 12.0)
    assert bounds.intersects(TileBounds(5.0, 5.0, 15.0, 15.0))
    assert not bounds.intersects(TileBounds(10.0, 0.0, 20.0, 10.0))  # bord commun seul
    mask = bounds.contains(np.array([0.0, 10.0, 10.1]), np.array([5.0, 5.0, 5.0]))
    assert mask.tolist() == [True, True, False]


# --- Lecture des points sol ---------------------------------------------------


def test_read_ground_points_filtre_classes_et_dalles(monkeypatch: pytest.MonkeyPatch) -> None:
    lues: list[Path] = []

    def fake_read(path: Path, bounds: TileBounds) -> np.ndarray:
        lues.append(path)
        classes = [GROUND_CLASSES[0], GROUND_CLASSES[1], NON_GROUND_CLASS]
        return np.array([[1.0, 1.0, 5.0, c] for c in classes])

    monkeypatch.setattr(dtm, "read_tile_points", fake_read)
    tiles = {
        Path("proche.laz"): TileBounds(0.0, 0.0, 10.0, 10.0),
        Path("loin.laz"): TileBounds(100.0, 100.0, 110.0, 110.0),
    }
    points = read_ground_points(tiles, TileBounds(-1.0, -1.0, 11.0, 11.0))

    assert lues == [Path("proche.laz")]
    assert points.shape == (2, 3)


def test_read_ground_points_aucune_dalle() -> None:
    assert read_ground_points({}, TileBounds(0.0, 0.0, 1.0, 1.0)).shape == (0, 3)


@pytest.mark.skipif(
    not (RAW_LIDAR_DIR / TILE_NAME).exists(), reason="dalle réelle absente (dvc pull)"
)
def test_read_tile_points_dalle_reelle() -> None:
    bounds = TileBounds(860_000.0, 6_264_000.0, 860_020.0, 6_265_000.0)
    points = dtm.read_tile_points(RAW_LIDAR_DIR / TILE_NAME, bounds)
    assert points.shape[1] == 4
    assert bounds.contains(points[:, 0], points[:, 1]).all()


# --- Décimation, grille, interpolation ---------------------------------------


def test_decimate_points_moyenne_par_cellule() -> None:
    points = np.array([[0.1, 0.1, 1.0], [0.3, 0.3, 3.0], [1.2, 0.1, 7.0]])
    result = decimate_points(points, cell_size=0.5)
    result = result[np.argsort(result[:, 0])]
    np.testing.assert_allclose(result, [[0.2, 0.2, 2.0], [1.2, 0.1, 7.0]])


def test_decimate_points_vide() -> None:
    assert decimate_points(np.empty((0, 3)), 0.5).shape == (0, 3)


def test_pixel_centers_orientation() -> None:
    xs, ys = pixel_centers(TileBounds(0.0, 0.0, 2.0, 1.0), resolution=0.5)
    np.testing.assert_allclose(xs, [0.25, 0.75, 1.25, 1.75])
    np.testing.assert_allclose(ys, [0.75, 0.25])  # nord → sud


def test_interpolate_tin_restitue_un_plan() -> None:
    gx, gy = np.meshgrid(np.arange(0.0, 21.0, 2.0), np.arange(0.0, 21.0, 2.0))
    points = np.column_stack([gx.ravel(), gy.ravel(), 2.0 * gx.ravel() + gy.ravel()])
    xs, ys = np.array([1.0, 5.5, 19.0]), np.array([3.0, 0.5])
    grid = interpolate_tin(points, xs, ys, max_edge=5.0)

    assert grid.shape == (2, 3)
    assert grid.dtype == np.float32
    np.testing.assert_allclose(grid, 2.0 * xs[np.newaxis, :] + ys[:, np.newaxis], rtol=1e-6)


def test_interpolate_tin_masque_longs_triangles_et_point_isole() -> None:
    gx, gy = np.meshgrid(np.arange(0.0, 11.0, 2.0), np.arange(0.0, 11.0, 2.0))
    terre = np.column_stack([gx.ravel(), gy.ravel(), np.ones(gx.size)])
    point_isole = np.array([[50.0, 5.0, 1.0]])  # retour parasite sur l'eau
    points = np.vstack([terre, point_isole])
    xs = np.array([5.0, 30.0, 49.5, 100.0])
    grid = interpolate_tin(points, xs, np.array([5.0]), max_edge=5.0)

    # terre → valeur ; vers le point isolé (longs triangles) → NaN ; hors enveloppe → NaN
    assert grid[0, 0] == pytest.approx(1.0)
    assert np.isnan(grid[0, 1:]).all()


def test_interpolate_tin_trop_peu_de_points() -> None:
    grid = interpolate_tin(np.zeros((2, 3)), np.arange(4.0), np.arange(3.0), max_edge=1.0)
    assert grid.shape == (3, 4)
    assert np.isnan(grid).all()


# --- Écriture GeoTIFF et mosaïque ---------------------------------------------


def test_write_geotiff_georeference_et_nodata(tmp_path: Path) -> None:
    data = np.array([[1.0, np.nan], [3.0, 4.0]], dtype=np.float32)
    bounds = TileBounds(860_000.0, 6_264_999.0, 860_001.0, 6_265_000.0)
    path = tmp_path / "sous" / "mnt.tif"
    write_geotiff(data, bounds, 0.5, path)

    with rasterio.open(path) as src:
        assert src.crs.to_epsg() == 2154
        assert src.res == (0.5, 0.5)
        assert (src.bounds.left, src.bounds.top) == (860_000.0, 6_265_000.0)
        assert src.nodata == DTM_NODATA
        assert src.read(1)[0, 1] == DTM_NODATA
        assert np.isnan(src.read(1, masked=True).filled(np.nan)[0, 1])
        assert src.overviews(1) == [2]  # 2×2 px : ÷4 et au-delà impossibles


def test_write_geotiff_apercus_complets(tmp_path: Path) -> None:
    size = max(DTM_OVERVIEW_FACTORS)
    path = tmp_path / "mnt.tif"
    write_geotiff(np.ones((size, size), np.float32), TileBounds(0.0, 0.0, 8.0, 8.0), 0.5, path)

    with rasterio.open(path) as src:
        assert src.overviews(1) == list(DTM_OVERVIEW_FACTORS)


def test_build_vrt_assemble_deux_dalles(tmp_path: Path) -> None:
    ouest = TileBounds(0.0, 0.0, 1.0, 1.0)
    est = TileBounds(1.0, 0.0, 2.0, 1.0)
    write_geotiff(np.full((2, 2), 1.0, np.float32), ouest, 0.5, tmp_path / "a.tif")
    write_geotiff(np.full((2, 2), 2.0, np.float32), est, 0.5, tmp_path / "b.tif")
    vrt = tmp_path / "mosaique.vrt"
    build_vrt([tmp_path / "a.tif", tmp_path / "b.tif"], vrt)

    with rasterio.open(vrt) as src:
        assert src.crs.to_epsg() == 2154
        assert (src.width, src.height) == (4, 2)
        np.testing.assert_array_equal(src.read(1), [[1, 1, 2, 2], [1, 1, 2, 2]])


# --- Chaîne complète ----------------------------------------------------------


@pytest.fixture
def plan_synthetique(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Deux dalles factices sur un plan incliné ; grille grossière pour un test rapide."""
    monkeypatch.setattr(dtm, "DTM_RESOLUTION_M", 50.0)
    monkeypatch.setattr(dtm, "DECIMATION_CELL_M", 5.0)

    def fake_read(path: Path, bounds: TileBounds) -> np.ndarray:
        gx, gy = np.meshgrid(
            np.arange(bounds.xmin, bounds.xmax + 1, 5.0),
            np.arange(bounds.ymin, bounds.ymax + 1, 5.0),
        )
        x, y = gx.ravel(), gy.ravel()
        return np.column_stack([x, y, _plane(x, y), np.full(x.shape, GROUND_CLASSES[0])])

    monkeypatch.setattr(dtm, "read_tile_points", fake_read)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for name in [TILE_NAME, TILE_NAME.replace("0860", "0861")]:
        (raw_dir / name).touch()
    return raw_dir


def test_generate_dtm_chaine_complete(plan_synthetique: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "dtm"
    vrt = generate_dtm(plan_synthetique, out_dir)

    assert vrt == out_dir / DTM_VRT_NAME
    assert sorted(p.name for p in out_dir.glob("*.tif")) == [
        "mnt_0860_6265.tif",
        "mnt_0861_6265.tif",
    ]
    with rasterio.open(vrt) as src:
        assert (src.width, src.height) == (40, 20)
        z = src.read(1)
        xs = src.bounds.left + (np.arange(src.width) + 0.5) * 50.0
        ys = src.bounds.top - (np.arange(src.height) + 0.5) * 50.0
        gx, gy = np.meshgrid(xs, ys)
        np.testing.assert_allclose(z, _plane(gx, gy), atol=1e-3)


def test_generate_dtm_ignore_dalles_existantes(plan_synthetique: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "dtm"
    generate_dtm(plan_synthetique, out_dir)
    tif = out_dir / "mnt_0860_6265.tif"
    mtime = tif.stat().st_mtime_ns

    generate_dtm(plan_synthetique, out_dir)
    assert tif.stat().st_mtime_ns == mtime
    dtm.main(["--raw-dir", str(plan_synthetique), "--out-dir", str(out_dir), "--overwrite"])
    assert tif.stat().st_mtime_ns != mtime


def test_generate_dtm_sans_dalle(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="dvc pull"):
        generate_dtm(tmp_path, tmp_path / "dtm")


def test_generate_dtm_une_seule_dalle(plan_synthetique: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "dtm"
    dtm.main(["--raw-dir", str(plan_synthetique), "--out-dir", str(out_dir), "--tile", "0861_6265"])

    assert [p.name for p in out_dir.glob("*.tif")] == ["mnt_0861_6265.tif"]
    with rasterio.open(out_dir / DTM_VRT_NAME) as src:
        assert (src.width, src.height) == (20, 20)


def test_generate_dtm_dalle_inconnue(plan_synthetique: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="9999_9999"):
        generate_dtm(plan_synthetique, tmp_path / "dtm", tile_ids=["9999_9999"])
