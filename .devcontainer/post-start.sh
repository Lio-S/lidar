#!/usr/bin/env bash
# Lancé à chaque démarrage du Dev Container (postStartCommand).
# 1. Démarre minikube s'il est arrêté (ex : après un redémarrage de Windows/WSL2)
# 2. Lance un container Docker par port-forward (MLflow / Grafana / Prometheus)
#
# Pourquoi des containers et pas des processus en arrière-plan : VS Code tue tous les
# processus lancés par postStartCommand à la fin de la commande (même avec setsid/nohup).
# Des containers gérés par Docker (--restart unless-stopped) survivent, et redémarrent
# seuls si un pod redémarre ou au reboot de WSL2.
#
# Logs : /tmp/post-start.log ; docker logs lidar-pf-<service>
set -u

LOG=/tmp/post-start.log
exec >>"$LOG" 2>&1
echo "=== $(date -Is) post-start"

KUBECTL_IMAGE=registry.k8s.io/kubectl:v1.37.2

# Service K8s → "namespace service port"
FORWARDS=(
  "mlflow mlflow 5000"
  "monitoring grafana 3000"
  "monitoring prometheus 9090"
)

if ! minikube status >/dev/null 2>&1; then
  echo "minikube arrêté → démarrage"
  # --force : le container tourne en root (refusé par défaut avec le driver docker)
  minikube start --driver=docker --force || { echo "échec minikube start"; exit 1; }
fi

for fwd in "${FORWARDS[@]}"; do
  read -r ns svc port <<<"$fwd"
  name="lidar-pf-$svc"
  docker rm -f "$name" >/dev/null 2>&1 || true
  # --network host : écoute sur localhost de WSL2 → accessible depuis Windows
  # volumes lidar-kube / lidar-minikube : kubeconfig + certificats créés par minikube
  if docker run -d --name "$name" --restart unless-stopped --network host --user 0 \
      -v lidar-kube:/root/.kube:ro -v lidar-minikube:/root/.minikube:ro \
      "$KUBECTL_IMAGE" --kubeconfig /root/.kube/config \
      port-forward -n "$ns" "svc/$svc" "$port:$port" >/dev/null; then
    echo "port-forward $svc → http://localhost:$port"
  else
    echo "échec port-forward $svc"
  fi
done
