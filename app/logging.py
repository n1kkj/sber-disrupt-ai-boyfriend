import logging as std_logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import List

from settings import config


class ApplicationLogging:
    _handler_marker = '_ai_companion_handler'

    @classmethod
    def configure(cls: type['ApplicationLogging']) -> None:
        root_logger = std_logging.getLogger()
        root_logger.setLevel(config.logging.level.upper())
        formatter = std_logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        )
        handlers: List[std_logging.Handler] = [
            std_logging.StreamHandler(),
            cls._file_handler(),
        ]
        for handler in list(root_logger.handlers):
            if getattr(handler, cls._handler_marker, False):
                root_logger.removeHandler(handler)
                handler.close()
        for handler in handlers:
            setattr(handler, cls._handler_marker, True)
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)

        logger = std_logging.getLogger('ai_companion')
        logger.setLevel(config.logging.level.upper())
        logger.propagate = True

    @classmethod
    def _file_handler(cls: type['ApplicationLogging']) -> RotatingFileHandler:
        path = Path(config.logging.file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return RotatingFileHandler(
            path,
            maxBytes=config.logging.max_bytes,
            backupCount=config.logging.backup_count,
            encoding='utf-8',
        )


ApplicationLogging.configure()
logger = std_logging.getLogger('ai_companion')
