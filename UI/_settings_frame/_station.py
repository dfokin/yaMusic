"""STUB"""
from tkinter import Event
from tkinter.ttk import  Frame, LabelFrame, Label
from typing import List, Optional, Tuple

from yandex_music import Enum, Restrictions, RotorSettings, StationResult, Value

import player.constants as const
from player.yamusic import YaPlayer

from UI._styling import padding, apply_custom_combo_styling
from ._controls import ValCombobox, ColonLabel

class StationSettingsPane(Frame):
    """
    Container for station settings controls.
    Widgets are added dynamically according to given restrictions.
    """
    def __init__(self, player: YaPlayer, *args, **kwargs) -> None:
        super().__init__(*args, style='MainFrame.TFrame', **kwargs)
        apply_custom_combo_styling(self)
        self.s_c: ValCombobox = None
        self.l_c: ValCombobox = None
        self.controls: LabelFrame = None
        self.l_l: ColonLabel = None
        self.d_c: ValCombobox = None
        self.d_l: ColonLabel = None
        self.m_c: ValCombobox = None
        self.m_l: ColonLabel = None
        self._player = player

        stations: List[Value] = []
        s_r: List[StationResult] = player.get_sources_list()
        for result in s_r:
            stations.append(Value(name=result.station.name, value=result.station.id.tag))

        # Station selector
        if stations:
            ColonLabel(
                self, text='Станция', justify='left'
            ).grid(row=0, column=0, padx=(0, padding), sticky='w')
            self.s_c = ValCombobox(self, stations, preselect=player.source_id)
            self.s_c.grid(row=0, column=1, padx=(padding, 0), sticky='e')
            self.s_c.bind("<<ComboboxSelected>>", self._station_update)
            self.s_c.bind('<Key>', self._keypress_event)

        # Separator
        Label(self, style='SettingsLabel.TLabel').grid(row=1, column=0, columnspan=2, sticky='NEWS')
        # Controls frame
        self.controls = LabelFrame(
            self, style='SettingsFrame.TLabelframe', text='Настройки станции')
        self.controls.grid(
            row=2, column=0, columnspan=2, ipadx=padding, ipady=padding, sticky='NEWS')
        self.controls.bind('<Key>', self._keypress_event)

        restr: Restrictions = player.get_source_restrictions()
        if restr:
            station_config: RotorSettings = player.get_source_settings()
            self._build_settings_frame(restr, station_config)

        self.bind('<Key>', self._keypress_event)
        self.grid(padx=padding / 2, pady=padding / 2, row=0, columnspan=2)
        self.update()

    def _station_update(self, _):
        station_id: str = self.s_c.get()
        restr: Restrictions = self._player.get_source_restrictions(station_id=station_id)
        if restr:
            station_config: RotorSettings = self._player.get_source_settings(station_id=station_id)
            self._build_settings_frame(restr, station_config)

    def _keypress_event(self, event: Event) -> None:
        if event.keycode in [const.KEY_ESCAPE]:
            self.master.hide()

    def get_updated_settings(self) -> Optional[Tuple[str, RotorSettings]]:
        """
        Returns dictionary with the new station settings taken from the controls.
        When no controls are altered returns None.
        """
        settings: RotorSettings = RotorSettings(language=None, diversity=None, mood_energy=None)
        if self.l_c:
            settings.language = self.l_c.get()
        if self.d_c:
            settings.diversity = self.d_c.get()
        if self.m_c:
            settings.mood_energy = self.m_c.get()

        if settings.language == settings.diversity == settings.mood_energy == None:
            return None
        return (self.s_c.get(), settings)

    def _build_settings_frame(self, restr: Restrictions, station_config: RotorSettings):
        # Cleanup
        for ctrl in [self.l_c, self.d_c, self.m_c, self.l_l, self.d_l, self.m_l]:
            if ctrl is not None:
                ctrl.grid_forget()
                ctrl.destroy()
        self.l_c = self.d_c = self.m_c = self.l_l = self.d_l = self.m_l = None

        # Rebuild
        if restr.language:
            lang: Enum = restr.language
            self.l_l = ColonLabel(self.controls, text=lang.name, justify='left')
            self.l_c = ValCombobox(
                self.controls, lang.possible_values, preselect=station_config.language)
            self.l_c.bind('<Key>', self._keypress_event)
            self.l_l.grid(row=0, column=0, padx=(0, padding), sticky='w')
            self.l_c.grid(row=0, column=1, padx=(padding, 0), sticky='e')
        if restr.diversity:
            div: Enum = restr.diversity
            self.d_l = ColonLabel(self.controls, text=div.name, justify='left')
            self.d_c = ValCombobox(
                self.controls, div.possible_values, preselect=station_config.diversity)
            self.d_c.bind('<Key>', self._keypress_event)
            self.d_l.grid(row=1, column=0, padx=(0, padding), sticky='w')
            self.d_c.grid(row=1, column=1, padx=(padding, 0), sticky='e')
        if restr.mood_energy:
            mood: Enum = restr.mood_energy
            self.m_l = ColonLabel(self.controls, text=mood.name,justify='left')
            self.m_c = ValCombobox(
                self.controls, mood.possible_values, preselect=station_config.mood_energy)
            self.m_c.bind('<Key>', self._keypress_event)
            self.m_l.grid(row=2, column=0, padx=(0, padding), sticky='w')
            self.m_c.grid(row=2, column=1, padx=(padding, 0), sticky='e')
