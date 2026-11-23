"""Tests de la configuration des logs (JSON console + fichier rotatif optionnel)."""

# Annotations non évaluées à l'exécution : logging._SysExcInfoType n'existe que dans typeshed
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from lidar_arch import logging_config
from lidar_arch.logging_config import _JsonFormatter, configure_logging, get_logger


@pytest.fixture
def root_vide() -> Iterator[Callable[[], logging.Logger]]:
    """Fournit `vider()` : retire les handlers du logger racine ; état restauré après le test.

    pytest attache ses handlers de capture au logger racine au début de l'exécution
    du test (après les fixtures) : `vider()` doit donc être appelé dans le test, sinon
    configure_logging() sortirait immédiatement (`if root.handlers: return`).
    """
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level

    def vider() -> logging.Logger:
        root.handlers.clear()
        return root

    yield vider
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers[:] = handlers
    root.setLevel(level)


def _record(msg: str, exc_info: logging._SysExcInfoType | None = None) -> logging.LogRecord:
    return logging.LogRecord("test", logging.WARNING, __file__, 1, msg, None, exc_info)


def test_get_logger_returns_logger() -> None:
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test"


def test_json_formatter_champs() -> None:
    payload = json.loads(_JsonFormatter().format(_record("dalle traitée é")))
    assert payload["level"] == "WARNING"
    assert payload["logger"] == "test"
    assert payload["message"] == "dalle traitée é"
    assert payload["timestamp"].endswith("+00:00")  # UTC
    assert "exception" not in payload


def test_json_formatter_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
    payload = json.loads(_JsonFormatter().format(_record("erreur", exc_info)))
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_console_seule(
    root_vide: Callable[[], logging.Logger], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = root_vide()
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    configure_logging()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0], logging.StreamHandler)
    assert isinstance(root.handlers[0].formatter, _JsonFormatter)


def test_configure_logging_avec_fichier(
    root_vide: Callable[[], logging.Logger], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = root_vide()
    log_file = tmp_path / "logs" / "lidar_arch.log"
    monkeypatch.setattr(logging_config, "LOG_FILE", str(log_file))
    configure_logging()

    file_handlers = [
        h for h in root.handlers if isinstance(h, logging.handlers.TimedRotatingFileHandler)
    ]
    assert len(file_handlers) == 1
    get_logger("test").warning("écrit dans le fichier")
    file_handlers[0].flush()
    line = log_file.read_text(encoding="utf-8").strip()
    assert json.loads(line)["message"] == "écrit dans le fichier"


def test_configure_logging_idempotent(
    root_vide: Callable[[], logging.Logger], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = root_vide()
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    configure_logging()
    configure_logging()
    assert len(root.handlers) == 1


def test_configure_logging_niveau(
    root_vide: Callable[[], logging.Logger], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = root_vide()
    monkeypatch.setattr(logging_config, "LOG_LEVEL", "DEBUG")
    monkeypatch.setattr(logging_config, "LOG_FILE", None)
    configure_logging()
    assert root.level == logging.DEBUG
