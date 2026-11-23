# ── Stage base : libs système communes dev + prod ──────────────────────────────
# Ubuntu 24.04 LTS (noble) — cohérent avec le WSL2 de dev
# noble fournit : Python 3.12, GDAL 3.4+, PROJ 9.4+
FROM ubuntu:24.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    UV_LINK_MODE=copy

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
        git \
    && rm -f /usr/lib/python3.12/EXTERNALLY-MANAGED \
    && rm -rf /var/lib/apt/lists/*

# uv 0.11.18 — gestionnaire de dépendances Python
COPY --from=ghcr.io/astral-sh/uv:0.11.18 /uv /usr/local/bin/uv

WORKDIR /app

# ── Stage dev : outils qualité code + toutes les dépendances ───────────────────
FROM base AS dev

COPY pyproject.toml uv.lock ./
# Dépendances seules : le code (src/) n'est pas dans l'image, il est monté par le Dev Container.
# Le projet lui-même est installé en éditable au postCreate (voir .devcontainer/devcontainer.json).
RUN uv sync --frozen --extra dev --no-install-project

# Venv unique /app/.venv, même quand uv tourne depuis /workspaces/lidar
# (évite d'utiliser le .venv WSL2 visible via le montage du workspace)
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Outils infra (dev uniquement) : Terraform, kubectl, minikube, Docker CLI, GitHub CLI
# minikube utilise le Docker Engine de WSL2 via le socket monté (voir .devcontainer/)
ARG TERRAFORM_VERSION=1.17.2
ARG KUBECTL_VERSION=1.37.2
ARG MINIKUBE_VERSION=1.39.0
ARG GH_VERSION=2.105.0

COPY --from=docker:29.5.2-cli /usr/local/bin/docker /usr/local/bin/docker

RUN apt-get update && apt-get install -y --no-install-recommends unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSLo /tmp/tf.zip "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && unzip /tmp/tf.zip terraform -d /usr/local/bin && rm /tmp/tf.zip \
    && curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && curl -fsSLo /usr/local/bin/minikube "https://github.com/kubernetes/minikube/releases/download/v${MINIKUBE_VERSION}/minikube-linux-amd64" \
    && chmod +x /usr/local/bin/kubectl /usr/local/bin/minikube \
    && curl -fsSLo /tmp/gh.tar.gz "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" \
    && tar -xzf /tmp/gh.tar.gz -C /usr/local/bin --strip-components=2 "gh_${GH_VERSION}_linux_amd64/bin/gh" \
    && rm /tmp/gh.tar.gz

# Le code source est monté en volume par le Dev Container (pas copié)
# → les modifications locales sont immédiatement visibles dans le container

# Stage prod : ajouté en Phase 6 — voir meta/ROADMAP.md
