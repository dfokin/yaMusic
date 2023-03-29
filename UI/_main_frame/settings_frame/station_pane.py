"""STUB"""
from tkinter import Event
from tkinter.ttk import  Frame
from typing import Optional, Tuple

from yandex_music import Enum, Restrictions, RotorSettings

from utils.constants.events import TYPE_KEY
from utils.constants.ui import KEY_ESCAPE, KEY_SETTINGS

from ...__utils.controls import ColonLabel, ValCombobox
from ...__utils.styling import padding, apply_custom_combo_styling

class StationSettingsPane(Frame):
    """
    Container for station settings controls.
    Widgets are added dynamically according to given restrictions.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, style='MainFrame.TFrame', **kwargs)
        apply_custom_combo_styling(self)
        self.cframe: Frame = None
        self.l_c: ValCombobox = None
        self.l_l: ColonLabel = None
        self.d_c: ValCombobox = None
        self.d_l: ColonLabel = None
        self.m_c: ValCombobox = None
        self.m_l: ColonLabel = None

        self.cframe = Frame(self, style='CFrame.TFrame')
        self.cframe.grid(row=2, column=0, columnspan=2, ipady=padding, sticky='NEWS')
        self.cframe.bind('<Key>', self._keypress_event)

        restr: Restrictions = self.master.player.get_source_restrictions()
        if restr:
            station_config: RotorSettings = self.master.player.get_source_settings()
            self._build_settings_frame(restr, station_config)

        self.bind('<Key>', self._keypress_event)
        self.grid(padx=padding / 2, pady=padding / 2, row=0, columnspan=2)

    def _keypress_event(self, event: Event) -> None:
        if event.keycode in [KEY_ESCAPE, KEY_SETTINGS]:
            self.master.ui_queue.put({'type': TYPE_KEY, 'keycode': KEY_SETTINGS})

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
        return (self.master.player.source_id, settings)

    def _build_settings_frame(self, restrictions: Restrictions, config: RotorSettings):
        # Cleanup
        for ctrl in [self.l_c, self.d_c, self.m_c, self.l_l, self.d_l, self.m_l]:
            if ctrl is not None:
                ctrl.grid_forget()
                ctrl.destroy()
        self.l_c = self.d_c = self.m_c = self.l_l = self.d_l = self.m_l = None

        # Rebuild
        if restrictions.language:
            lang: Enum = restrictions.language
            self.l_l = ColonLabel(self.cframe, text=lang.name, justify='left')
            self.l_c = ValCombobox(self.cframe, lang.possible_values, preselect=config.language)
            self.l_c.bind('<Key>', self._keypress_event)
            self.l_l.grid(row=0, column=0, padx=(padding, 0), pady=2, sticky='w')
            self.l_c.grid(row=0, column=1, padx=(0, padding), pady=2, sticky='e')
        if restrictions.diversity:
            div: Enum = restrictions.diversity
            self.d_l = ColonLabel(self.cframe, text=div.name, justify='left')
            self.d_c = ValCombobox(self.cframe, div.possible_values, preselect=config.diversity)
            self.d_c.bind('<Key>', self._keypress_event)
            self.d_l.grid(row=1, column=0, padx=(padding, 0), pady=2, sticky='w')
            self.d_c.grid(row=1, column=1, padx=(0, padding), pady=2, sticky='e')
        if restrictions.mood_energy:
            mood: Enum = restrictions.mood_energy
            self.m_l = ColonLabel(self.cframe, text=mood.name, justify='left')
            self.m_c = ValCombobox(self.cframe, mood.possible_values, preselect=config.mood_energy)
            self.m_c.bind('<Key>', self._keypress_event)
            self.m_l.grid(row=2, column=0, padx=(padding, 0), pady=2, sticky='w')
            self.m_c.grid(row=2, column=1, padx=(0, padding), pady=2, sticky='e')
