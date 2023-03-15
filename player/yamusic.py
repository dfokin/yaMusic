"""Plays media from Yandex.Music using embedded Gstreamer pipeline"""
import logging
from typing import Dict

from aioprocessing import AioManager, AioQueue, AioProcess
from yandex_music import ClientAsync, Restrictions
from yandex_music.exceptions import YandexMusicError

from player.gst import GstPlayer
from player.helpers import aiohttp_retry, YaTrack
import player.constants as const
from player.controllers.station import StationController, StationControllerError

_LOGGER = logging.getLogger(__name__)

_MY_API_RETRIES: int = 3
_MY_API_RETRY_DELAY: int = 0.3
_MY_API_TIMEOUT: float = 2.0

class YaPlayerError(Exception):
    """General Yandex.Music player error"""

_RETRY_ARGS = [
    YandexMusicError,
    YaPlayerError,
    ]
_RETRY_KWARGS = {
    'num_tries': _MY_API_RETRIES,
    'timeout': _MY_API_TIMEOUT,
    'retry_delay': _MY_API_RETRY_DELAY,
    'logger': _LOGGER,
    }

class YaPlayer:
    """
        Wraps gstreamer process, who executes playback playbin, and yaMusic 
        controller, who queries Yandex Music API for media URIs.
        Allows media uri queueing and comminicating with the process via IPC.
        Media URIs and player commands are sent to gstreamer via media and command queues
        Messages from player will be passed to user via ui_event_queue.

    """
    def __init__(self, 
                 ui_event_queue: AioQueue,
                 mode:str = const.DEFAULT_MODE,
                 source:str = const.DEFAULT_SOURCE,
                 high_res: bool = True,
                 token: str = None
                 ):
        self._dashboard: AioManager = AioManager().dict({
            const.ATTR_STATE: None,
            const.ATTR_DURATION: None,
            const.ATTR_POSITION: None,
            const.ATTR_VOLUME: None,
            const.ATTR_TITLE: None,
            const.ATTR_ERROR: None,
            const.ATTR_URI: None
        })
        self.mode: str = mode
        self.high_res: str = high_res
        self.source_id: str = source
        self._token = token
        self._client: ClientAsync = ClientAsync(token=self._token)
        self._command_queue: AioQueue = AioQueue()
        self._media_queue: AioQueue = AioQueue()
        self._ui_event_queue: AioQueue = ui_event_queue
        self._controller: StationController = None
        self._gstreamer: AioProcess = AioProcess(
            target=GstPlayer(
                self._dashboard, self._command_queue,
                self._media_queue, ui_event_queue
                ).run
            )

    async def init(self):
        """
        Initialize YaMusicPlayer.
        Creates API client, which is used to get tracks
        """
        await self._emit_status_event("Initializing client...")
        try:
            await self._init_client()
            return self
        except YandexMusicError as exc:
            if self._client:
                del self._client
                self._client = None
            raise YaPlayerError(f'Cannot initialize client: {exc}')         # pylint: disable=raise-missing-from

    async def shutdown(self):
        """Shut down Gstreamer and controller."""
        await self._emit_status_event("Shutting dow...")
        if self._controller:
            await self._controller.shutdown(played=self.position)
            del self._controller
        if self._client:
            del self._client
        if self._gstreamer.pid:                                                 # pylint: disable=no-member
            await self._gs_command(const.CMD_SHUTDOWN)
            await self._gstreamer.coro_join()                                   # pylint: disable=no-member
            del self._gstreamer

    async def start_player(self) -> YaTrack:
        """
        Creates Controller for given mode, and retrieves first track to play
        """
        try:
            if self.mode == const.MODE_RADIO:
                await self._emit_status_event("Starting...")
                self._controller = StationController(self._client, high_res=self.high_res)
                track: YaTrack = await self._controller.tune_station(self.source_id)
        except StationControllerError as exc:
            raise YaPlayerError(f'Cannot start: {exc}')              # pylint: disable=raise-missing-from
        await self._set_title(str(track))
        await self._enqueue(track.uri)
        self._gstreamer.start()                                                 # pylint: disable=no-member
        _LOGGER.info('Started GstPlayer as PID %s', self._gstreamer.pid)        # pylint: disable=no-member

    def get_restrictions(self) -> Restrictions:
        """Get settings restrictions for active controller"""
        return self._controller.restrictions

    async def apply_settings(self, settings: Dict[str, str]) -> bool:
        """Set settings for active controller"""
        await self._emit_status_event("Applying new settings...")
        try:
            return await self._controller.apply_settings(**settings)
        except StationControllerError as exc:
            await self._emit_error(f'Cannot apply settings: {exc}.')
            return

    async def get_next_track(self):
        """Get next track from controller."""
        await self._emit_status_event("Requesting track...")
        try:
            track: YaTrack = await self._controller.get_next_track()
        except StationControllerError as exc:
            await self._emit_error(f'Cannot retrieve track: {exc}.')
            return
        await self._set_title(str(track))
        await self._enqueue(track.uri)
        await self.play()

    async def skip(self):
        """Skip current track and play next."""
        await self._emit_status_event("Requesting track...")
        try:
            track: YaTrack = await self._controller.get_next_track(played=self.position)
        except StationControllerError as exc:
            await self._emit_error(f'Cannot retrieve track: {exc}.')
            return
        await self._set_title(str(track))
        await self._enqueue(track.uri)
        await self._gs_command(const.CMD_SKIP)

    async def like_track(self):
        """Add track to favorites"""
        await self._emit_status_event("Setting liked track...")
        try:
            return await self._controller.like_track()
        except StationControllerError as exc:
            await self._emit_error(f'Cannot like track: {exc}.')
            return False

    async def play(self):
        """Start to play media."""
        await self._gs_command(const.CMD_PLAY)

    async def pause(self):
        """Pause playback."""
        await self._gs_command(const.CMD_PAUSE)

    async def stop(self):
        """Stop playback."""
        await self._gs_command(const.CMD_STOP)

    async def play_again(self):
        """Skip 10% of media"""
        await self._gs_command(const.CMD_AGAIN)

    async def skip_forward(self):
        """Skip 10% of media"""
        await self._gs_command(const.CMD_SKIP_F)

    async def skip_back(self):
        """Back 10% of media"""
        await self._gs_command(const.CMD_SKIP_B)

    async def set_volume(self, volume):
        """Set volume."""
        await self._gs_command(const.CMD_SET_VOLUME, volume=volume)

    @property
    def title(self):
        """Get track title tag."""
        return self._dashboard[const.ATTR_TITLE]

    @property
    def mode_state(self) -> str:
        """Get current player mode."""
        mode: str = const.MODE_ICONS[self.mode]
        if self.high_res:
            mode = f'{mode} {const.HI_RES}'
        if self.mode == const.MODE_RADIO:
            if self._controller and self._controller.tuned:
                mode = f'{mode} {self._controller.station_name}'
        return mode

    @property
    def state(self):
        """Get state."""
        return self._dashboard[const.ATTR_STATE]

    @property
    def duration(self):
        """Get duration."""
        return self._dashboard[const.ATTR_DURATION]

    @property
    def position(self):
        """Get position."""
        return self._dashboard[const.ATTR_POSITION]

    @property
    def uri(self):
        """Get URI."""
        return self._dashboard[const.ATTR_URI]

    @property
    def volume(self) -> float:
        """Get volume."""
        return self._dashboard[const.ATTR_VOLUME]

    @property
    def error(self):
        """Get error."""
        return self._dashboard[const.ATTR_ERROR]

    @position.setter
    async def position(self, position):
        """Set position."""
        await self._gs_command(const.CMD_SET_POSITION, position=position)

    async def _set_title(self, title: str):
        self._dashboard[const.ATTR_TITLE] = title
        await self._emit_tags_event()

    async def _enqueue(self, uri: str):
        if uri.startswith("/"):
            uri = f'file://{uri}'
        await self._media_queue.coro_put(uri)                   # pylint: disable=no-member

    async def _gs_command(self, name, **kwargs):
        """Queue a command to gstreamer process."""
        await self._command_queue.coro_put((name, kwargs))      # pylint: disable=no-member

    async def _emit_status_event(self, description: str):
        await self._ui_event_queue.coro_put(dict(type=const.TYPE_STATUS, status=description))

    async def _emit_tags_event(self):
        await self._ui_event_queue.coro_put(dict(type=const.TYPE_TAGS))

    async def _emit_state_event(self):
        await self._ui_event_queue.coro_put(dict(type=const.TYPE_STATE))

    async def _emit_error(self, error: str):
        _LOGGER.error(error)
        self._dashboard[const.ATTR_STATE] = const.STATE_ERR
        self._dashboard[const.ATTR_ERROR] = error
        await self._emit_state_event()

    ### Low-level API methods
    # General methods
    @aiohttp_retry(*_RETRY_ARGS, **_RETRY_KWARGS)
    async def _init_client(self, timeout: float=_MY_API_TIMEOUT) -> ClientAsync:
        return await self._client.init(timeout=timeout)
