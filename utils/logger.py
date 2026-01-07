# utils/logger.py
import sys
import logging

# Set this to False in Production
DEBUG_MODE = True


class Logger:
    @staticmethod
    def setup():
        logger = logging.getLogger("CaddyProc")
        logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.WARNING)

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger


log = Logger.setup()


def log_event(msg):
    if DEBUG_MODE:
        log.info(msg)


def log_error(msg, exc_info=None):
    # In prod, this will eventually route to the Telegram Bot
    log.error(msg, exc_info=exc_info)
