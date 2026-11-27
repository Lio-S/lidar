"""Inventaire de la BD TOPO sur l'emprise des 54 dalles LiDAR.

Pour chaque couche de la BD TOPO : nombre d'objets par nature, puis liste des objets
dont la nature ou le toponyme évoque un monument ou un vestige ancien. Sert à choisir
les natures du masque d'exclusion bâti et de la couche de protection (voir DECISIONS.md,
2026-11 — Masque bâti : sources externes datées et couche de protection).

Prérequis : ``uv add geopandas`` ; GeoPackage extrait dans ``data/external/bdtopo/``.

Usage ::

    uv run python explore/02_bdtopo_inventaire.py | tee explore/reports/bdtopo_inventaire.txt
"""

import geopandas as gpd
import pyogrio

from lidar_arch.constants import BDTOPO_DIR, RAW_LIDAR_DIR, TILE_GLOB
from lidar_arch.data.dtm import tile_bounds_from_name

NATURE_COLS = ("nature", "nature_detaillee", "categorie")
TEXT_COLS = (*NATURE_COLS, "toponyme")
ANCIEN = (
    r"(?i)ruine|rempart|fortif|vestige|ch[aâ]teau|chapelle|[ée]glise|monument|oppidum"
    r"|tour\b|donjon|fort\b|blockhaus|ar[eè]ne|th[ée][aâ]tre antique|guet|clocher|aqueduc|carri[eè]re"
)

gpkg_files = sorted(BDTOPO_DIR.rglob("*.gpkg"))
if not gpkg_files:
    raise FileNotFoundError(f"Aucun .gpkg dans {BDTOPO_DIR} (télécharger et extraire la BD TOPO)")
gpkg = gpkg_files[0]

bounds = [tile_bounds_from_name(p) for p in RAW_LIDAR_DIR.glob(TILE_GLOB)]
if not bounds:
    raise FileNotFoundError(f"Aucune dalle {TILE_GLOB} dans {RAW_LIDAR_DIR} (dvc pull ?)")
bbox = (
    min(b.xmin for b in bounds),
    min(b.ymin for b in bounds),
    max(b.xmax for b in bounds),
    max(b.ymax for b in bounds),
)
print(f"BD TOPO : {gpkg.name}\nEmprise Lambert 93 : {bbox}")

for layer, geometry_type in pyogrio.list_layers(gpkg):
    if geometry_type is None:  # table attributaire sans géométrie : pas de filtre spatial
        continue
    gdf = gpd.read_file(gpkg, layer=layer, bbox=bbox)
    if gdf.empty:
        continue
    print(f"\n=== {layer} : {len(gdf)} objets")
    if layer == "commune":  # communes couvertes : liste à croiser avec les Monuments historiques
        name_col = next((c for c in ("nom_officiel", "nom") if c in gdf.columns), None)
        if name_col:
            print(", ".join(sorted(gdf[name_col].astype(str))))
    nature_cols = [c for c in NATURE_COLS if c in gdf.columns]
    if nature_cols:
        print(gdf[nature_cols].value_counts(dropna=False).to_string())

    text_cols = [c for c in TEXT_COLS if c in gdf.columns]
    if not text_cols:
        continue
    texts = gdf[text_cols].fillna("").astype(str)
    text = texts.iloc[:, 0].str.cat(texts.iloc[:, 1:], sep=" ")
    anciens = gdf[text.str.contains(ANCIEN)]
    if not anciens.empty:
        print(f"--- {len(anciens)} objet(s) potentiellement ancien(s)")
        print(anciens.drop(columns="geometry").to_string(max_colwidth=40))
