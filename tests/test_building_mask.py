"""Tests du masque d'exclusion bâti (lidar_arch.data.building_mask)."""

from pathlib import Path

import numpy as np
import pytest
import rasterio

from lidar_arch.constants import (
    BUILDING_BUFFER_M,
    BUILDING_CLASSES,
    BUILDING_MASK_VRT_NAME,
    CLASS_SOL,
    MASK_EXCLUDED,
)
from lidar_arch.data import building_mask, dtm
from lidar_arch.data.building_mask import (
    buffer_mask,
    building_footprint,
    compute_building_mask,
    generate_building_mask,
    rasterize_points,
    write_mask,
)
from lidar_arch.data.dtm import TileBounds, build_vrt

TILE_NAME = "LHD_FXX_0860_6265_PTS_C_LAMB93_IGN69.copc.laz"


def _block(x0: float, x1: float, y0: float, y1: float, step: float = 0.25) -> np.ndarray:
    """Points (x, y, z) réguliers sur un rectangle : un « toit »."""
    gx, gy = np.meshgrid(np.arange(x0, x1, step), np.arange(y0, y1, step))
    return np.column_stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)])


def test_rasterize_points_orientation_et_hors_emprise() -> None:
    points = np.array([[0.1, 1.9, 0.0], [1.9, 0.1, 0.0], [5.0, 5.0, 0.0], [2.0, 1.0, 0.0]])
    grid = rasterize_points(points, TileBounds(0.0, 0.0, 2.0, 2.0), 0.5)

    assert grid.shape == (4, 4)
    assert grid[0, 0] and grid[3, 3]  # nord-ouest en haut à gauche, sud-est en bas à droite
    assert grid.sum() == 2  # (5, 5) et le bord est x = 2 sont hors grille


def test_building_footprint_ferme_les_toits_et_ecarte_le_bruit() -> None:
    occupancy = np.zeros((40, 40), dtype=bool)
    occupancy[10:20, 10:20] = True
    occupancy[12:18:2, 12:18:2] = False  # pixels de toit sans point
    occupancy[30, 30] = True  # point isolé mal classé

    footprint = building_footprint(occupancy, resolution=0.5, closing_m=1.0, min_area_m2=10.0)

    assert footprint[10:20, 10:20].all()
    assert not footprint[30, 30]


def test_buffer_mask_distance() -> None:
    footprint = np.zeros((21, 21), dtype=bool)
    footprint[10, 10] = True
    mask = buffer_mask(footprint, resolution=1.0, buffer_m=5.0)

    assert mask[10, 15] and mask[10, 5]  # à 5 m : inclus
    assert not mask[10, 16]  # à 6 m : exclu du tampon
    assert not buffer_mask(np.zeros((3, 3), dtype=bool), 1.0, 5.0).any()


def test_compute_building_mask_tampon_et_bati_voisin() -> None:
    bounds = TileBounds(0.0, 0.0, 100.0, 100.0)
    points = np.concatenate(
        [
            _block(45.0, 55.0, 45.0, 55.0),  # bâtiment au centre
            _block(-6.0, -1.0, 10.0, 20.0),  # bâtiment sur la dalle voisine, à 1 m du bord
            np.array([[80.0, 80.0, 0.0]]),  # point isolé
        ]
    )
    mask = compute_building_mask(points, bounds, 0.5)

    def at(x: float, y: float) -> bool:
        return bool(mask[int((100.0 - y) / 0.5), int(x / 0.5)])

    assert mask.shape == (200, 200)
    assert at(50.0, 50.0)  # le bâtiment
    assert at(55.0 + BUILDING_BUFFER_M - 1.0, 50.0)  # dans le tampon
    assert not at(55.0 + BUILDING_BUFFER_M + 1.0, 50.0)  # au-delà du tampon
    assert at(0.25, 15.0)  # tampon du bâtiment voisin : continuité au raccord
    assert not at(80.0, 80.0)  # le point isolé n'est pas masqué


