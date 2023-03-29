"""STUB"""
import logging
from typing import Dict, Optional, List

from tkinter.ttk import Combobox, Label

from yandex_music import Value
from UI._styling import main_font, padding

_LOGGER = logging.getLogger(__name__)


class SpinnerLabel(Label):
    """
    Spinner widget: one-character label with ability to automatically change its value.
    """
    def __init__(self, master, phases:str='⢿⣻⣽⣾⣷⣯⣟⡿', **kwargs):
        super().__init__(master, **kwargs)
        self.phases: str = phases
        self._running: bool = False
        self._pause: str = '⏸'
        self._stop: str = '⏹'
        self._phase: int = 0
        self._job: str = None
        self.grid(row=0, column=0, pady=padding)

    def _cancel(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def stop(self) -> None:
        """Stop spinning and draw a stop symbol"""
        self._cancel()
        self._running = False
        self._phase = 0
        self['text'] = self._stop

    def pause(self) -> None:
        """Stop spinning and draw a pause symbol"""
        self._cancel()
        self._running = False
        self._phase = 0
        self['text'] = self._pause

    def start(self) -> None:
        """Start spinning"""
        if self._running:
            return
        self._running = True
        self._step()

    def _step(self) -> None:
        if self._running:
            self['text'] = self.phases[self._phase]
            self._phase += 1
            if self._phase > len(self.phases) - 1:
                self._phase = 0
            self._job = self.after(400, self._step)

class ProgressLabel(Label):
    """Label to display progress"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._passed: str = '░'
        self._to_go: str = '🞌'
        self.position: int = 0
        self.grid(row=0, column=1, pady=padding, sticky='NSEW')
        self._update()

    def clean(self) -> None:
        """Set progress to the beginning"""
        self.position = 0
        self._update()

    def set_position(self, ratio: float) -> None:
        """Set progress to given position defined as completed/total ratio"""
        self.position = round(self['width'] * ratio)
        self._update()

    def _update(self) -> None:
        to_go: int = self["width"] - self.position
        self['text'] = f'{self._passed * self.position}{self._to_go * to_go}'

class VolumeLabel(Label):
    """
    Volume widget: one-character label to display current volume label.
    """
    def __init__(self, master, scale: str='🞮 ▁▂▃▄▅▆▇█', **kwargs):
        super().__init__(master, **kwargs)
        self.volume: int = 0
        self._stored: int = None
        self._scale: str = scale
        self._min = 0
        self._max = 10
        self.grid(row=0, column=2, pady=padding)
        self._update()

    def set_volume(self, value: int) -> None:
        """Set current value. Minimum is 0, maximum is 10"""
        self.volume = min(int(value), self._max)
        self.volume = max(self.volume, self._min)
        self._update()

    def toggle_mute(self) -> None:
        """Toggle volume mute status"""
        if self._stored is None:
            self._stored = self.volume
            self.volume = 0
        else:
            self.volume = self._stored
            self._stored = None
        self._update()


    def _update(self) -> None:
        self['text'] = self._scale[self.volume]

class ModeLabel(Label):
    """
    Ordinary label, but with custom style
    """
    def __init__(self, *args, text: str = "", **kwargs):
        super().__init__(*args,  text=f'{text}: ', style='ModeLabel.TLabel', **kwargs)

class ValCombobox(Combobox):
    """
    Combobox for List of yamusic Values: selects an option by name and returns its value.
    Executes passed callback when selection is made.
    """
    def __init__(
            self, master, values_list: List[Value],
            selected_callback=None, preselect: str=None, **kwargs):
        self._dict: Dict[str, str] = {val.name: val.value for val in values_list}
        self._selected_callback = selected_callback
        keys: List[str] = sorted(list(self._dict.keys()))
        super().__init__(
            master, values=keys,
            style='ComboBox.TCombobox', font=main_font, state='readonly', **kwargs)
        self.bind('<<ComboboxSelected>>', self._on_selected)
        if preselect:
            try:
                self._preselect(preselect)
            except ValueError:
                _LOGGER.warning('ValCombobox: Cannot preselect value: %s', preselect)

    def get(self) -> Optional[str]:
        """
        get value from embedded dict by selected key from Combobox
        """
        return self._dict.get(super().get(), None)

    def _preselect(self, value: str) -> None:
        name = [k for k, v in self._dict.items() if v == value][0]
        self.current(list(self['values']).index(name))

    def _on_selected(self, _):
        self.selection_clear()
        if self._selected_callback:
            self._selected_callback(self.get())
