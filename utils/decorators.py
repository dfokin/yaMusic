"""
Controller helpers
"""
from asyncio import sleep
from functools import wraps


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