def test_compute_building_mask_marge_nulle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans tampon ni fermeture, la marge vaut 0 : le masque garde la taille de la dalle."""
    monkeypatch.setattr(building_mask, "BUILDING_BUFFER_M", 0.0)
    monkeypatch.setattr(building_mask, "BUILDING_CLOSING_M", 0.0)
    bounds = TileBounds(0.0, 0.0, 100.0, 100.0)
    mask = compute_building_mask(_block(45.0, 55.0, 45.0, 55.0), bounds, 0.5)

    assert mask.shape == (200, 200)
    assert mask[100, 100] and not mask[0, 0]


def test_write_mask_et_mosaique_uint8(tmp_path: Path) -> None:
    ouest, est = TileBounds(0.0, 0.0, 1.0, 1.0), TileBounds(1.0, 0.0, 2.0, 1.0)
    write_mask(np.array([[True, False], [False, False]]), ouest, 0.5, tmp_path / "a.tif")
    write_mask(np.zeros((2, 2), dtype=bool), est, 0.5, tmp_path / "b.tif")
    vrt = tmp_path / "masque.vrt"
    build_vrt([tmp_path / "a.tif", tmp_path / "b.tif"], vrt)

    with rasterio.open(vrt) as src:
        assert src.dtypes[0] == "uint8"
        assert src.nodata is None
        np.testing.assert_array_equal(src.read(1), [[MASK_EXCLUDED, 0, 0, 0], [0, 0, 0, 0]])


# --- Chaîne complète ----------------------------------------------------------


@pytest.fixture
def bati_au_raccord(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Deux dalles factices, un bâtiment à cheval sur leur raccord ; grille de 5 m."""
    monkeypatch.setattr(building_mask, "DTM_RESOLUTION_M", 5.0)

    def fake_read(path: Path, bounds: TileBounds) -> np.ndarray:
        roof = _block(860_990.0, 861_010.0, 6_264_490.0, 6_264_510.0, step=1.0)
        roof = roof[bounds.contains(roof[:, 0], roof[:, 1])]
        ground = np.array([[860_100.0, 6_264_100.0, 0.0, CLASS_SOL]])
        return np.concatenate(
            [np.column_stack([roof[:, :3], np.full(len(roof), BUILDING_CLASSES[0])]), ground]
        )

    monkeypatch.setattr(dtm, "read_tile_points", fake_read)
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    for name in [TILE_NAME, TILE_NAME.replace("0860", "0861")]:
        (raw_dir / name).touch()
    return raw_dir


def test_generate_building_mask_chaine_complete(bati_au_raccord: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "masque"
    vrt = generate_building_mask(bati_au_raccord, out_dir)

    assert vrt == out_dir / BUILDING_MASK_VRT_NAME
    assert sorted(p.name for p in out_dir.glob("*.tif")) == [
        "masque_bati_0860_6265.tif",
        "masque_bati_0861_6265.tif",
    ]
    with rasterio.open(vrt) as src:
        mask = src.read(1)
        assert (src.width, src.height) == (400, 200)
    row = 100  # y = 6 264 500, milieu du bâtiment
    assert mask[row, 199] == mask[row, 200] == MASK_EXCLUDED  # de part et d'autre du raccord
    assert mask[row, 0] == 0 and mask[0, 0] == 0  # sol nu loin du bâti


def test_generate_building_mask_reprise_et_une_dalle(bati_au_raccord: Path, tmp_path: Path) -> None:
    out_dir = tmp_path / "masque"
    building_mask.main(
        ["--raw-dir", str(bati_au_raccord), "--out-dir", str(out_dir), "--tile", "0861_6265"]
    )
    tif = out_dir / "masque_bati_0861_6265.tif"
    assert [p.name for p in out_dir.glob("*.tif")] == [tif.name]

    mtime = tif.stat().st_mtime_ns
    generate_building_mask(bati_au_raccord, out_dir, tile_ids=["0861_6265"])
    assert tif.stat().st_mtime_ns == mtime  # déjà présent : conservé
    generate_building_mask(bati_au_raccord, out_dir, overwrite=True, tile_ids=["0861_6265"])
    assert tif.stat().st_mtime_ns != mtime
