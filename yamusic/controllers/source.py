"""Prototype for Yandex.Music source controller"""
import logging
from random import random
from typing import List, Union

from yandex_music import (
    ClientAsync,
    DownloadInfo,
    RotorSettings,
    Track,
    Value,
    )
from yandex_music.exceptions import YandexMusicError

from utils.config import get_key
from utils.decorators import aiohttp_retry

from .error import ControllerError
from .track import YaTrack

ClientAsync.notice_displayed = True

_LOGGER = logging.getLogger(__name__)

logging.getLogger('yandex_music.client_async').setLevel(logging.WARNING)

_YANDEX_APP_NAME : str = 'desktop_win-home-playlist_of_the_day-playlist-default'
_CODEC : str = 'mp3'

MY_API_RETRIES: int = 3
MY_API_RETRY_DELAY: int = 0.3
MY_API_TIMEOUT: float = 2.0
RETRY_ARGS = [
    YandexMusicError,
    ControllerError,
    ]
RETRY_KWARGS = {
    'num_tries': MY_API_RETRIES,
    'timeout': MY_API_TIMEOUT,
    'retry_delay': MY_API_RETRY_DELAY,
    'logger': _LOGGER,
    }

class SourceController:
    """
    Controls abstract Yandex.Music source
    """
    def __init__(self, client: ClientAsync):
        self.high_res: bool = get_key('high_res', True)
        self._client: ClientAsync = client
        self._current_play_id: str = None
        self._current_track: Track = None
        self._current_track_int: YaTrack = None

    async def init(self):
        """Initialize Yandex.Music client and populate list of available stations"""
        try:
            await self._client.init()
        except YandexMusicError as exc:
            self._client = None
            raise ControllerError(f'Cannot initialize client: {exc}')                               # pylint: disable=raise-missing-from

    async def shutdown(self):
        """
        Stop controller
        """
        raise NotImplementedError

    async def set_source(self, source_id: str=None,
            source_settings:RotorSettings=None, played:float=0) -> YaTrack:
        """
        Sets up current source 
        and returns first track from it
        """
        raise NotImplementedError

    async def apply_source_settings(self, settings: RotorSettings, force: bool=False) -> bool:
        """
        Apply settings for current source
        """
        raise NotImplementedError

    async def get_next_track(self) -> YaTrack:
        """
        Retrieve next track from the source.
        in skipped param pass number seconds played
        """
        raise NotImplementedError

    async def like_track(self) -> bool:
        """
        Add current track to favorites
        """
        return await self._send_track_user_likes_add(self._current_track.id)

    def get_sources_list(self) -> List[Value]:
        """Return list of available sources"""
        raise NotImplementedError

    def get_short_playlist(self) -> List[YaTrack]:
        """
        Return list of internal representations of tracks in current playlist
        download and user_likes info is not provided
        """
        raise NotImplementedError

    def get_playlist_position(self) -> int:
        """
        Return index of current playlist
        """
        raise NotImplementedError

    async def set_playlist_position(self, position: int, played:float=0) -> YaTrack:
        """
        Set index of current playlist
        """
        raise NotImplementedError

    @property
    def source_name(self) -> str:
        """Returns the name of current source"""
        raise NotImplementedError

    @property
    def source_id(self) -> str:
        """Returns ID of current source"""
        raise NotImplementedError

    def _to_internal_short(self, track: Track) -> YaTrack:
        return YaTrack(
            title=track.title,
            artist=",".join(track.artists_name()),
            duration=int(track.duration_ms / 1000),
            )

    ### API wrappers
    # Track controls
    async def _setup_current_track(self) -> None:
        raise NotImplementedError

    def _cleanup_current_track(self) -> None:
        self._current_play_id = None
        self._current_track = None
        self._current_track_int = None

    ### API wrappers
    # Informers
    async def _inform_track_playback_started(self, track: Track, play_id: str):
        """Inform Track API about start of playback"""
        try:
            await self._send_track_playback_started(track, play_id)
        except ControllerError:
            pass
        else:
            _LOGGER.debug('Informed Track API about start of track %s.', track.id)

    async def _inform_track_playback_ended(
        self, track: Track, play_id: str, played:float=0):
        """Inform Track API about playback completion"""
        try:
            await self._send_track_playback_ended(track, play_id, played=played)
        except ControllerError:
            pass
        else:
            _LOGGER.debug('Informed Track API about stop of track %s.', track.id)

    # Track controls
    async def _get_track_url(
            self, track: Track, codec:str=_CODEC, high_res:bool=False) -> str:
        dl_infos: List[DownloadInfo] = sorted(
            [d for d in await self._get_track_download_infos(track) if d.codec == codec],
            key=lambda x: x.bitrate_in_kbps
        )
        dl_info: DownloadInfo = dl_infos[-1] if high_res else dl_infos[0]
        return await self._get_track_direct_link(dl_info)

    # Helpers
    @staticmethod
    def _generate_play_id() -> str:
        def randint() -> int:
            return int(random() * 1000)
        return f'{randint()}-{randint()}-{randint()}'

    ### Low-level API methods
    # Track controls
    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_track(self, track_id:str, timeout: float=MY_API_TIMEOUT) -> Track:
        tracks: List[Track] = await self._client.tracks([track_id], timeout=timeout)
        return tracks[0]

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_track_download_infos(
        self, track: Track, timeout: float=MY_API_TIMEOUT) -> List[DownloadInfo]:
        return await track.get_download_info_async(timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_track_direct_link(
        self, dl_info: DownloadInfo, timeout: float=MY_API_TIMEOUT) -> str:
        return await dl_info.get_direct_link_async(timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_track_user_likes_add(
        self, track_id: Union[str, int], timeout: float=MY_API_TIMEOUT) -> bool:
        return await self._client.users_likes_tracks_add(track_id, timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_track_playback_started(
        self, track: Track, play_id: str, timeout: float=MY_API_TIMEOUT):
        total_seconds = track.duration_ms / 1000
        await self._client.play_audio(
            from_=_YANDEX_APP_NAME,
            track_id=track.id,
            album_id=track.albums[0].id,
            play_id=play_id,
            track_length_seconds=int(total_seconds),
            total_played_seconds=0,
            end_position_seconds=total_seconds,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_track_playback_ended(
        self, track: Track, play_id: str, played: float = 0, timeout: float=MY_API_TIMEOUT):
        played_seconds = played if played else track.duration_ms / 1000
        total_seconds = track.duration_ms / 1000
        await self._client.play_audio(
            from_=_YANDEX_APP_NAME,
            track_id=track.id,
            album_id=track.albums[0].id,
            play_id=play_id,
            track_length_seconds=int(total_seconds),
            total_played_seconds=played_seconds,
            end_position_seconds=total_seconds,
            timeout=timeout
        )
