import logging
import sys


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure the patchwork logger. Idempotent — safe to call multiple times."""
    logger = logging.getLogger("patchwork")

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger
