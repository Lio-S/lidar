import logging

from lidar_arch.logging_config import configure_logging, get_logger


def test_get_logger_returns_logger() -> None:
    logger = get_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test"


def test_configure_logging_idempotent() -> None:
    configure_logging()
    handler_count = len(logging.getLogger().handlers)
    configure_logging()
    assert len(logging.getLogger().handlers) == handler_count
