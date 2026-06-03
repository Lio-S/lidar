# LiDAR Archéologie PACA

Détection automatique de structures archéologiques sur données IGN LiDAR HD
par apprentissage automatique — zone d'étude : Bouches-du-Rhône (PACA, France).

## Objectif

Développer un pipeline ML capable de détecter des anomalies de relief
caractéristiques de structures archéologiques (fossés, remparts, tumuli, villae)
à partir des nuages de points LiDAR haute densité de l'IGN.

## Zone d'étude

- **Site principal** : Saint-Blaise (Saint-Mitre-les-Remparts, 13)
- **Site secondaire** : Miouvin (Istres, 13)
- **Données** : IGN LiDAR HD, résolution 10 pts/m², open data

## Pipeline

```
Dalles .laz IGN → Filtrage végétation → MNT → Indicateurs morphologiques → ML → Détection
```

## Stack

Python 3.11 · laspy · pdal · rasterio · scikit-learn · PyTorch · WSL2/Ubuntu

## Données

Les données LiDAR sont téléchargeables gratuitement sur :
https://geoservices.ign.fr/lidarhd

Non incluses dans ce dépôt (trop volumineuses) — voir `DATA.md` pour les instructions.

## Installation

```bash
git clone https://github.com/Lio-S/lidar-archeologie
cd lidar-archeologie
uv sync                # installe Python 3.12 + toutes les dépendances
```

## Structure

```
├── data/           # Données (non versionnées, gérées par DVC)
├── meta/           # Documentation
├── notebooks/      # Exploration et prototypage
├── src/            # Code source
├── configs/        # Hyperparamètres
└── reports/        # Résultats et figures
```

## Références

- [IGN LiDAR HD](https://geoservices.ign.fr/lidarhd)
- [open-archaeo.info](https://open-archaeo.info)
- [Computer Applications in Archaeology (CAA)](https://caa-international.org)

## Licence

MIT
