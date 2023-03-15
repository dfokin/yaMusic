"""Yandex.Music client for Linux"""
import asyncio
import logging

import aiotkinter

from UI import run_ui
from player.helpers import stderr_handler

logging.basicConfig(encoding='utf-8', level=logging.DEBUG, handlers=[stderr_handler])
asyncio.set_event_loop_policy(aiotkinter.TkinterEventLoopPolicy())

if __name__ == "__main__":
    asyncio.run(run_ui())
