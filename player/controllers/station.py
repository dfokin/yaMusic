"""STUB"""
import asyncio
import logging
from random import random
from typing import Dict, List, Union
from yandex_music import (
    ClientAsync,
    Dashboard,
    DownloadInfo,
    Restrictions,
    Sequence,
    Station,
    StationResult,
    StationTracksResult,
    Track,
    )
from yandex_music.exceptions import YandexMusicError
from player.helpers import aiohttp_retry, YaTrack
import player.config as cfg

ClientAsync.notice_displayed = True

_LOGGER = logging.getLogger(__name__)


YANDEX_APP_NAME: str = 'desktop_win-home-playlist_of_the_day-playlist-default'
MY_CODEC: str = 'mp3'

MY_API_RETRIES: int = 3
MY_API_RETRY_DELAY: int = 0.3
MY_API_TIMEOUT: float = 2.0



# logging.getLogger('yandex_music.client_async').setLevel(logging.WARNING)


class StationControllerError(Exception):
    """General Radio Controller error"""

RETRY_ARGS = [
    YandexMusicError,
    StationControllerError,
    ]
RETRY_KWARGS = {
    'num_tries': MY_API_RETRIES,
    'timeout': MY_API_TIMEOUT,
    'retry_delay': MY_API_RETRY_DELAY,
    'logger': _LOGGER,
    }

