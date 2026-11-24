#!/usr/bin/env bash
# Lancé à chaque démarrage du Dev Container (postStartCommand).
# 1. Démarre minikube s'il est arrêté (ex : après un redémarrage de Windows/WSL2)
# 2. Déploie (ou met à jour) MLflow + monitoring : kubectl apply est idempotent
# 3. Lance un container Docker par port-forward (MLflow / Grafana / Prometheus)
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
  minikube start --driver=docker || { echo "échec minikube start"; exit 1; }
fi

# Namespaces d'abord (kubectl traite les fichiers par ordre alphabétique)
kubectl apply -f k8s/mlflow/namespace.yaml -f k8s/monitoring/namespace.yaml
kubectl apply -f k8s/mlflow/ -f k8s/monitoring/

for fwd in "${FORWARDS[@]}"; do
  read -r ns svc port <<<"$fwd"
  name="lidar-pf-$svc"
  docker rm -f "$name" >/dev/null 2>&1 || true
  # --network host : écoute sur localhost de WSL2 → accessible depuis Windows
  # volumes : kubeconfig + certificats créés par minikube, montés aux mêmes chemins
  # que dans le Dev Container (le kubeconfig référence les certificats en chemin absolu)
  if docker run -d --name "$name" --restart unless-stopped --network host --user 0 \
      -v lidar-kube-ubuntu:/home/ubuntu/.kube:ro -v lidar-minikube-ubuntu:/home/ubuntu/.minikube:ro \
      "$KUBECTL_IMAGE" --kubeconfig /home/ubuntu/.kube/config \
      port-forward -n "$ns" "svc/$svc" "$port:$port" >/dev/null; then
    echo "port-forward $svc → http://localhost:$port"
  else
    echo "échec port-forward $svc"
  fi
done
