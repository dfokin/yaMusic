"""STUB"""
from tkinter import Event
from tkinter.ttk import  Frame, Label
from typing import Dict, Optional, Tuple

from yandex_music import Enum, Restrictions

import player.constants as const
import player.config as cfg
from player.yamusic import YaPlayer

from UI._styling import padding, apply_custom_combo_styling
from ._controls import EnumCombobox

class StationSettingsPane(Frame):
    """
    Container for station settings controls.
    Widgets are added dynamically according to given restrictions.
    """
    def __init__(self, player: YaPlayer, *args, **kwargs) -> None:
        super().__init__(*args, style='MainFrame.TFrame', **kwargs)
        apply_custom_combo_styling(self)
        self.l_c: EnumCombobox = None
        self.d_c: EnumCombobox = None
        self.m_c: EnumCombobox = None
        self._station_id: str = player.source_id

        restr: Restrictions = player.get_restrictions()

        station_config: Dict = cfg.get_station_settings(self._station_id, default={})
        if restr.language:
            lang: Enum = restr.language
            Label(
                self, text=lang.name, style='SettingsLabel.TLabel', justify='left'
                ).grid(row=0, column=0, padx=(0, padding), sticky='w')
            self.l_c = EnumCombobox(self, lang, preselect=station_config.get('language'))
            self.l_c.grid(row=0, column=1, padx=(padding, 0), sticky='e')
        if restr.diversity:
            div: Enum = restr.diversity
            Label(
                self, text=div.name, style='SettingsLabel.TLabel', justify='left'
                ).grid(row=1, column=0, padx=(0, padding), sticky='w')
            self.d_c = EnumCombobox(self, div, preselect=station_config.get('diversity'))
            self.d_c.grid(row=1, column=1, padx=(padding, 0), sticky='e')
        if restr.mood_energy:
            mood: Enum = restr.mood_energy
            Label(
                self, text=mood.name, style='SettingsLabel.TLabel', justify='left'
                ).grid(row=2, column=0, padx=(0, padding), sticky='w')
            self.m_c = EnumCombobox(self, mood, preselect=station_config.get('mood_energy'))
            self.m_c.grid(row=2, column=1, padx=(padding, 0), sticky='e')

        self.bind('<Key>', self._keypress_event)
        self.grid(padx=padding / 2, pady=padding / 2, row=0, columnspan=2)

    def _keypress_event(self, event: Event) -> None:
        if event.keycode in [const.KEY_SETTINGS, const.KEY_ESCAPE]:
            self.master.hide()

    def get_updated_settings(self) -> Optional[Tuple[str, Dict[str, str]]]:
        """
        Returns dictionary with the new station settings taken from the controls.
        When no controls are altered returns None.
        """
        settings: Dict[str, str] = {}
        if self.l_c:
            settings['language'] = self.l_c.get()
        if self.d_c:
            settings['diversity'] = self.d_c.get()
        if self.m_c:
            settings['mood_energy'] = self.m_c.get()

        if settings.get('language', None) == \
            settings.get('diversity', None) == \
            settings.get('mood_energy', None) == None:
            return None
        # Store settings to config
        cfg.set_station_settings(self._station_id, settings)
        return settings
