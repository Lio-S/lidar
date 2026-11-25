"""Tests du schéma DuckDB (tables dalles, sites, detections)."""

import runpy
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest

from lidar_arch.db.schema import init_db

EXPECTED_TABLES = {"dalles", "sites", "detections"}


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Base DuckDB temporaire, fermée après le test."""
    connection = init_db(tmp_path / "test.duckdb")
    yield connection
    connection.close()


def _tables(connection: duckdb.DuckDBPyConnection) -> set[str]:
    return {row[0] for row in connection.execute("SHOW TABLES").fetchall()}


def _insert_dalle(connection: duckdb.DuckDBPyConnection, id_: int, nom: str) -> None:
    connection.execute(
        "INSERT INTO dalles (id, nom, code, x_min, y_min, x_max, y_max)"
        " VALUES (?, ?, ?, 0, 0, 1000, 1000)",
        [id_, nom, f"code_{id_}"],
    )


def test_init_db_cree_les_trois_tables(conn: duckdb.DuckDBPyConnection) -> None:
    assert _tables(conn) == EXPECTED_TABLES


def test_init_db_cree_le_dossier_parent(tmp_path: Path) -> None:
    db_path = tmp_path / "sous" / "dossier" / "test.duckdb"
    init_db(db_path).close()
    assert db_path.exists()


def test_init_db_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.duckdb"
    init_db(db_path).close()
    connection = init_db(db_path)  # CREATE TABLE IF NOT EXISTS : pas d'erreur au 2e appel
    assert _tables(connection) == EXPECTED_TABLES
    connection.close()


def test_dalles_valeurs_par_defaut(conn: duckdb.DuckDBPyConnection) -> None:
    _insert_dalle(conn, 1, "dalle_a.copc.laz")
    bloc, statut = conn.execute("SELECT bloc, statut FROM dalles WHERE id = 1").fetchone() or ()
    assert bloc == "OQ"
    assert statut == "en_attente"


def test_dalles_nom_unique(conn: duckdb.DuckDBPyConnection) -> None:
    _insert_dalle(conn, 1, "dalle_a.copc.laz")
    with pytest.raises(duckdb.ConstraintException):
        _insert_dalle(conn, 2, "dalle_a.copc.laz")


def test_detections_refuse_dalle_inexistante(conn: duckdb.DuckDBPyConnection) -> None:
    with pytest.raises(duckdb.ConstraintException):
        conn.execute("INSERT INTO detections (id, dalle_id, score) VALUES (1, 999, 0.9)")


def test_detections_date_par_defaut(conn: duckdb.DuckDBPyConnection) -> None:
    _insert_dalle(conn, 1, "dalle_a.copc.laz")
    conn.execute("INSERT INTO detections (id, dalle_id, score) VALUES (1, 1, 0.9)")
    (date_detection,) = conn.execute(
        "SELECT date_detection FROM detections WHERE id = 1"
    ).fetchone() or (None,)
    assert date_detection is not None


# Avertissement attendu : le module est déjà importé par ce fichier de test avant runpy
@pytest.mark.filterwarnings("ignore:'lidar_arch.db.schema' found in sys.modules:RuntimeWarning")
def test_execution_en_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`python -m lidar_arch.db.schema` crée data/lidar_arch.duckdb dans le dossier courant."""
    monkeypatch.chdir(tmp_path)
    runpy.run_module("lidar_arch.db.schema", run_name="__main__")
    assert (tmp_path / "data" / "lidar_arch.duckdb").exists()
    assert "Tables créées" in capsys.readouterr().out
