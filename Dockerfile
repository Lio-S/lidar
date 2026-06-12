# ── Stage base : libs système communes dev + prod ──────────────────────────────
# Ubuntu 24.04 LTS (noble) — cohérent avec le WSL2 de dev
# noble fournit : Python 3.12, GDAL 3.4+, PROJ 9.4+
FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    UV_SYSTEM_PYTHON=1

RUN sed -i 's/Components: main restricted/Components: main restricted universe/' /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.12 \
        python3.12-dev \
        python3.12-venv \
        gdal-bin \
        libgdal-dev \
        libproj-dev \
        libspatialindex-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# uv 0.11.18 — gestionnaire de dépendances Python
COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /usr/local/bin/uv

WORKDIR /app

# ── Stage dev : outils qualité code + toutes les dépendances ───────────────────
FROM base AS dev

COPY pyproject.toml ./
RUN uv pip install --system -e ".[dev]"

# Le code source est monté en volume par le Dev Container (pas copié)
# → les modifications locales sont immédiatement visibles dans le container

# Stage prod : ajouté en Phase 6 — voir meta/ROADMAP.md
