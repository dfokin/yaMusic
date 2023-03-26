"""
Implements Yandex.Music client's UI
"""
import asyncio
import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict

from aioprocessing import AioQueue

from constants.app import APP_NAME
import constants.events as ev
from yamusic import YaPlayer, YaPlayerError, YaTrack, STATE_ERR, STATE_PAUSED, STATE_PLAYING

from . import _constants as const
from ._display_frame import  DisplayFrame
from ._display_frame._progress_pane import ProgressPane, ProgressLabel, SpinnerLabel, VolumeLabel
from ._main_frame import MainFrame
from ._styling import build_styles, APP_HEIGHT, APP_WIDTH

_LOGGER = logging.getLogger(__name__)


class UI(tk.Tk):
    """
    Application window with various player controls.
    Under the hood runs async _ui_loop to poll UI events and react accordingly.
    When loop exits, shutdown future is set, signalling that UI is gone.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, className=APP_NAME, **kwargs)
        self.shutdown: asyncio.Future = asyncio.Future()
        self._ui_events: AioQueue = AioQueue()
        self._status_queue: asyncio.Queue = asyncio.Queue()
        self._player: YaPlayer = None
        self._progress_task: asyncio.Task = None
        self._status_task: asyncio.Task = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        build_styles(ttk.Style(self))
        self.main: MainFrame = MainFrame(self, style='MainFrame.TFrame')
        # Controls shortcuts
        self._display_frame: DisplayFrame = self.main.display_frame
        self._progress_frame: ProgressPane = self.main.display_frame.progress_frame
        self._spinner: SpinnerLabel = self._progress_frame.spinner
        self._progress: ProgressLabel = self._progress_frame.progress
        self._volume:VolumeLabel = self._progress_frame.volume

        self._spinner.stop()
        self._progress.clean()
        self._set_title()
        self._set_status('Initializing UI...')
        self.bind('<Key>', self._keypress_event)
        self.bind('<Configure>', self._resize_event)
        asyncio.create_task(self._ui_loop())

    async def _ui_loop(self) -> None:
        """
        Main UI loop:
        Create and start YaMusic player, poll and handle UI events
        """
        self._status_task = asyncio.create_task(self._show_status_task())
        try:
            self._player = await YaPlayer(self._ui_events).init()
            await self._player.start()
            self._set_volume_from_player()
        except YaPlayerError as exc:
            msg: str = 'Cannot start player: %s. Shutting down.', str(exc)
            self._to_status(msg)
            _LOGGER.error(msg)
            if self._player:
                await self._player.shutdown()
        else:
            while True:
                message: Dict[int, Dict] = await self._ui_events.coro_get()              #pylint: disable=no-member
                if message['type'] == ev.TYPE_SHUTDOWN:
                    break
                await self._handle_ui_event(message)
        finally:
            await self._shutdown()

    async def _shutdown(self):
        await self._to_status('Shutting down UI...')
        if self._player:
            await self._player.shutdown()
        if self._progress_task:
            self._progress_task.cancel()
        if self._status_task:
            self._status_task.cancel()
        self._ui_events = None
        self._status_queue = None
        _LOGGER.debug('UI Loop exit')
        self.shutdown.set_result(True)

    def _resize_event(self, _) -> None:
        pass
        # self.geometry(f'{APP_WIDTH}x{APP_HEIGHT}')

    def _keypress_event(self, event: tk.Event) -> None:
        self._ui_events.put({"type": ev.TYPE_KEY, "keycode": event.keycode})         #pylint: disable=no-member

    def _toggle_playlist(self) -> None:
        self.main.toggle_playlist()

    def _toggle_settings(self) -> None:
        self.main.toggle_settings(
            self._ui_events, self._player, text=f' {self._player_mode_state()} ')

    def _set_title(self, track: YaTrack=None) -> None:
        title: str
        if not track:
            title = 'Waiting for a track'
        else:
            liked: str = f'{const.LIKE_ICON} ' if track.is_liked else ''
            title = f'{liked}{str(track)}'
        self.title(f'{APP_NAME} {title}')
        self._progress_frame.set_title(title)

    def _player_mode_state(self) -> str:
        """Get current player mode."""
        mode: str = const.MODE_ICONS[self._player.mode]
        if self._player.high_res:
            mode = f'{mode} {const.HI_RES_ICON}'
        mode = f'{mode} {self._player.source_name}'
        return mode

    def _player_mode(self) -> str:
        """Get current player mode."""
        mode: str = const.MODE_ICONS[self._player.mode]
        if self._player.high_res:
            mode = f'{mode} {const.HI_RES_ICON}'
        if self._player.repeat_state:
            mode = f'{mode} {const.REPEAT_ICON}'
        return mode


    def _set_status(self, status: str = '') -> None:
        mode: str = ''
        if self._player:
            mode = self._player_mode()
        self._mode_source.set_mode(mode)
        self._mode_source.set_status(status)

    def _set_volume_from_player(self):
        self._volume.set_volume(self._player.volume * 10)

    async def _vol_up(self) -> None:
        self._volume.set_volume(self._volume.volume + 1)
        await self._player.set_volume(self._volume.volume / 10)

    async def _vol_down(self) -> None:
        self._volume.set_volume(self._volume.volume - 1)
        await self._player.set_volume(self._volume.volume / 10)

    async def _toggle_mute(self) -> None:
        self._volume.toggle_mute()
        await self._player.set_volume(self._volume.volume / 10)

    async def _handle_ui_event(self, event) -> None:
        event_type: int = event["type"]
        _LOGGER.debug('Got event of type %s', ev.TYPE_TO_STR[event_type])
        if event_type == ev.TYPE_STATE:
            await self._handle_player_state()
        elif event_type == ev.TYPE_KEY:
            await self._handle_keypress(event['keycode'])
        elif event_type == ev.TYPE_TAGS:
            self._set_title(track=self._player.current_track)
        elif event_type == ev.TYPE_ATF:
            await self._player.get_next_track()
        elif event_type == ev.TYPE_REPEAT:
            self._mode_source.set_mode(self._player_mode())
        elif event_type == ev.TYPE_STATUS:
            await self._to_status(event.get('status', 'Unknown'))
        elif event_type == ev.TYPE_SOURCE_UPD:
            if event.get('settings', None):
                _LOGGER.debug('New player settings: %s', event['settings'])
                await self._player.apply_source_settings(event['settings'])

    async def _handle_keypress(self, keycode: int) -> None:
        _LOGGER.debug('keycode="%s"', keycode)
        if keycode == const.KEY_LIKE:
            if await self._player.like_track():
                self._set_title(track=self._player.current_track)
        elif keycode == const.KEY_SKIP:
            await self._player.skip()
        elif keycode == const.KEY_FWD:
            await self._player.skip_forward()
        elif keycode == const.KEY_ZERO:
            await self._player.play_again()
        elif keycode == const.KEY_REPEAT:
            await self._player.repeat()
        elif keycode == const.KEY_BACK:
            await self._player.skip_back()
        elif keycode == const.KEY_VOLUP:
            await self._vol_up()
        elif keycode == const.KEY_VOLDOWN:
            await self._vol_down()
        elif keycode == const.KEY_MUTE:
            await self._toggle_mute()
        elif keycode == const.KEY_PLAY:
            state: str = self._player.state
            if state in [STATE_PAUSED]:
                await self._player.play()
            elif state == STATE_PLAYING:
                await self._player.pause()
        elif keycode == const.KEY_PLAYLIST:
            self._toggle_playlist()
        elif keycode == const.KEY_SETTINGS:
            self._toggle_settings()
        elif keycode == const.KEY_EXIT:
            await self._ui_events.coro_put({"type": ev.TYPE_SHUTDOWN})               #pylint: disable=no-member

    async def _handle_player_state(self) -> None:
        state: str = self._player.state
        if state == STATE_ERR:
            await self._to_status(f'Player error: {self._player.error}')
            if self._progress_task:
                self._progress_task.cancel()
        elif state == STATE_PLAYING:
            self._spinner.start()
            if self._progress_task:
                self._progress_task.cancel()
            self._progress_task = asyncio.create_task(self._update_progress())
        elif state == STATE_PAUSED:
            self._spinner.pause()
            if self._progress_task:
                self._progress_task.cancel()

    async def _to_status(self, status: str):
        await self._status_queue.put(status)

    async def _show_status_task(self) -> None:
        try:
            _LOGGER.debug('Status task started.')
            while True:
                self._set_status(await self._status_queue.get())
                await asyncio.sleep(1)
                self._set_status()
        except asyncio.CancelledError:
            _LOGGER.debug('Status task cancelled.')

    async def _update_progress(self) -> None:
        _LOGGER.debug('Progress task started.')
        self._progress.clean()
        try:
            while True:
                duration: int = (self._player.duration or 0)
                position: int = self._player.position
                fac: float = 0
                if duration > 0:
                    fac = position/duration
                self._progress.set_position(fac)
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            _LOGGER.debug('Progress task cancelled.')
            if self._player.state != STATE_PAUSED:
                self._progress.clean()
            return
