import logging

from patchwork.logging_config import setup_logging


class TestSetupLogging:
    def setup_method(self):
        """Remove any existing patchwork logger handlers before each test."""
        logger = logging.getLogger("patchwork")
        logger.handlers.clear()

    def test_returns_logger(self):
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "patchwork"

    def test_adds_stderr_handler(self):
        logger = setup_logging()
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_default_handler_level_is_info(self):
        logger = setup_logging(verbose=False)
        assert logger.handlers[0].level == logging.INFO

    def test_verbose_handler_level_is_debug(self):
        logger = setup_logging(verbose=True)
        assert logger.handlers[0].level == logging.DEBUG

    def test_idempotent_no_duplicate_handlers(self):
        logger = setup_logging()
        setup_logging()
        assert len(logger.handlers) == 1

    def test_logger_level_is_debug(self):
        logger = setup_logging()
        assert logger.level == logging.DEBUG
