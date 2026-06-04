"""Reclassification du sol — PDAL CLI via subprocess.

Remplace la classification IGN par une extraction sol indépendante.
La classe Sol IGN contient des artefacts côtiers (points dans l'eau,
plage mélangée à des affleurements) qui corrompent le MNT archéologique.

Dépendance système : `pdal` (apt, PPA ubuntugis-unstable).
Paramètres CSF vérifiés via `pdal --options filters.csf` (PDAL 2.6.2).
"""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import laspy
from tqdm import tqdm

# Paramètres CSF calibrés pour la détection archéologique en garrigue.
# Threshold serré pour préserver les micro-reliefs (murets, fossés < 50cm).
_THRESHOLD = 0.1   # seuil vertical sol/cloth (m) — défaut PDAL : 0.5
_RESOLUTION = 0.5  # résolution de la cloth (m) — cohérente avec MNT principal
_SMOOTH = True     # post-traitement des pentes du promontoire
_RIGIDNESS = 3     # rigidité du cloth (1=souple, 3=rigide) — défaut PDAL

_GROUND_CLASS = 2


def reclassify_ground(input_path: Path, output_path: Path) -> int:
    """Reclassifie les points sol d'une dalle LAZ via PDAL filtre CSF.

    Parameters
    ----------
    input_path : Path
        Dalle source (classification IGN ignorée et réinitialisée).
    output_path : Path
        Dalle résultat avec sol reclassifié (classe 2).

    Returns
    -------
    int
        Nombre de points classifiés sol.

    Raises
    ------
    RuntimeError
        Si PDAL échoue avec le message d'erreur complet.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reader = "readers.copc" if ".copc." in input_path.name else "readers.las"
    pipeline_def = [
        {"type": reader, "filename": str(input_path)},
        # Réinitialise toutes les classes IGN avant de reclassifier.
        {"type": "filters.assign", "assignment": "Classification[:]=0"},
        {
            "type": "filters.csf",
            "resolution": _RESOLUTION,
            "threshold": _THRESHOLD,
            "smooth": _SMOOTH,
            "rigidness": _RIGIDNESS,
        },
        {"type": "writers.copc", "filename": str(output_path)},
    ]

    result = subprocess.run(
        ["pdal", "pipeline", "--stdin"],
        input=json.dumps(pipeline_def),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"PDAL pipeline failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")

    las = laspy.read(output_path)
    return int((las.classification == _GROUND_CLASS).sum())


def reclassify_all(
    input_dir: Path,
    output_dir: Path,
    *,
    pattern: str = "*.laz",
    workers: int | None = None,
) -> dict[str, int]:
    """Reclassifie toutes les dalles d'un répertoire en parallèle.

    Parameters
    ----------
    input_dir : Path
        Répertoire contenant les dalles LAZ sources.
    output_dir : Path
        Répertoire de sortie pour les dalles reclassifiées.
    pattern : str
        Glob pattern pour sélectionner les dalles.
    workers : int | None
        Nombre de threads parallèles. None = os.cpu_count().

    Returns
    -------
    dict[str, int]
        Mapping nom_dalle → nombre de points sol.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    dalles = sorted(input_dir.glob(pattern))
    todo = [
        (d, output_dir / d.name)
        for d in dalles
    ]
    pending = [(d, o) for d, o in todo if not (o.exists() and o.stat().st_size > 0)]
    skipped = len(todo) - len(pending)

    if skipped:
        print(f"  → {skipped} dalle(s) déjà traitées, ignorées")
    print(f"Reclassification de {len(pending)}/{len(dalles)} dalle(s) — {workers or os.cpu_count()} workers\n")

    if not pending:
        return {}

    results: dict[str, int] = {}
    n_workers = workers or os.cpu_count() or 4
    # n_workers = workers or min(4, os.cpu_count() or 4)

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = {
            executor.submit(reclassify_ground, dalle, out): dalle
            for dalle, out in pending
        }
        with tqdm(total=len(pending), unit="dalle") as pbar:
            for future in as_completed(futures):
                dalle = futures[future]
                try:
                    n_ground = future.result()
                    pbar.set_postfix_str(dalle.name[:30])
                    results[dalle.name] = n_ground
                except Exception as e:
                    tqdm.write(f"  ✗ {dalle.name} — erreur : {e}")
                finally:
                    pbar.update(1)

    return results


def main() -> None:
    input_dir = Path("./data/raw/lidar/saint_blaise")
    output_dir = Path("./data/processed/lidar/reclassified")
    reclassify_all(input_dir, output_dir, pattern="*.copc.laz")


if __name__ == "__main__":
    main()
