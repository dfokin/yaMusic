"""STUB"""
from tkinter.ttk import  LabelFrame
from typing import Tuple

from aioprocessing import AioQueue

import player.constants as const
from player.yamusic import YaPlayer, RotorSettings

from UI._styling import padding
from ._controls import SettingsButton
from ._station import StationSettingsPane


class SettingsFrame(LabelFrame):
    """
    Container for SettingsFrames.
    When settings are altered, triggers UI SETTINGS event with altered values.
    """
    def __init__(
            self, queue: AioQueue, player: YaPlayer, *args, **kwargs) -> None:
        super().__init__(
            *args, style='SettingsFrame.TLabelframe',
            text=f' {player.mode_state} ', **kwargs)
        self._queue: AioQueue = queue
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        if player.mode == const.MODE_RADIO:
            self._pane: StationSettingsPane = StationSettingsPane(player, self)

        SettingsButton(
            self, text='Применить', command=self._apply_settings
            ).grid(row=1, column=0, sticky='sew')
        SettingsButton(
            self, text='Отмена', command=self.hide
            ).grid(row=1, column=1, sticky='sew')

        self.grid(row=0, column=1, padx=padding, pady=padding, rowspan=2, sticky='NSEW')
        self._pane.focus_set()

    def _apply_settings(self) -> None:
        settings: Tuple[str, RotorSettings] = self._pane.get_updated_settings()
        if settings:
            self._queue.put({'type': const.TYPE_SOURCE_UPD, 'settings': settings})
        self.hide()

    def hide(self) -> None:
        """Hide and destroy SettingsFrame and all underlying controls"""
        self._pane.grid_forget()
        self._pane.destroy()
        self._pane = None
        self.grid_forget()
        self.master.settings_frame = None
        self.destroy()
        self.master.focus_set()
