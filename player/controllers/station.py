"""STUB"""
import asyncio
import logging
from random import random
from typing import Dict, List, Optional, Union
from yandex_music import (
    ClientAsync,
    Dashboard,
    DownloadInfo,
    Restrictions,
    RotorSettings,
    Sequence,
    StationResult,
    StationTracksResult,
    Track,
    )
from yandex_music.exceptions import YandexMusicError
from player.helpers import aiohttp_retry, YaTrack
import player.config as cfg
from player import constants as const

ClientAsync.notice_displayed = True

_LOGGER = logging.getLogger(__name__)


YANDEX_APP_NAME: str = 'desktop_win-home-playlist_of_the_day-playlist-default'
MY_CODEC: str = 'mp3'

MY_API_RETRIES: int = 3
MY_API_RETRY_DELAY: int = 0.3
MY_API_TIMEOUT: float = 2.0



logging.getLogger('yandex_music.client_async').setLevel(logging.WARNING)


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
    def __init__(self):
        self.high_res: bool = cfg.get_key('high_res', True)
        self.source_id: str = cfg.get_key('source_id', default=const.DEFAULT_SOURCE)
        self._token: str = cfg.get_key('token')
        self._client: ClientAsync = None
        self._sources: List[StationResult] = []
        self._source: StationResult = None
        self._batch: StationTracksResult = None
        self._batch_index: int = 0
        self._current_play_id: str = None
        self._current_track: Track = None
        self._current_track_int: YaTrack = None

    async def init(self):
        """Initialize Yandex.Music client and populate list of available stations"""
        self._client = ClientAsync(token=self._token)
        try:
            await self._client.init()
        except YandexMusicError as exc:
            self._client = None
            raise StationControllerError(f'Cannot initialize client: {exc}')            # pylint: disable=raise-missing-from
        self._sources = await self._get_station_list()
        return self

    async def set_source(
            self, source_id: str=None,
            source_settings:RotorSettings=None, played:float=0) -> YaTrack:
        """
        Tunes to given station name, applies station settings (if any) 
        and returns first track from this station
        """
        if self._batch is not None:
            # Tuning to new station
            asyncio.create_task(
                self._inform_playback_ended(
                    self._current_track, self._current_play_id, self._batch.batch_id, played
                    )
            )
            self._cleanup_current_track()
        if not self._set_source(source_id or self.source_id):
            raise StationControllerError(f'No such station: {self.source_id} in rotor\'s stations.')
        if not await self.apply_source_settings(
            source_settings or self.get_source_settings(), force=True):
            _LOGGER.warning(
                'Failed to apply %s\'s settings.', self._source.station.id.tag)
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
        if self._client:
            del self._client
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

    async def apply_source_settings(self, settings: RotorSettings, force: bool = False) -> bool:
        """
        Apply settings for current station and store them to current config
        """
        # Do nothing if given settings are same as current source settings
        if not force and self._is_current_settings(settings):
            return True
        _LOGGER.debug(
            'Apply %s\'s settings: {language="%s", diversity="%s", mood_energy="%s"}.', 
            self._source.station.id.tag,
            settings.language, settings.diversity, settings.mood_energy)
        if await self._apply_radio_settings(self._station_id, settings):
            # Store settings to config
            cfg.set_station_settings(
                self.source_id,
                {
                    'language': settings.language,
                    'diversity': settings.diversity,
                    'mood_energy': settings.mood_energy,
                })
            if self._batch:
                self._batch_index = len(self._batch.sequence)
            return True
        return False

    def get_sources_list(self) -> List[StationResult]:
        """Return list of available stations"""
        return self._sources

    ### API wrappers
    # Informers
    async def _get_station_list(self) -> List[StationResult]:
        return list(
            set(
                await self._get_dashboard_stations() + await self._get_rotor_stations()
            )
        )

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
    def _set_source(self, station_id: str) -> bool:
        result: StationResult
        for result in self._sources:
            if result.station.id.tag == station_id:
                self._source = result
                self.source_id = station_id
                return True
        return False

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
            uri=await self._get_track_url(self._current_track, high_res=self.high_res),
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
        return f'{self._source.station.id.type}:{self._source.station.id.tag}'

    @property
    def tuned(self) -> bool:
        """Are we tuned to a station?"""
        return self._source is not None

    @property
    def source_name(self) -> str:
        """Returns the name of currently tuned station"""
        return self._source.station.name.strip()

    def get_source_restrictions(self, station_id: str=None) -> Optional[Restrictions]:
        """
        When no station_id is set, returns settings restrictions for currently tuned station
        In opposite case, returns restrictions for given station_id
        """
        if not station_id:
            if self._source and self._source.station.restrictions2:
                return self._source.station.restrictions2
            return None
        for s_r in self._sources:
            if s_r.station.id.tag == station_id:
                return s_r.station.restrictions2
        return None

    def get_source_settings(self, station_id: str=None) -> Optional[RotorSettings]:
        """
        When no station_id is set, returns settings for currently tuned station
        In opposite case, returns settings for given station_id
        If settings are set in config returns them,
        else returns default station settings received from rotor
        """
        if not station_id:
            if not self._source:
                return None
            cfg_settings: RotorSettings = self._get_cfg_settings(self._source.station.id.tag)
            if cfg_settings:
                return cfg_settings
            return self._source.settings2
        cfg_settings: RotorSettings = self._get_cfg_settings(station_id)
        if cfg_settings:
            return cfg_settings
        for s_r in self._sources:
            if s_r.station.id.tag == station_id:
                return s_r.settings2
        return None

    @staticmethod
    def _get_cfg_settings(station_id: str) -> Optional[RotorSettings]:
        cfg_settings: Dict = cfg.get_station_settings(station_id)
        if cfg_settings:
            return RotorSettings(
                language = cfg_settings.get('language', None),
                diversity = cfg_settings.get('diversity', None),
                mood_energy = cfg_settings.get('mood_energy', None))
        return None

    @staticmethod
    def _generate_play_id() -> str:
        def randint() -> int:
            return int(random() * 1000)
        return f'{randint()}-{randint()}-{randint()}'

    def _is_current_settings(self, settings: RotorSettings):
        curr_settings: RotorSettings = self.get_source_settings()
        return  settings.language == curr_settings.language and \
                settings.diversity == curr_settings.diversity and \
                settings.mood_energy == curr_settings.mood_energy

    ### Low-level API methods
    # Rotor controls
    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_dashboard_stations(self, timeout: float=MY_API_TIMEOUT) -> List[StationResult]:
        dashboard: Dashboard = await self._client.rotor_stations_dashboard(timeout=timeout)
        return dashboard.stations

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_rotor_stations(self, timeout: float=MY_API_TIMEOUT) -> List[StationResult]:
        return await self._client.rotor_stations_list(timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_station_tracks(
        self, station_id: str, queue=None, timeout: float=MY_API_TIMEOUT) -> StationTracksResult:
        return await self._client.rotor_station_tracks(station_id, queue=queue, timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _apply_radio_settings(
        self, station_id: str, settings: RotorSettings, timeout: float=MY_API_TIMEOUT) -> bool:
        return await self._client.rotor_station_settings2(
            station_id, language=settings.language, diversity=settings.diversity,
            mood_energy=settings.mood_energy, timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_radio_batch_started(self, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_radio_started(
            station=self._station_id,
            from_=self._source.station.id_for_from,
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
