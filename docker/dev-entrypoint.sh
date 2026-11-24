#!/bin/sh
# Entrypoint du stage dev — exécuté en root au démarrage du container, avant VS Code.
#
# Donne à l'utilisateur non-root du container (ubuntu, uid 1000) l'accès au socket
# Docker monté depuis l'hôte. Le GID du socket varie selon la machine (ex : 989 sur
# un WSL2, 0 avec Docker Desktop) : on le lit au démarrage au lieu de le figer dans l'image.
# `docker exec -u ubuntu` (utilisé par VS Code) relit /etc/group → le groupe est actif
# pour toutes les sessions ouvertes ensuite.
set -e

DEV_USER=ubuntu
SOCK=/var/run/docker.sock

if [ -S "$SOCK" ]; then
  gid=$(stat -c %g "$SOCK")
  group=$(getent group "$gid" | cut -d: -f1)
  if [ -z "$group" ]; then
    group=docker-host
    groupadd -g "$gid" "$group"
  fi
  usermod -aG "$group" "$DEV_USER"
fi

exec "$@"
