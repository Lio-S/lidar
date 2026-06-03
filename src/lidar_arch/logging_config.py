import json
import logging
import logging.handlers
import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
# LOG_FILE : chemin du fichier log (ex: "logs/lidar_arch.log")
# Si absent → logs console uniquement (comportement Docker/K8s)
LOG_FILE: str | None = os.getenv("LOG_FILE")


class _JsonFormatter(logging.Formatter):
    """Formatte les logs en JSON structuré — compatible Grafana Loki."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configure le logger racine.

    - Console (stdout, JSON) : toujours actif → capturé par Docker/K8s
    - Fichier rotatif (minuit, 30 jours) : activé si LOG_FILE est défini
    """
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    if root.handlers:
        return

    formatter = _JsonFormatter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if LOG_FILE:
        log_path = Path(LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_path,
            when="midnight",
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé. Appeler configure_logging() une fois au démarrage."""
    return logging.getLogger(name)
