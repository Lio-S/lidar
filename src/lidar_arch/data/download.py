"""Téléchargement des dalles IGN LiDAR HD de la zone Saint-Blaise.

Source : OVH Cloud Storage (hébergement officiel des dalles IGN LiDAR HD).
Les dalles sont ensuite versionnées par DVC : en usage normal, ``dvc pull`` suffit.

Reprise sûre : chaque dalle est écrite dans un fichier ``.part`` puis renommée,
une interruption ne laisse donc jamais une dalle tronquée prise pour complète.

Usage : ``python -m lidar_arch.data.download [--out-dir DIR]``
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

from lidar_arch.constants import BYTES_PER_MB, IGN_BLOC, RAW_LIDAR_DIR
from lidar_arch.logging_config import configure_logging, get_logger

logger = get_logger("lidar_arch.data.download")

BASE_URL = (
    "https://storage.sbg.cloud.ovh.net/v1/"
    "AUTH_63234f509d6048bca3c9fd7928720ca1/ppk-lidar/{bloc}/{nom}"
)

PART_SUFFIX = ".part"

DALLES = [
    "LHD_FXX_0857_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0857_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0857_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0857_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0857_6267_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0858_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0858_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0858_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0858_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0858_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0858_6267_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0859_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0859_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0859_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0859_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0859_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0859_6267_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0860_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0860_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0860_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0860_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0860_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0860_6267_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0861_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0861_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0861_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0861_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0861_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0861_6267_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0862_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0862_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0862_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0862_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0862_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0862_6267_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0863_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0863_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0863_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0863_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0863_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0864_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0864_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0864_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0864_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0864_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0865_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0865_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0865_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0865_6265_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0865_6266_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0866_6262_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0866_6263_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0866_6264_PTS_C_LAMB93_IGN69.copc.laz",
    "LHD_FXX_0866_6265_PTS_C_LAMB93_IGN69.copc.laz",
]


def download_dalle(nom: str, output_dir: Path, bloc: str = IGN_BLOC) -> bool:
    """Télécharge une dalle si elle n'est pas déjà présente.

    Returns
    -------
    bool
        ``True`` si la dalle est présente à la fin (déjà là ou téléchargée).
    """
    chemin = output_dir / nom
    if chemin.exists() and chemin.stat().st_size > 0:
        logger.info("Déjà présente : %s", nom)
        return True

    partiel = chemin.with_name(chemin.name + PART_SUFFIX)
    try:
        urlretrieve(BASE_URL.format(bloc=bloc, nom=nom), partiel)
    except (HTTPError, URLError) as err:
        logger.error("Échec : %s (%s)", nom, err)
        partiel.unlink(missing_ok=True)
        return False

    partiel.replace(chemin)
    logger.info("Téléchargée : %s (%.1f Mo)", nom, chemin.stat().st_size / BYTES_PER_MB)
    return True


def download_all(output_dir: Path, noms: Sequence[str] = DALLES) -> int:
    """Télécharge toutes les dalles manquantes ; renvoie le nombre de dalles présentes."""
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("%d dalles (bloc %s) → %s", len(noms), IGN_BLOC, output_dir)
    presentes = sum(download_dalle(nom, output_dir) for nom in noms)
    logger.info("%d/%d dalles présentes", presentes, len(noms))
    return presentes


def main(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée CLI : code de sortie 1 si au moins une dalle a échoué."""
    parser = argparse.ArgumentParser(description="Téléchargement des dalles IGN LiDAR HD")
    parser.add_argument("--out-dir", type=Path, default=RAW_LIDAR_DIR)
    args = parser.parse_args(argv)

    configure_logging()
    if download_all(args.out_dir) < len(DALLES):
        sys.exit(1)


if __name__ == "__main__":
    main()
