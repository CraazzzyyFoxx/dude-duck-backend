"""Custom Logger Using Loguru, inspired by Riki-1mg gist custom_logging.py"""

import logging
import sys
from pathlib import Path

from loguru import logger as loguru_logger

from app.core import config


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists.
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class OverFastAPILogger:
    @classmethod
    def make_logger(cls):
        return cls.customize_logging(
            Path(f"{config.app.logs_root_path}/access.log"),
            level=config.app.log_level,
            rotation="1 day",
            retention="1 year",
            compression="gz",
            log_format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan> - <level>{message}</level>"
            ),
        )

    @classmethod
    def customize_logging(
        cls,
        filepath: Path,
        level: str,
        rotation: str,
        retention: str,
        compression: str,
        log_format: str,
    ):
        loguru_logger.remove()
        loguru_logger.add(
            sys.stdout,
            backtrace=True,
            level=level.upper(),
            format=log_format,
        )
        loguru_logger.add(
            str(filepath),
            rotation=rotation,
            retention=retention,
            compression=compression,
            enqueue=True,
            backtrace=True,
            level=level.upper(),
            format=log_format,
        )
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        # logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
        # for _log in ("uvicorn", "uvicorn.error", "fastapi"):
        #     _logger = logging.getLogger(_log)
        #     _logger.handlers = [InterceptHandler()]

        return loguru_logger


# Instanciate generic logger for all the app
logger = OverFastAPILogger.make_logger()
