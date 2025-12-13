import sys
import logging
import colorlog
from logging.handlers import RotatingFileHandler
from utils.system_utils import isBundle


class InitLogging:
    def __init__(
        self,
        log_file="app.log",
        max_size_mb=5,
        max_backups=5
    ):
        """
        Initialize logging with:
        - Console logging (colored)
        - File logging (rotating)
        - Different behavior when packaged (PyInstaller bundle)
        """

        logger = logging.getLogger()

        # PyInstaller bundle → file-only, no console
        if isBundle():
            LOGGING_MODE = "file"
            logger.setLevel(logging.INFO)

        else:
            LOGGING_MODE = "both"
            logger.setLevel(logging.DEBUG)

        # Clear old handlers (avoid duplicate logging)
        if logger.hasHandlers():
            logger.handlers.clear()

        # -------- FORMATTERS -------- #
        basic_fmt = logging.Formatter(
            "[%(asctime)s][%(levelname)s] -> %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        colored_fmt = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d] -> %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
        )

        handlers = []

        # -------- FILE HANDLER (with auto-rotation) -------- #
        if LOGGING_MODE in ("file", "both"):
            try:
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_size_mb * 1024 * 1024,
                    backupCount=max_backups,
                    encoding="utf-8"
                )
                file_handler.setFormatter(basic_fmt)
                logger.addHandler(file_handler)
                handlers.append("rotating log file")
            except Exception as e:
                print(f"[Logging Error] File handler failed: {e}")

        # -------- CONSOLE HANDLER -------- #
        if LOGGING_MODE in ("console", "both"):
            try:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(colored_fmt)
                logger.addHandler(console_handler)
                handlers.append("console output")
            except Exception as e:
                print(f"[Logging Error] Console handler failed: {e}")

        # Final result
        if handlers:
            logger.info(f"Logging initialized with: {', '.join(handlers)}")
        else:
            logger.error("Logging setup failed — no handlers added!")
