"""STUB"""
import logging
from tkinter.ttk import Button, Combobox, Label
from typing import Dict, Optional, List

from yandex_music import Value

from UI._styling import main_font

_LOGGER = logging.getLogger(__name__)


class ValCombobox(Combobox):
    """
    Combobox for List of yamusic Values: selects an option by name and returns its value
    """
    def __init__(self, master, values_list: List[Value], preselect: str=None, **kwargs):
        self.dict: Dict[str, str] = {val.name: val.value for val in values_list}
        keys: List[str] = sorted(list(self.dict.keys()))
        super().__init__(
            master, values=keys,
            style='ComboBox.TCombobox', font=main_font, **kwargs)
        if preselect:
            try:
                self._preselect(preselect)
            except ValueError:
                _LOGGER.warning('ValCombobox: Cannot preselect value: %s', preselect)

    def get(self) -> Optional[str]:
        """
        get value from embedded dict by selected key from Combobox
        """
        return self.dict.get(super().get(), None)

    def _preselect(self, value: str) -> None:
        name = [k for k, v in self.dict.items() if v == value][0]
        self.current(list(self['values']).index(name))

class SettingsButton(Button):
    """
    Ordinary button, but may be pressed by hitting Enter key
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args,  style='SettingsButton.TButton', **kwargs)
        self.bind('<Return>', lambda _: self.invoke())

class ColonLabel(Label):
    """
    Ordinary label, but with custom style and colon with space is added after the text
    """
    def __init__(self, *args, text: str = "", **kwargs):
        super().__init__(*args,  text=f'{text}: ', style='SettingsLabel.TLabel', **kwargs)
