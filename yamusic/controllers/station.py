"""STUB"""
import asyncio
import logging
from typing import Dict, List, Optional

from yandex_music import (
    Dashboard,
    Restrictions,
    RotorSettings,
    Sequence,
    StationResult,
    StationTracksResult,
    Track,
    Value,
    )

from utils.config import get_key, get_station_settings, set_station_settings
from utils.decorators import aiohttp_retry

from .error import ControllerError
from .source import (
    RETRY_ARGS,
    RETRY_KWARGS,
    MY_API_TIMEOUT,
    SourceController,
    )
from .track import YaTrack

_LOGGER = logging.getLogger(__name__)


DEFAULT_RADIO_SOURCE    : str = 'onyourwave'

class StationController(SourceController):
    """
    Controls Yandex.Music radio station
    """
    def __init__(self):
        super().__init__()
        self._station_id: str = get_key('radio_id', default=DEFAULT_RADIO_SOURCE)
        self._stations: List[StationResult] = []
        self._source: StationResult = None
        self._batch: StationTracksResult = None
        self._batch_index: int = 0

    async def init(self):
        """Initialize Yandex.Music client and populate list of available stations"""
        await super().init()
        self._stations = await self._get_station_list()
        return self

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
            raise ControllerError(f'No such station: {self.source_id} in rotor\'s stations.')
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
        if await self._apply_rotor_settings(self._station_id, settings):
            # Store settings to config
            set_station_settings(
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

    def get_sources_list(self) -> List[Value]:
        """Return list of available stations"""
        return [Value(name=s.station.name, value=s.station.id.tag) for s in self._stations]

    ### API wrappers
    # Informers
    async def _inform_playback_started(self, track: Track, play_id: str, batch_id: str):
        await self._inform_track_playback_started(track, play_id)
        try:
            await self._send_rotor_track_playback_started(track, batch_id)
        except ControllerError:
            pass
        else:
            _LOGGER.debug('Informed Rotor API about start of track %s.', track.id)

    async def _inform_playback_ended(
        self, track: Track, play_id: str, batch_id: str, played:float=0):
        await self._inform_track_playback_ended(track, play_id, played=played)
        try:
            if played:
                await self._send_rotor_track_playback_skipped(track, batch_id, played)
            else:
                await self._send_rotor_track_playback_ended(track, batch_id)
        except ControllerError:
            pass
        else:
            _LOGGER.debug('Informed Rotor API about stop of track %s.', track.id)

    async def _inform_batch_started(self, batch_id: str):
        try:
            await self._send_rotor_batch_started(batch_id)
        except ControllerError:
            pass
        else:
            _LOGGER.debug('Informed Rotor API about start of batch %s.', batch_id)

    # Rotor controls
    async def _get_station_list(self) -> List[StationResult]:
        return list(
            set(
                await self._get_dashboard_stations() + await self._get_rotor_stations()
            )
        )

    def _set_source(self, station_id: str) -> bool:
        result: StationResult
        for result in self._stations:
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
    async def _setup_current_track(self) -> None:
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
        if self._source:
            return self._source.station.name.strip()
        return 'None'

    @property
    def source_id(self) -> str:
        """Returns ID of currently tuned station"""
        return self._station_id

    def get_source_restrictions(self, station_id: str=None) -> Optional[Restrictions]:
        """
        When no station_id is set, returns settings restrictions for currently tuned station
        In opposite case, returns restrictions for given station_id
        """
        if not station_id:
            if self._source and self._source.station.restrictions2:
                return self._source.station.restrictions2
            return None
        for s_r in self._stations:
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
        for s_r in self._stations:
            if s_r.station.id.tag == station_id:
                return s_r.settings2
        return None

    @staticmethod
    def _get_cfg_settings(station_id: str) -> Optional[RotorSettings]:
        cfg_settings: Dict = get_station_settings(station_id)
        if cfg_settings:
            return RotorSettings(
                language = cfg_settings.get('language', None),
                diversity = cfg_settings.get('diversity', None),
                mood_energy = cfg_settings.get('mood_energy', None))
        return None

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
    async def _apply_rotor_settings(
        self, station_id: str, settings: RotorSettings, timeout: float=MY_API_TIMEOUT) -> bool:
        return await self._client.rotor_station_settings2(
            station_id, language=settings.language, diversity=settings.diversity,
            mood_energy=settings.mood_energy, timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_rotor_batch_started(self, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_radio_started(
            station=self._station_id,
            from_=self._source.station.id_for_from,
            batch_id=batch_id,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_rotor_track_playback_started(
        self, track: Track, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_track_started(
            station=self._station_id,
            track_id=track.id,
            batch_id=batch_id,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_rotor_track_playback_skipped(
        self, track: Track, batch_id: str, played: float, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_skip(
            station=self._station_id,
            track_id=track.id,
            total_played_seconds=played,
            batch_id=batch_id,
            timeout=timeout
        )

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _send_rotor_track_playback_ended(
        self, track: Track, batch_id: str, timeout: float=MY_API_TIMEOUT):
        await self._client.rotor_station_feedback_track_finished(
            station=self._station_id,
            track_id=track.id,
            total_played_seconds=track.duration_ms / 1000,
            batch_id=batch_id,
            timeout=timeout
        )
