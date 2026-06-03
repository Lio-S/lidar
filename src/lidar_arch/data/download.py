"""Téléchargement des dalles LiDAR HD IGN — zone Saint-Blaise / Istres / Miouvin.

Source : OVH Cloud Storage (hébergement officiel des dalles IGN LiDAR HD).
"""

from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import HTTPError, URLError

# Bloc IGN couvrant la zone Bouches-du-Rhône (à confirmer pour toutes les dalles)
BLOC = "OQ"

BASE_URL = (
    "https://storage.sbg.cloud.ovh.net/v1/"
    "AUTH_63234f509d6048bca3c9fd7928720ca1/ppk-lidar/{bloc}/{nom}"
)

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

OUTPUT_DIR = Path("./data/raw/lidar")


def download_dalle(nom: str, bloc: str, output_dir: Path) -> bool:
    """Télécharge une dalle si elle n'existe pas déjà."""
    chemin = output_dir / nom
    if chemin.exists() and chemin.stat().st_size > 0:
        print(f"  → Déjà présent : {nom}")
        return True

    url = BASE_URL.format(bloc=bloc, nom=nom)
    try:
        urlretrieve(url, chemin)
        taille_mo = chemin.stat().st_size / (1024 * 1024)
        print(f"  ✓ {nom} ({taille_mo:.1f} Mo)")
        return True
    except (HTTPError, URLError) as e:
        print(f"  ✗ Échec : {nom} ({e})")
        if chemin.exists():
            chemin.unlink()
        return False


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement de {len(DALLES)} dalles (bloc {BLOC}) vers {OUTPUT_DIR}\n")

    succes = sum(download_dalle(d, BLOC, OUTPUT_DIR) for d in DALLES)

    print(f"\n{succes}/{len(DALLES)} dalles téléchargées avec succès.")


if __name__ == "__main__":
    main()
