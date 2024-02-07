"""Plays media from Yandex.Music using embedded Gstreamer pipeline"""
import logging
from typing import Optional, List, Tuple

from aioprocessing import AioManager, AioQueue, AioProcess
from yandex_music import ClientAsync, Restrictions, RotorSettings, Value

import utils.config as cfg
import utils.constants.player as const
import utils.constants.events as ev

from .controllers import (
    ArtistController,
    ControllerError,
    SourceController,
    PlaylistController,
    StationController,
    YaTrack
    )
from .gstreamer import gst

_LOGGER = logging.getLogger(__name__)

class YaPlayerError(Exception):
    """General Yandex.Music player error"""

class YaPlayer:
    """
        Wraps gstreamer process, who executes playback playbin, and yaMusic 
        controller, who queries Yandex Music API for media URIs.
        Allows media uri queueing and comminicating with the process via IPC.
        Media URIs and player commands are sent to gstreamer via media and command queues
        Messages from player are passed to consumer via ui_event_queue.
    """
    def __init__(self, ui_event_queue: AioQueue):
        self.mode: str = cfg.get_key('mode', default=const.DEFAULT_MODE)
        self.current_track: YaTrack = None
        self._client: ClientAsync = ClientAsync(token=cfg.get_key('token'))
        self._dashboard: AioManager = AioManager().dict(gst.DASHBOARD)
        self._command_queue: AioQueue = AioQueue()
        self._media_queue: AioQueue = AioQueue()
        self._ui_event_queue: AioQueue = ui_event_queue
        self._controller: SourceController = None
        self._gstreamer: AioProcess = None

    async def init(self):
        """
        Initialize underlying controller.
        """
        await self._emit_status_event("Starting controller")
        try:
            if self.mode == const.MODE_RADIO:
                self._controller = await StationController(self._client).init()
            elif self.mode == const.MODE_PLAYLIST:
                self._controller = await PlaylistController(self._client).init()
            elif self.mode == const.MODE_ARTIST:
                self._controller = await ArtistController(self._client).init()
            return self
        except ControllerError as exc:
            raise YaPlayerError(f'Cannot start controller: {exc}')                                  # pylint: disable=raise-missing-from

    async def start(self) -> YaTrack:
        """
        Retrieve first track from controller and start playback
        """
        try:
            track: YaTrack = await self._controller.set_source()
        except ControllerError as exc:
            raise YaPlayerError(f'Cannot start: {exc}')                                             # pylint: disable=raise-missing-from
        self._gstreamer = AioProcess(
            target=gst.GstPlayer(
                self._dashboard, self._command_queue,
                self._media_queue, self._ui_event_queue
                ).run
            )
        self._gstreamer.start()                                                                     # pylint: disable=no-member
        _LOGGER.debug('Started GstPlayer as PID %s', self._gstreamer.pid)                           # pylint: disable=no-member
        await self._enqueue(track.uri)
        await self._set_current(track)
        await self.set_volume(cfg.get_key('volume', default=0.5))

    async def shutdown(self):
        """Shut down Gstreamer and controller."""
        await self._emit_status_event("Shutting down")
        self._save_state()
        if self._controller:
            await self._controller.shutdown(played=self.position)
            del self._controller
        if self._client:
            del self._client
        if self._gstreamer and self._gstreamer.pid:                                                 # pylint: disable=no-member
            await self._gs_command(gst.CMD_SHUTDOWN)
            await self._gstreamer.coro_join()                                                       # pylint: disable=no-member
            del self._gstreamer

    async def switch_mode(self, mode: str):
        """Switch mode of player"""
        if self.mode == mode:
            return
        self._save_state()
        self.mode = mode
        await self._controller.shutdown(played=self.position)
        try:
            if self.mode == const.MODE_RADIO:
                self._controller = await StationController(self._client).init()
            elif self.mode == const.MODE_PLAYLIST:
                self._controller = await PlaylistController(self._client).init()
            elif self.mode == const.MODE_ARTIST:
                self._controller = await ArtistController(self._client).init()
            track: YaTrack = await self._controller.set_source()
            if not track:
                return
        except ControllerError as exc:
            raise YaPlayerError(f'Cannot switch mode: {exc}')                                       # pylint: disable=raise-missing-from
        await self._enqueue(track.uri)
        await self._set_current(track)
        await self._gs_command(gst.CMD_SKIP_NEXT)

    def get_sources_list(self) -> Optional[List[Value]]:
        """Get settings restrictions for active source"""
        return self._controller.get_sources_list()

    def get_source_restrictions(self, station_id: str=None) -> Optional[Restrictions]:
        """Get settings restrictions for active source"""
        return self._controller.get_source_restrictions(station_id=station_id)

    def get_source_settings(self, station_id: str=None) -> Optional[RotorSettings]:
        """Get settings for active source"""
        return self._controller.get_source_settings(station_id=station_id)

    def get_short_playlist(self) -> List[YaTrack]:
        """Get current playlist without download info"""
        return self._controller.get_short_playlist()

    def get_playlist_position(self) -> int:
        """Get current playlist position"""
        return self._controller.get_playlist_position()

    def query_artist(self, **kwargs) -> None:
        """Query artist controller for content"""
        if self.mode == const.MODE_ARTIST:
            return self._controller.query(**kwargs)

    async def apply_source_settings(self, settings: Tuple[str, RotorSettings]) -> bool:
        """Set settings for active controller"""
        await self._emit_status_event("Applying new settings...")
        try:
            if settings[0] == self._controller.source_id:
                if self.mode == const.MODE_ARTIST:
                    if not self._gstreamer:
                        await self.start()
                        self._save_state()
                        return True
                    return await self._switch_source(settings)
                res: bool =  await self._controller.apply_source_settings(settings[1])
                if res:
                    self._save_state()
                return res
            return await self._switch_source(settings)
        except ControllerError as exc:
            await self._emit_error(f'Cannot apply new settings: {exc}.')
            return False

    async def _switch_source(self, settings: Tuple[str, RotorSettings]) -> bool:
        s_id, r_s = settings
        _LOGGER.debug('Switching to new source: %s', s_id)
        try:
            track: YaTrack = await self._controller.set_source(
                source_id=s_id, source_settings=r_s, played=self.position)
        except ControllerError as exc:
            raise YaPlayerError(f'Cannot tune: {exc}')                                              # pylint: disable=raise-missing-from
        await self._enqueue(track.uri)
        await self._set_current(track)
        await self._gs_command(gst.CMD_SKIP_NEXT)
        self._save_state()
        return True

    async def get_next_track(self):
        """Get next track from controller."""
        await self._emit_status_event("Requesting track...")
        try:
            track: YaTrack = await self._controller.get_next_track()
        except ControllerError as exc:
            await self._emit_error(f'Cannot retrieve track: {exc}.')
            return
        await self._enqueue(track.uri)
        await self._set_current(track)
        await self.play()

    async def skip(self):
        """Skip to track and play next."""
        if not self.repeat_state:
            await self._emit_status_event("Requesting track...")
            try:
                track: YaTrack = await self._controller.get_next_track(played=self.position)
            except ControllerError as exc:
                await self._emit_error(f'Cannot retrieve track: {exc}.')
                return
            await self._enqueue(track.uri)
            await self._set_current(track)
        await self._gs_command(gst.CMD_SKIP_NEXT)

    async def skip_to_playlist_position(self, position: int):
        """Skip current track and play track at given playlist position."""
        if self.mode != const.MODE_PLAYLIST:
            return
        await self._emit_status_event("Requesting track...")
        try:
            track: YaTrack = await self._controller.set_playlist_position(
                position, played=self.position)
        except ControllerError as exc:
            await self._emit_error(f'Cannot skip to given position: {exc}.')
            return
        await self._enqueue(track.uri)
        await self._set_current(track)
        await self._gs_command(gst.CMD_SKIP_NEXT)


    async def like_track(self) -> bool:
        """Add track to favorites"""
        await self._emit_status_event("Setting liked track...")
        try:
            self.current_track.is_liked = await self._controller.like_track()
            return self.current_track.is_liked
        except ControllerError as exc:
            await self._emit_error(f'Cannot like track: {exc}.')
            return False

    async def play(self):
        """Start to play media."""
        await self._gs_command(gst.CMD_PLAY)

    async def pause(self):
        """Pause playback."""
        await self._gs_command(gst.CMD_PAUSE)

    async def stop(self):
        """Stop playback."""
        await self._gs_command(gst.CMD_STOP)

    async def play_again(self):
        """Start playback from the beginning"""
        await self._gs_command(gst.CMD_AGAIN)

    async def repeat(self):
        """Toggle continuous playback of current track"""
        await self._gs_command(gst.CMD_REPEAT)

    async def skip_forward(self):
        """Skip 10% of media"""
        await self._gs_command(gst.CMD_SKIP_FW)

    async def skip_back(self):
        """Back 10% of media"""
        await self._gs_command(gst.CMD_SKIP_BW)

    async def set_volume(self, volume):
        """Set volume."""
        await self._gs_command(gst.CMD_SET_VOLUME, volume=volume)

    @property
    def high_res(self) -> str:
        """Get quality of underlying controller's current source"""
        return self._controller.high_res

    @property
    def repeat_state(self) -> bool:
        """Get repeat state of GstPlayer"""
        return self._dashboard[gst.DASH_REPEAT]

    @property
    def source_name(self) -> str:
        """Get the name of underlying controller's current source"""
        return self._controller.source_name

    @property
    def source_id(self) -> str:
        """Get ID of underlying controller's current source"""
        return self._controller.source_id

    @property
    def state(self) -> str:
        """Get state."""
        return self._dashboard[gst.DASH_STATE]

    @property
    def duration(self):
        """Get duration."""
        return self._dashboard[gst.DASH_DURATION]

    @property
    def position(self) -> int:
        """Get position."""
        return self._dashboard[gst.DASH_POSITION]

    @property
    def uri(self) -> str:
        """Get URI."""
        return self._dashboard[gst.DASH_URI]

    @property
    def volume(self) -> float:
        """Get volume."""
        return self._dashboard[gst.DASH_VOLUME]

    @property
    def error(self):
        """Get error."""
        return self._dashboard[gst.DASH_ERROR]

    @position.setter
    async def position(self, position):
        """Set position."""
        await self._gs_command(gst.CMD_SET_POSITION, position=position)

    def _save_state(self):
        cfg.set_key('volume', self.volume)
        cfg.set_key('mode', self.mode)
        cfg.set_key('high_res', self._controller.high_res)
        if self.mode == const.MODE_RADIO:
            cfg.set_key('radio_id', self._controller.source_id)
        elif self.mode == const.MODE_PLAYLIST:
            cfg.set_key('playlist_id', self._controller.source_id)
        elif self.mode == const.MODE_ARTIST:
            cfg.set_key('artist_id', self._controller.source_id)
        cfg.save()

    async def _set_current(self, track: YaTrack):
        self.current_track = track
        await self._emit_tags_event()

    async def _enqueue(self, uri: str):
        if uri.startswith("/"):
            uri = f'file://{uri}'
        await self._media_queue.coro_put(uri)                                                       # pylint: disable=no-member

    async def _gs_command(self, name, **kwargs):
        """Queue a command to gstreamer process."""
        await self._command_queue.coro_put((name, kwargs))                                          # pylint: disable=no-member

    async def _emit_status_event(self, description: str):
        await self._ui_event_queue.coro_put(dict(type=ev.TYPE_STATUS, status=description))

    async def _emit_tags_event(self):
        await self._ui_event_queue.coro_put(dict(type=ev.TYPE_TAGS))

    async def _emit_state_event(self):
        await self._ui_event_queue.coro_put(dict(type=ev.TYPE_STATE))

    async def _emit_error(self, error: str):
        _LOGGER.error(error)
        self._dashboard[gst.DASH_STATE] = gst.STATE_ERR
        self._dashboard[gst.DASH_ERROR] = error
        await self._emit_state_event()
