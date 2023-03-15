"""STUB"""
import logging
from tkinter.ttk import Button, Combobox
from typing import Dict, Optional, List

from yandex_music import Enum

from UI._styling import main_font

_LOGGER = logging.getLogger(__name__)


class EnumCombobox(Combobox):
    """
    Combobox for yamusic Enum: selects option by name and returns its value
    """
    def __init__(self, master, enum: Enum, preselect: str=None, **kwargs):
        self.dict: Dict[str, str] = {val.name: val.value for val in enum.possible_values}
        keys: List[str] = list(self.dict.keys())
        vals: List[str] = list(self.dict.values())
        super().__init__(
            master, values=keys,
            style='ComboBox.TCombobox', font=main_font, **kwargs)
        if preselect:
            try:
                self._preselect(vals.index(preselect))
            except ValueError:
                _LOGGER.warning('%s: No such item: %s', enum.name, preselect)

    def get(self) -> Optional[str]:
        """
        get value from embedded dict by selected key from Combobox
        """
        return self.dict.get(super().get(), None)

    def _preselect(self, index: int):
        """
        preselect given value
        """
        self.current(index)

class SettingsButton(Button):
    """
    Ordinary button, but may be pressed by hitting Enter key
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args,  style='SettingsButton.TButton', **kwargs)
        self.bind('<Return>', lambda _: self.invoke())
