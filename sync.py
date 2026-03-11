"""Sync favorites"""
import sys
from typing import List


import asyncio
import json
import logging
import os

import aiotkinter
import requests

from mutagen.mp3 import MP3, error
from mutagen.id3 import ID3, TIT2, TPE1, TAL


from yandex_music import ClientAsync
import utils.config as cfg
from utils.log_handlers import stderr_handler
from utils.token import get_token

from yamusic.controllers import (
    ControllerError,
    PlaylistController,
    YaTrack
    )

logging.basicConfig(encoding='utf-8', level=logging.INFO, handlers=[stderr_handler])
asyncio.set_event_loop_policy(aiotkinter.TkinterEventLoopPolicy())

async def sync():
    """
    sync whole favorites collection
    """
    logger = logging.getLogger(__name__)
    sync_dir: str = cfg.get_key('sync_dir')
    ssync_file: str = os.path.join(sync_dir, 'syncdata.json')
    synced: List[str] = []
    exit_code: int  = 0
    downloaded: int = 0
    skipped: int = 0
    errored: int = 0

    if os.path.exists(ssync_file):
        with open(ssync_file, 'r', encoding='utf-8') as f:
            synced = json.load(f)

    try:
        client: ClientAsync = ClientAsync(token=get_token())
        controller = await PlaylistController(client, playlist_id='my_likes').init()
        await controller.set_source()
    except ControllerError as exc:
        logger.error('Cannot start: %s', exc)
        sys.exit(127)

    logger.info('Got %d tracks in collection', len(controller._playlist) )
    try:
        for t in controller._playlist:
            if t.track_id in synced:
                skipped += 1
            else:
                url: str = await controller._get_track_url(t, codec='mp3', high_res=True)
                current_track: YaTrack = controller._to_internal_short(t)
                await asyncio.sleep(1)
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    file_name: str = os.path.join(
                        sync_dir,
                        f'{current_track.artist.replace(os.path.sep,'_')} - {current_track.album.replace(os.path.sep,'_')} - {current_track.title.replace(os.path.sep,'_')} ({current_track.track_id}).mp3')
                    with open(file_name, 'wb') as f:
                        f.write(response.content)
                    audio = MP3(file_name, ID3=ID3)
                    try:
                        audio.add_tags()
                    except error:
                        pass # tags already present

                    audio.tags.add(TIT2(encoding=3, text=current_track.title))
                    audio.tags.add(TPE1(encoding=3, text=current_track.artist))
                    audio.tags.add(TAL(encoding=3, text=current_track.album))
                    audio.save()
                    synced.append(current_track.track_id)
                    downloaded += 1
                    logger.info('Sync: %s', file_name)
                else:
                    logger.warning(
                        'Failed (%s): %s', 
                        response.status_code, 
                        f'{current_track.artist} - {current_track.album} - {current_track.title} ({current_track.track_id})')
                    errored += 1
    except Exception as exc:
        logger.error('Thrown %s, exiting', exc)
        exit_code = 128
    finally:
        with open(ssync_file, 'w', encoding='utf-8') as f:
            json.dump(synced, f, ensure_ascii=False, indent=2)
        logger.info(
            'Sync completed. Synced: %d. Skipped: %d. Errored: %d', 
            downloaded, skipped, errored)
        sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(sync())
