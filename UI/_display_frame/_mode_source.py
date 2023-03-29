"""STUB"""
from tkinter.ttk import Frame
from typing import Any, List, Tuple

from yandex_music import Value

import constants.events as ev

from UI._styling import padding, apply_custom_combo_styling
from UI._settings_frame._controls import ColonLabel
from ._controls import ModeLabel, ValCombobox


class ModeSourceState(Frame):
    """Container for ColonLabels for mode and status display and ValCombobox for source select"""
    def __init__(self, master, **kwargs):
        super().__init__(master, style='ModeSource.TFrame', **kwargs)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        apply_custom_combo_styling(self)
        self._mode = ModeLabel(self)
        self._mode.grid(row=0, column=0, padx=padding, pady=0, sticky='EW')
        self._status = ColonLabel(self)
        self._status.grid(row=0, column=2, padx=0, pady=0, sticky='EW')
        self._sources: ValCombobox = None
        self.update_sources()

    def update_sources(self):
        """Update Combobox vith sources taken from player"""
        if not self.master.player:
            return
        if self._sources:
            self._sources.grid_forget()
            self._sources = None
        _sources: List[Value] = self.master.player.get_sources_list()
        if _sources:
            if self._sources:
                self._sources.grid_forget()
                self._sources = None
            preselect: str = self.master.player.source_id
            self._sources = ValCombobox(self, _sources, self._on_select, preselect=preselect)
            self._sources.grid(row=0, column=1, padx=(0, padding), pady=0, sticky='EW')

    def _on_select(self, value: str):
        if self.master.ui_queue:
            settings: Tuple[str, Any] = (value, None)
            self.master.ui_queue.put({'type': ev.TYPE_SOURCE_UPD, 'settings': settings})
        self.tk_focusNext()

    def set_mode(self, mode: str) -> None:
        """Set current player mode"""
        self._mode['text'] = f'{mode.strip()}'

    def set_status(self, status: str) -> None:
        """Set status text"""
        self._status['text'] = f'{status.strip()}'
