"""STUB"""
from tkinter import Event
from tkinter.ttk import  LabelFrame
from typing import Optional, Tuple

from aioprocessing import AioQueue
from yandex_music import RotorSettings

from yamusic import YaPlayer

import utils.constants.events as ev
import utils.constants.player as const
import utils.constants.ui as const

from ...__utils.styling import padding
from ...__utils.controls import SettingsButton

from .artist_pane import ArtistPane
from .station_pane import StationSettingsPane


class SettingsFrame(LabelFrame):
    """
    Container for SettingsFrames.
    When settings are altered, triggers UI SETTINGS event with altered values.
    """
    def __init__(
            self, *args, **kwargs) -> None:
        super().__init__(*args, style='SettingsFrame.TLabelframe', **kwargs)
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.bind('<Key>', self._keypress_event)

        if self.master.player.mode == const.MODE_RADIO:
            self.pane: StationSettingsPane = StationSettingsPane(self)
        if self.master.player.mode == const.MODE_ARTIST:
            self.pane: ArtistPane = ArtistPane(self)
        self.pane.grid(padx=padding / 2, pady=padding / 2, row=0, columnspan=2)

        SettingsButton(
            self, text='Применить', command=self._apply_settings
            ).grid(row=1, column=0, padx=padding, pady=(0, padding), sticky='sew')
        SettingsButton(
            self, text='Отмена', command=self._send_settings_keypress
            ).grid(row=1, column=1, padx=padding, pady=(0, padding), sticky='sew')

        self.grid(row=0, column=1, padx=(0, padding), pady=(0, padding), rowspan=2, sticky='NSEW')
        self.config(text=f' {self._mode_source()}: Настройки ')
        if hasattr(self, '_pane'):
            self.pane.focus_set()

    @property
    def player(self) -> Optional[YaPlayer]:
        """Accessor for player instance"""
        if hasattr(self.master, 'player'):
            return self.master.player
        return None

    @property
    def ui_queue(self) -> Optional[AioQueue]:
        """Accessor for UI event queue instance"""
        if hasattr(self.master, 'ui_queue'):
            return self.master.ui_queue
        return None

    def _mode_source(self) -> str:
        mode: str = const.MODE_ICONS[self.player.mode]
        if self.player.high_res:
            mode = f'{mode} {const.HI_RES_ICON}'
        mode = f'{mode} {self.player.source_name}'
        return mode

    def _apply_settings(self) -> None:
        settings: Tuple[str, RotorSettings] = self.pane.get_updated_settings()
        if settings:
            self.master.ui_queue.put({'type': ev.TYPE_SOURCE_UPD, 'settings': settings})
        self.hide()

    def _keypress_event(self, event: Event) -> None:
        if event.keycode in [const.KEY_ESCAPE, const.KEY_SETTINGS]:
            self._send_settings_keypress()

    def _send_settings_keypress(self):
        self.master.ui_queue.put({'type': ev.TYPE_KEY, 'keycode': const.KEY_SETTINGS})

    def hide(self) -> None:
        """Hide and destroy SettingsFrame and all underlying controls"""
        if hasattr(self, '_pane'):
            self.pane.grid_forget()
            self.pane.destroy()
            self.pane = None
        self.grid_forget()
        self.master.settings_frame = None
        self.destroy()
        self.master.focus_set()
