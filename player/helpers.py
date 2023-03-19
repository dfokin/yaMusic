"""
Different useful helpers
"""
from asyncio import sleep
from functools import wraps
import logging
import os

from player.constants import TRACK_LIKE, APP_NAME

def touch(path, mode=0o666, exist_ok=True):
    """Unix-like touch"""
    if exist_ok:
        try:
            os.utime(path, None)
        except OSError:
            pass
        else:
            return
    flags = os.O_CREAT | os.O_WRONLY
    if not exist_ok:
        flags |= os.O_EXCL
    with os.open(path, flags, mode):
        pass


def aiohttp_retry(
    to_catch: Exception, to_raise: Exception,
    timeout: float=2.0, num_tries:int=3, retry_delay=0.3,
    logger=None):
    """
    Retries aiohttp request after to_catch exceptions with total num_tries tries
    Adds timeout to request
    Rises to_raise when no retries left
    """
    def retry_decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _tries = num_tries + 1
            while _tries > 1:
                try:
                    return await func(*args, timeout=timeout, **kwargs)
                except to_catch as exc:
                    _tries -= 1
                    if _tries == 1:
                        if logger:
                            logger.warning(f'{func.__name__} failed after {num_tries} tries.')
                        raise to_raise(exc)             # pylint: disable=raise-missing-from
                    if logger:
                        logger.warning(f'{func.__name__} raised: {exc}')
                    await sleep(retry_delay)

        return wrapper
    return retry_decorator

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

class YaTrack:
    """Internal representation of the track"""
    def __init__(self, title:str=None, artist:str=None,
                 uri:str=None, duration:int=0, is_liked:bool=None) -> None:
        self.title: str = title
        self.artist: str = artist
        self.uri: str = uri
        self.duration: int = duration
        self.is_liked: bool = is_liked

    def _str_duration(self) -> str:
        ''' Convert seconds to 'HH:MM:SS' '''
        hour: int = 0
        minute: int = 0
        second: int = 0

        minute, second = divmod(self.duration, 60)
        hour, minute = divmod(minute, 60)
        if hour == 0:
            if minute == 0:
                return f'00:{second:02}'
            return f'{minute}:{second:02}'
        return f'{hour}::{minute:02}::{second:02}'

    def __str__(self) -> str:
        liked: str = f'{TRACK_LIKE} ' if self.is_liked else ''
        return f'{liked}{self.artist} - {self.title} ({self._str_duration()})'



FMT_STRING = '%(asctime)s [%(levelname)-8s] %(name)-30s: %(message)s'
stderr_handler = logging.StreamHandler()
stderr_handler.setFormatter(ColorFormatter(FMT_STRING))

file_handler = logging.FileHandler(f'{APP_NAME}.log')
file_handler.setFormatter(ColorFormatter(FMT_STRING))
