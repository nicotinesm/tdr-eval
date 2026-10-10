"""Logging configuration for the DR Price Evaluator.

Logs rotate daily, keeping the last 7 files, written to the same
directory as the executable/config file.
"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

LOG_NAME = "dr_evaluator.log"


def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    log_dir = _base_dir()
    log_path = os.path.join(log_dir, LOG_NAME)

    logger = logging.getLogger("dr_evaluator")
    if logger.handlers:
        return logger

    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = TimedRotatingFileHandler(
        log_path, when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    console.setLevel(logging.WARNING)

    logger.addHandler(file_handler)
    logger.addHandler(console)
    return logger


def get_logger(name: str = "dr_evaluator") -> logging.Logger:
    """Return a logger that propagates to the configured file handler.

    All module loggers are made children of the ``dr_evaluator`` logger so
    their records flow into the rotating file handler installed by
    :func:`setup_logging`.
    """
    if name == "dr_evaluator" or name.startswith("dr_evaluator."):
        return logging.getLogger(name)
    return logging.getLogger(f"dr_evaluator.{name}")


def safe(value, max_len: int = 80) -> str:
    """Neutralize log forging: strip CR/LF and cap length of user-influenced values."""
    return str(value).replace("\r", " ").replace("\n", " ")[:max_len]
