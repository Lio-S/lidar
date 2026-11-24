# LiDAR Archéologie PACA

Détection automatique de structures archéologiques sur données IGN LiDAR HD
par apprentissage automatique — zone d'étude : Bouches-du-Rhône (PACA, France).

## Objectif

Développer un pipeline ML capable de détecter des anomalies de relief
caractéristiques de structures archéologiques (fossés, remparts, tumuli, villae)
à partir des nuages de points LiDAR haute densité de l'IGN.

## Zone d'étude

- **Site v1** : Saint-Blaise (Saint-Mitre-les-Remparts, 13) — remparts massifs, ground truth solide
- **Données** : IGN LiDAR HD, résolution 10 pts/m², open data

## Pipeline

```
Dalles .laz IGN → Filtrage végétation → MNT → Indicateurs morphologiques → ML → Détection
```

## Stack

Python 3.12 · uv · laspy · rasterio · scikit-learn · XGBoost · PyTorch · MLflow · DVC · Prefect · BentoML

→ Architecture complète (diagrammes, K8s, Terraform, flux données) : [`meta/ARCHITECTURE.md`](meta/ARCHITECTURE.md)

## Données

Les données LiDAR sont téléchargeables gratuitement sur :
https://geoservices.ign.fr/lidarhd

Non incluses dans ce dépôt (trop volumineuses) — voir `DATA.md` pour les instructions.

## Démarrage rapide

```bash
git clone https://github.com/Lio-S/lidar
cd lidar
```

Ouvrir dans VS Code → **Reopen in Container** (Dev Container requis).
Le container tourne en utilisateur non-root `ubuntu` (uid 1000) : les fichiers créés dedans
appartiennent à l'utilisateur de l'hôte. Au démarrage, minikube, MLflow (http://localhost:5000),
Grafana (http://localhost:3000) et Prometheus (http://localhost:9090) sont lancés automatiquement.

> Dev Container créé avant le passage en non-root : suivre la **migration** décrite dans
> [`meta/DECISIONS.md`](meta/DECISIONS.md) (« Dev Container non-root »).

**Récupérer les données LiDAR (5.23 Go, dossier Drive public en lecture) :**
```bash
dvc pull          # dans le terminal du container
```

**Lancer le pipeline :**
```bash
dvc repro         # génère les MNT et features depuis les données brutes
uv run pytest     # vérifie l'installation
```

> Contributeur (push de données) : demander l'accès Éditeur au dossier Drive,
> puis configurer ses propres credentials OAuth — voir [`meta/DATA.md`](meta/DATA.md).

## Contribuer

La branche `main` est protégée : toute modification passe par une Pull Request,
fusionnable uniquement si la CI (`ruff → mypy → pytest → build`) est verte.

```bash
git switch main && git pull                  # 1. partir de la dernière version
git switch -c <type>/<sujet>                 # 2. créer une branche (ex. docs/roadmap, ci/declencheurs)
# … modifier les fichiers …
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
                                             # 3. vérifier en local (mêmes étapes que la CI)
git add <fichiers>                           # 4. sélectionner les fichiers modifiés
git commit -m "Description courte"           # 5. commiter
git push -u origin <type>/<sujet>            # 6. envoyer la branche
gh pr create --fill                          # 7. ouvrir la Pull Request
gh pr merge --squash --delete-branch         # 8. fusionner une fois la CI verte
```

Les données ne passent pas par Git : après modification de `data/`, utiliser `dvc add` puis
`dvc push`, et commiter le fichier `.dvc` mis à jour.

## Structure

```
├── data/           # Données (non versionnées, gérées par DVC → Google Drive)
├── meta/           # Documentation (ARCHITECTURE.md, ROADMAP.md, DECISIONS.md)
├── notebooks/      # Exploration et prototypage
├── src/            # Code source
├── k8s/            # Manifests Kubernetes (MLflow, Prometheus, Grafana)
├── terraform/      # Infrastructure as Code (GitHub ; GCS optionnel dans gcs/)
├── configs/        # Hyperparamètres
└── reports/        # Résultats et figures (commitées dans Git)
```

## Références

- [IGN LiDAR HD](https://geoservices.ign.fr/lidarhd)
- [open-archaeo.info](https://open-archaeo.info)
- [Computer Applications in Archaeology (CAA)](https://caa-international.org)

## Licence

MIT