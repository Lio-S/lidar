"""Tests du téléchargement des dalles IGN (lidar_arch.data.download), réseau simulé."""

from collections.abc import Callable
from fnmatch import fnmatch
from pathlib import Path
from urllib.error import URLError

import pytest

from lidar_arch.constants import TILE_GLOB
from lidar_arch.data import download
from lidar_arch.data.download import DALLES, PART_SUFFIX, download_all, download_dalle

NOM = DALLES[0]
CONTENU = b"dalle-laz"

FakeRetrieve = Callable[[str, Path], None]


def _ok(urls: list[str]) -> FakeRetrieve:
    """Faux urlretrieve : écrit CONTENU et note l'URL demandée."""

    def fake(url: str, path: Path) -> None:
        urls.append(url)
        Path(path).write_bytes(CONTENU)

    return fake


def _coupure(url: str, path: Path) -> None:
    """Faux urlretrieve : écriture partielle puis erreur réseau."""
    Path(path).write_bytes(CONTENU[:3])
    raise URLError("connexion perdue")


def test_liste_dalles_coherente() -> None:
    assert len(DALLES) == len(set(DALLES)) == 54
    assert all(fnmatch(nom, TILE_GLOB) for nom in DALLES)


def test_download_dalle_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []
    monkeypatch.setattr(download, "urlretrieve", _ok(urls))

    assert download_dalle(NOM, tmp_path)
    assert (tmp_path / NOM).read_bytes() == CONTENU
    assert not (tmp_path / (NOM + PART_SUFFIX)).exists()
    assert urls == [download.BASE_URL.format(bloc="OQ", nom=NOM)]


def test_download_dalle_deja_presente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / NOM).write_bytes(CONTENU)
    urls: list[str] = []
    monkeypatch.setattr(download, "urlretrieve", _ok(urls))

    assert download_dalle(NOM, tmp_path)
    assert urls == []  # aucun appel réseau


def test_download_dalle_vide_retelechargee(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / NOM).touch()
    monkeypatch.setattr(download, "urlretrieve", _ok([]))

    assert download_dalle(NOM, tmp_path)
    assert (tmp_path / NOM).read_bytes() == CONTENU


def test_download_dalle_coupure_ne_laisse_rien(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(download, "urlretrieve", _coupure)

    assert not download_dalle(NOM, tmp_path)
    assert list(tmp_path.iterdir()) == []  # ni dalle tronquée, ni .part


def test_download_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download, "urlretrieve", _ok([]))
    out = tmp_path / "raw"  # créé par download_all

    assert download_all(out, DALLES[:3]) == 3
    assert sorted(p.name for p in out.iterdir()) == sorted(DALLES[:3])


def test_main_succes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download, "urlretrieve", _ok([]))
    download.main(["--out-dir", str(tmp_path)])
    assert len(list(tmp_path.iterdir())) == len(DALLES)


def test_main_echec_code_sortie(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download, "urlretrieve", _coupure)
    with pytest.raises(SystemExit) as exc:
        download.main(["--out-dir", str(tmp_path)])
    assert exc.value.code == 1
