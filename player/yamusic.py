"""Plays media from Yandex.Music using embedded Gstreamer pipeline"""
import logging
from typing import Optional, List, Tuple

from aioprocessing import AioManager, AioQueue, AioProcess
from yandex_music import Restrictions, RotorSettings, StationResult

import player.config as cfg
import player.constants as const
from player.controllers.station import StationController, StationControllerError
from player.gst import GstPlayer
from player.helpers import YaTrack

_LOGGER = logging.getLogger(__name__)

class YaPlayerError(Exception):
    """General Yandex.Music player error"""

class YaPlayer:
    """
        Wraps gstreamer process, who executes playback playbin, and yaMusic 
        controller, who queries Yandex Music API for media URIs.
        Allows media uri queueing and comminicating with the process via IPC.
        Media URIs and player commands are sent to gstreamer via media and command queues
        Messages from player will be passed to user via ui_event_queue.

    """
    def __init__(self, ui_event_queue: AioQueue):
        self._dashboard: AioManager = AioManager().dict({
            const.ATTR_STATE: None,
            const.ATTR_DURATION: None,
            const.ATTR_POSITION: None,
            const.ATTR_VOLUME: None,
            const.ATTR_TITLE: None,
            const.ATTR_ERROR: None,
            const.ATTR_URI: None
        })
        self.mode: str = cfg.get_key('mode', default=const.DEFAULT_MODE)
        self._command_queue: AioQueue = AioQueue()
        self._media_queue: AioQueue = AioQueue()
        self._ui_event_queue: AioQueue = ui_event_queue
        self._controller: StationController = None
        self._gstreamer: AioProcess = None

    async def init(self):
        """
        Initialize underlying controller.
        """
        await self._emit_status_event("Starting controller")
        try:
            if self.mode == const.MODE_RADIO:
                self._controller = await StationController().init()
            return self
        except StationControllerError as exc:
            raise YaPlayerError(f'Cannot start controller: {exc}')               # pylint: disable=raise-missing-from

    async def start(self) -> YaTrack:
        """
        Retrieve first track from controller and start playback
        """
        self._gstreamer = AioProcess(
            target=GstPlayer(
                self._dashboard, self._command_queue,
                self._media_queue, self._ui_event_queue
                ).run
            )
        _LOGGER.debug('Started GstPlayer as PID %s', self._gstreamer.pid)        # pylint: disable=no-member
        try:
            track: YaTrack = await self._controller.set_source()
        except StationControllerError as exc:
            raise YaPlayerError(f'Cannot start: {exc}')                         # pylint: disable=raise-missing-from
        await self._set_title(str(track))
        await self._enqueue(track.uri)
        self._gstreamer.start()                                                 # pylint: disable=no-member
        await self.set_volume(cfg.get_key('volume', default=0.5))

    async def shutdown(self):
        """Shut down Gstreamer and controller."""
        await self._emit_status_event("Shutting down")
        self._save_state()
        if self._controller:
            await self._controller.shutdown(played=self.position)
            del self._controller
        if self._gstreamer.pid:                                                 # pylint: disable=no-member
            await self._gs_command(const.CMD_SHUTDOWN)
            await self._gstreamer.coro_join()                                   # pylint: disable=no-member
            del self._gstreamer

    def get_sources_list(self) -> Optional[List[StationResult]]:
        """Get settings restrictions for active source"""
        return self._controller.get_sources_list()

    def get_source_restrictions(self, station_id: str=None) -> Optional[Restrictions]:
        """Get settings restrictions for active source"""
        return self._controller.get_source_restrictions(station_id=station_id)

    def get_source_settings(self, station_id: str=None) -> Optional[RotorSettings]:
        """Get settings for active source"""
        return self._controller.get_source_settings(station_id=station_id)

    async def apply_source_settings(self, settings: Tuple[str, RotorSettings]) -> bool:
        """Set settings for active controller"""
        await self._emit_status_event("Applying new settings...")
        try:
            if settings[0] == self._controller.source_id:
                return await self._controller.apply_source_settings(settings[1])
            return await self._switch_source(settings)
        except StationControllerError as exc:
            await self._emit_error(f'Cannot apply new settings: {exc}.')
            return False

    async def _switch_source(self, settings: Tuple[str, RotorSettings]) -> bool:
        s_id, r_s = settings
        _LOGGER.debug('Switching to new source: %s', s_id)
        try:
            track: YaTrack = await self._controller.set_source(
                source_id=s_id, source_settings=r_s, played=self.position)
        except StationControllerError as exc:
            raise YaPlayerError(f'Cannot tune: {exc}')                         # pylint: disable=raise-missing-from
        await self._set_title(str(track))
        await self._enqueue(track.uri)
        await self._gs_command(const.CMD_SKIP)
        return True


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

    async def like_track(self) -> bool:
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
    def title(self) -> str:
        """Get track title tag."""
        return self._dashboard[const.ATTR_TITLE]

    @property
    def mode_state(self) -> str:
        """Get current player mode."""
        mode: str = const.MODE_ICONS[self.mode]
        if self._controller.high_res:
            mode = f'{mode} {const.HI_RES}'
        if self.mode == const.MODE_RADIO:
            if self._controller and self._controller.tuned:
                mode = f'{mode} {self._controller.source_name}'
        return mode

    @property
    def source_id(self) -> str:
        """Get ID of underlying controller's current source"""
        return self._controller.source_id

    @property
    def state(self) -> str:
        """Get state."""
        return self._dashboard[const.ATTR_STATE]

    @property
    def duration(self):
        """Get duration."""
        return self._dashboard[const.ATTR_DURATION]

    @property
    def position(self) -> int:
        """Get position."""
        return self._dashboard[const.ATTR_POSITION]

    @property
    def uri(self) -> str:
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

    def _save_state(self):
        cfg.set_key('mode', self.mode)
        cfg.set_key('volume', self.volume)
        cfg.set_key('source_id', self._controller.source_id)
        cfg.set_key('high_res', self._controller.high_res)
        cfg.save()

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
