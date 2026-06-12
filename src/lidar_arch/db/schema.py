"""Initialisation du schéma DuckDB — tables dalles, sites, detections."""

from pathlib import Path

import duckdb

DB_PATH = Path("data/lidar_arch.duckdb")

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS dalles (
        id                  INTEGER PRIMARY KEY,          -- identifiant interne auto-incrémenté
        nom                 VARCHAR NOT NULL UNIQUE,      -- nom IGN de la dalle, ex : LHD_FXX_0860_6265_PTS_C_LAMB93_IGN69.copc.laz
        bloc                VARCHAR NOT NULL DEFAULT 'OQ',-- bloc IGN (OQ = Bouches-du-Rhône)
        x_min               DOUBLE  NOT NULL,             -- coin bas-gauche en projection LAMB93 (mètres)
        y_min               DOUBLE  NOT NULL,
        x_max               DOUBLE  NOT NULL,             -- coin haut-droit en projection LAMB93 (mètres)
        y_max               DOUBLE  NOT NULL,
        chemin_local        VARCHAR,                      -- chemin absolu sur disque WSL2, null si non téléchargé
        chemin_gcs          VARCHAR,                      -- URI GCS après dvc push, ex : gs://projet-dvc/lidar/dalle.laz
        taille_mo           DOUBLE,                       -- taille du fichier .laz en Mo
        date_telechargement TIMESTAMP,                    -- horodatage du téléchargement IGN
        statut              VARCHAR DEFAULT 'en_attente'  -- cycle de vie : en_attente | telecharge | traite
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sites (
        id             INTEGER PRIMARY KEY,               -- identifiant interne
        nom            VARCHAR NOT NULL,                  -- nom du site, ex : 'Saint-Blaise — rempart hellénistique'
        type           VARCHAR,                           -- catégorie archéologique : rempart, habitat, fossé, nécropole…
        epoque         VARCHAR,                           -- période : protohistoire, antiquite, medieval, moderne
        geometrie_wkt  VARCHAR,                           -- emprise en WKT POLYGON, coordonnées LAMB93 (→ Spatial en Phase 2)
        source         VARCHAR,                           -- référence bibliographique ou cartographique (ex : BCH 2003)
        confiance      VARCHAR DEFAULT 'haute',           -- fiabilité du ground truth : haute | moyenne | faible
        notes          VARCHAR                            -- observations libres (fouilles, état de conservation…)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS detections (
        id             INTEGER PRIMARY KEY,               -- identifiant interne
        run_id         VARCHAR,                           -- UUID du run MLflow associé (métriques + hyperparamètres)
        dalle_id       INTEGER REFERENCES dalles(id),     -- dalle sur laquelle la structure a été détectée
        site_id        INTEGER REFERENCES sites(id),      -- site archéologique correspondant, null si non validé
        x_centroid     DOUBLE,                            -- centroïde X du polygone détecté, en LAMB93
        y_centroid     DOUBLE,                            -- centroïde Y du polygone détecté, en LAMB93
        geometrie_wkt  VARCHAR,                           -- contour de la détection en WKT POLYGON LAMB93
        score          DOUBLE,                            -- score de confiance du modèle [0.0 – 1.0]
        modele         VARCHAR,                           -- nom du modèle utilisé, ex : 'RandomForest_v1'
        date_detection TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        vrai_positif   BOOLEAN                            -- validation terrain : TRUE | FALSE | NULL (non encore vérifié)
    )
    """,
]


def init_db(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Crée les tables si elles n'existent pas et retourne la connexion."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    for ddl in _TABLES:
        conn.execute(ddl)
    return conn


if __name__ == "__main__":
    conn = init_db()
    tables = conn.execute("SHOW TABLES").fetchall()
    print("Tables créées :", [t[0] for t in tables])
    conn.close()
