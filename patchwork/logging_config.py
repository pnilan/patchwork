import logging
import sys


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure the patchwork logger. Idempotent — safe to call multiple times.

    Always updates the handler level to match the current ``verbose`` setting,
    but never adds duplicate handlers.
    """
    logger = logging.getLogger("patchwork")
    level = logging.DEBUG if verbose else logging.INFO

    if logger.handlers:
        logger.handlers[0].setLevel(level)
        return logger

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    return logger
