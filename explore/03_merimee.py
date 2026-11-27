"""Monuments historiques (base Mérimée) des communes couvertes par les 54 dalles LiDAR.

Filtre l'export Mérimée sur les communes de l'emprise (codes INSEE de la couche
``commune`` de la BD TOPO), projette les points en Lambert 93, indique la dalle qui
les contient et l'objet BD TOPO ancien le plus proche. Sert à la couche de protection
et à la table ``sites`` (voir DECISIONS.md, 2026-11 — Masque bâti : sources externes
datées et couche de protection).

Les coordonnées Mérimée sont des points représentatifs, pas des emprises : un monument
étendu (oppidum, enceinte) n'est localisé que par un point.

Prérequis : export Mérimée dans ``data/external/merimee/`` et BD TOPO extraite dans
``data/external/bdtopo/`` (voir DATA.md).

Usage ::

    uv run python explore/03_merimee.py > explore/reports/merimee.txt

Écrit aussi les points en Lambert 93 dans ``data/external/merimee/merimee_emprise_l93.gpkg``
(superposition QGIS).
"""

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from lidar_arch.constants import (
    BDTOPO_DIR,
    CRS_EPSG,
    MERIMEE_CSV,
    MERIMEE_DIR,
    RAW_LIDAR_DIR,
    TILE_GLOB,
)
from lidar_arch.data.dtm import tile_bounds_from_name, tile_id

SEP = "|"
INSEE_SEP = ";"  # monuments à cheval sur plusieurs communes
WGS84_EPSG = 4326
OUT_GPKG = MERIMEE_DIR / "merimee_emprise_l93.gpkg"
COLS = {
    "Reference": "reference",
    "Titre_editorial_de_la_notice": "titre",
    "Commune_forme_editoriale": "commune",
    "Denomination_de_l_edifice": "denomination",
    "Format_abrege_du_siecle_de_construction": "siecle",
    "Date_et_typologie_de_la_protection": "protection",
    "COG_Insee_lors_de_la_protection": "code_insee",
    "coordonnees_au_format_WGS84": "coord_wgs84",
}
# Objets BD TOPO comparés aux points Mérimée (voir l'inventaire, explore/02_bdtopo_inventaire.py)
BDTOPO_ANCIENS = {
    "batiment": ["Chapelle", "Eglise", "Tour, donjon", "Fort, blockhaus, casemate"],
    "construction_lineaire": ["Ruines", "Mur", "Mur de soutènement"],
}
REPORT_COLS = ["reference", "titre", "commune", "protection", "siecle", "dalle"]

gpkg = next(iter(sorted(BDTOPO_DIR.rglob("*.gpkg"))), None)
if gpkg is None:
    raise FileNotFoundError(f"Aucun .gpkg dans {BDTOPO_DIR} (télécharger et extraire la BD TOPO)")
tiles = {tile_id(p): tile_bounds_from_name(p) for p in RAW_LIDAR_DIR.glob(TILE_GLOB)}
if not tiles:
    raise FileNotFoundError(f"Aucune dalle {TILE_GLOB} dans {RAW_LIDAR_DIR} (dvc pull ?)")
dalles = gpd.GeoDataFrame(
    {"dalle": list(tiles)},
    geometry=[box(b.xmin, b.ymin, b.xmax, b.ymax) for b in tiles.values()],
    crs=CRS_EPSG,
)
bbox = tuple(dalles.total_bounds)

communes = gpd.read_file(gpkg, layer="commune", bbox=bbox)
codes = set(communes["code_insee"])
print(f"Mérimée : {MERIMEE_CSV.name}\nBD TOPO : {gpkg.name}")
print(f"Communes de l'emprise : {', '.join(sorted(communes['nom_officiel']))}")

merimee = pd.read_csv(MERIMEE_CSV, sep=SEP, dtype=str, usecols=list(COLS)).rename(columns=COLS)
par_code = merimee.assign(code=merimee["code_insee"].str.split(INSEE_SEP)).explode("code")
merimee = merimee[merimee.index.isin(par_code.index[par_code["code"].isin(codes)])]
print(f"\n{len(merimee)} notice(s) Mérimée dans ces communes")

sans_coord = merimee[merimee["coord_wgs84"].isna()]
if not sans_coord.empty:
    print(f"\n=== {len(sans_coord)} notice(s) sans coordonnées (à localiser à la main)")
    print(sans_coord[REPORT_COLS[:-1]].to_string(index=False, max_colwidth=50))

avec_coord = merimee.dropna(subset=["coord_wgs84"])
lat_lon = avec_coord["coord_wgs84"].str.split(",", expand=True).astype(float)
points = gpd.GeoDataFrame(
    avec_coord.drop(columns="coord_wgs84"),
    geometry=gpd.points_from_xy(lat_lon[1], lat_lon[0]),
    crs=WGS84_EPSG,
).to_crs(CRS_EPSG)
points = points.sjoin(dalles, how="left", predicate="within").drop(columns="index_right")

anciens = pd.concat(
    [
        gpd.read_file(gpkg, layer=layer, bbox=bbox, columns=["nature"])
        .loc[lambda g: g["nature"].isin(natures)]
        .assign(couche=layer)
        for layer, natures in BDTOPO_ANCIENS.items()
    ],
    ignore_index=True,
).rename(columns={"nature": "objet_bdtopo"})
points = (
    gpd.sjoin_nearest(points, anciens, how="left", distance_col="dist_bdtopo_m")
    .drop(columns="index_right")
    .drop_duplicates("reference")  # ex aequo : un seul objet BD TOPO par notice
)

dans = points["dalle"].notna()
pd.set_option("display.width", 250)
print(f"\n=== {dans.sum()} monument(s) dans l'emprise des dalles")
print(
    points.loc[dans, [*REPORT_COLS, "objet_bdtopo", "couche", "dist_bdtopo_m"]]
    .sort_values(["dalle", "reference"])
    .to_string(index=False, max_colwidth=45, float_format="{:.0f}".format)
)
print(f"\n=== {(~dans).sum()} monument(s) hors emprise")
print(points.loc[~dans, REPORT_COLS[:-1]].sort_values("reference").to_string(index=False, max_colwidth=45))

points.to_file(OUT_GPKG, layer="merimee", driver="GPKG")
print(f"\nPoints Lambert 93 : {OUT_GPKG}")
