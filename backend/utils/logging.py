from __future__ import annotations

import logging
import sys


def configure_logging(debug: bool = False) -> None:
    """Configure structured-ish logging for the application.

    Args:
        debug: Enable DEBUG-level output when ``True``.
    """
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on re-config.
    if not root.handlers:
        root.addHandler(handler)