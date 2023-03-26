"""Log handlers"""

import logging

from constants.app import APP_NAME

class ColorFormatter(logging.Formatter):
    """Colorize messages according to its severity"""
    grey = '\x1b[38;21m'
    blue = '\x1b[38;5;39m'
    yellow = '\x1b[38;5;226m'
    red = '\x1b[38;5;196m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'

    def __init__(self, format_string):
        super().__init__()
        self.fmt = format_string
        self.formats = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

_FMT_STRING = '%(asctime)s [%(levelname)-8s] %(name)-30s: %(message)s'
stderr_handler = logging.StreamHandler()
stderr_handler.setFormatter(ColorFormatter(_FMT_STRING))

file_handler = logging.FileHandler(f'{APP_NAME}.log')
file_handler.setFormatter(ColorFormatter(_FMT_STRING))