class StationController:
    """
    Controls Yandex.Music radio station
    """
    def __init__(self, client: ClientAsync, high_res:bool = True):
        self._high_res: bool = high_res
        self._client: ClientAsync = client

        self._station: Station = None
        self._batch: StationTracksResult = None
        self._batch_index: int = 0
        self._current_play_id: str = None
        self._current_track: Track = None
        self._current_track_int: YaTrack = None

    async def tune_station(self, station_name: str) -> YaTrack:
        """
        Starts controller for given station name and returns first track from this station
        """
        if not await self._setup_station(station_name):
            raise StationControllerError(f'No such station: {station_name} in your dashboard.')
        _LOGGER.debug('Tuned to %s station.', self._station_id)

        await self._start_new_batch()
        await self._setup_current_track()

        asyncio.create_task(
            self._inform_playback_started(
                self._current_track, self._current_play_id, self._batch.batch_id
                )
            )

        return self._current_track_int

    async def shutdown(self, played:float=0):
        """
        Stop controller
        """
        if self._current_track:
            await self._inform_playback_ended(
                self._current_track, self._current_play_id, self._batch.batch_id, played=played)
        _LOGGER.debug('Shut down.')


    async def get_next_track(self, played:float=0) -> YaTrack:
        """
        Retrieve next track from the station.
        in skipped param pass number seconds played
        """
        asyncio.create_task(
            self._inform_playback_ended(
                self._current_track, self._current_play_id, self._batch.batch_id, played=played
                )
            )
        self._cleanup_current_track()

        self._batch_index += 1
        if self._batch_index >= len(self._batch.sequence):
            await self._start_new_batch()

        await self._setup_current_track()

        asyncio.create_task(
            self._inform_playback_started(
                self._current_track, self._current_play_id, self._batch.batch_id)
            )

        return self._current_track_int

    async def like_track(self) -> bool:
        """
        Add current track to favorites
        """
        return await self._send_track_user_likes_add(self._current_track.id)

    async def apply_settings(
            self, language:str=None, diversity:str=None, mood_energy:str=None) -> bool:
        """
        Apply settings for current station
        """
        _LOGGER.debug(
            'Apply %s\'s settings: {language="%s", diversity="%s", mood_energy="%s"}.', 
            self._station.id.tag, language, diversity, mood_energy)
        if await self._apply_radio_settings(self._station_id,
            language=language, diversity=diversity, mood_energy=mood_energy):
            if self._batch:
                self._batch_index = len(self._batch.sequence)
            return True
        return False

    ### API wrappers
    # Informers
    async def _inform_playback_started(self, track: Track, play_id: str, batch_id: str):
        try:
            await self._send_track_playback_started(track, play_id)
            await self._send_radio_track_playback_started(track, batch_id)
        except StationControllerError:
            pass
        else:
            _LOGGER.debug('Informed station about start of %s.', track.id)

    async def _inform_playback_ended(
        self, track: Track, play_id: str, batch_id: str, played:float=0):
        try:
            await self._send_track_playback_ended(track, play_id, played=played)
            if played:
                await self._send_radio_track_playback_skipped(track, batch_id, played)
            else:
                await self._send_radio_track_playback_ended(track, batch_id)
        except StationControllerError:
            pass
        else:
            _LOGGER.debug('Informed station about stop of %s.', track.id)

    async def _inform_batch_started(self, batch_id: str):
        try:
            await self._send_radio_batch_started(batch_id)
        except StationControllerError:
            pass
        else:
            _LOGGER.debug('Informed station about start of batch %s.', batch_id)

    # Rotor controls
    async def _setup_station(self, station_name: str) -> bool:
        dashboard: Dashboard = await self._get_dashboard()

        station_results: List[StationResult] = dashboard.stations
        result: StationResult = None
        for result in station_results:
            station: Station = result.station
            if station.id.tag == station_name:
                self._station = station
                settings: Dict = cfg.get_station_settings(self._station.id.tag)
                if settings:
                    if not await self.apply_settings(**settings):
                        _LOGGER.warning(
                            'Cannot apply %s\'s settings: %s', self._station.id.tag, settings)
                return True

    async def _start_new_batch(self, queue=None):
        self._batch_index = 0
        self._batch = await self._get_station_tracks(self._station_id, queue=queue)
        asyncio.create_task(self._inform_batch_started(self._batch.batch_id))

    # Track controls
    async def _setup_current_track(self) -> Track:
        current_sequence: Sequence = self._batch.sequence[self._batch_index]
        self._current_track = await self._get_track(current_sequence.track.track_id)
        self._current_track_int = YaTrack(
            title=self._current_track.title,
            artist=",".join(self._current_track.artists_name()),
            uri=await self._get_track_url(self._current_track, high_res=self._high_res),
            duration=int(self._current_track.duration_ms / 1000),
            is_liked=current_sequence.liked
            )
        self._current_play_id = self._generate_play_id()

    def _cleanup_current_track(self):
        self._current_play_id = None
        self._current_track = None
        self._current_track_int = None

    async def _get_track_url(self, track: Track, codec:str=MY_CODEC, high_res:bool=False) -> str:
        dl_infos: List[DownloadInfo] = sorted(
            [d for d in await self._get_track_download_infos(track) if d.codec == codec],
            key=lambda x: x.bitrate_in_kbps
        )
        dl_info: DownloadInfo = dl_infos[-1] if high_res else dl_infos[0]
        return await self._get_track_direct_link(dl_info)

    # Helpers
    @property
    def _station_id(self) -> str:
        return f'{self._station.id.type}:{self._station.id.tag}'

    @property
    def tuned(self) -> bool:
        """Are we tuned to a station?"""
        return self._station is not None

    @property
    def station_name(self) -> str:
        """Returns the name of currently tuned station"""
        return self._station.name.strip()

    @property
    def restrictions(self) -> Restrictions:
        """Returns the settings restrictions for currently tuned station"""
        return self._station.restrictions2

    @staticmethod
    def _generate_play_id() -> str:
        def randint() -> int:
            return int(random() * 1000)
        return f'{randint()}-{randint()}-{randint()}'

    ### Low-level API methods
    # Rotor controls
    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_dashboard(self, timeout: float=MY_API_TIMEOUT) -> Dashboard:
        return await self._client.rotor_stations_dashboard(timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_station_tracks(
        self, station_id: str, queue=None, timeout: float=MY_API_TIMEOUT) -> StationTracksResult:
        return await self._client.rotor_station_tracks(station_id, queue=queue, timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _apply_radio_settings(
        self, station_id: str, language:str=None, diversity:str=None,
        mood_energy:str=None, timeout: float=MY_API_TIMEOUT) -> bool:
        return await self._client.rotor_station_settings2(
            station_id, language=language, diversity=diversity,
            mood_energy=mood_energy, timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_radio_batch_started(self, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_radio_started(
            station=self._station_id,
            from_=self._station.id_for_from,
            batch_id=batch_id,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_radio_track_playback_started(
        self, track: Track, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_track_started(
            station=self._station_id,
            track_id=track.id,
            batch_id=batch_id,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_radio_track_playback_skipped(
        self, track: Track, batch_id: str, played: float, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_skip(
            station=self._station_id,
            track_id=track.id,
            total_played_seconds=played,
            batch_id=batch_id,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_radio_track_playback_ended(
        self, track: Track, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_track_finished(
            station=self._station_id,
            track_id=track.id,
            total_played_seconds=track.duration_ms / 1000,
            batch_id=batch_id,
            timeout=timeout
        )


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
            from_=YANDEX_APP_NAME,
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
            from_=YANDEX_APP_NAME,
            track_id=track.id,
            album_id=track.albums[0].id,
            play_id=play_id,
            track_length_seconds=int(total_seconds),
            total_played_seconds=played_seconds,
            end_position_seconds=total_seconds,
            timeout=timeout
        )
