import sys
from pathlib import Path
from loguru import logger
from src.config.parser import PathsConfig

def setup_logger(paths_config: PathsConfig):
    logger.remove()

    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        enqueue=True,
    )

    log_file = paths_config.output_logs / "attendance_ai_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file),
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        enqueue=True,
    )

    logger.info("Logger initialized successfully.")
