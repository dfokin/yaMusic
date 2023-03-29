"""STUB"""
from tkinter.ttk import LabelFrame


from ...__utils.controls import SpinnerLabel, ProgressLabel, VolumeLabel
from ...__utils.styling import progress_chars, padding

class ProgressPane(LabelFrame):
    """Container for Spinner, Progress and Volume widgets, also displays current track nam"""
    def __init__(self, master, scroll_delay_ms :int=400, **kwargs):
        super().__init__(master, style='ProgressFrame.TLabelframe', **kwargs)
        self._window: int  = progress_chars - 5
        self._title: str = None
        self._window_pos: int = 0
        self._job: str = None
        self._scroll_direction: int = 1
        self._delay_ms: int = scroll_delay_ms
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid(row=0, column=0, padx=padding, pady=padding, sticky='NSEW')

        self.spinner = SpinnerLabel(self, style='SpinnerLabel.TLabel', text='⣽')
        self.progress = ProgressLabel(self, style='ProgressLabel.TLabel', width=progress_chars)
        self.volume = VolumeLabel(self, style='VolumeLabel.TLabel', text='🔊')

    def set_title(self, title: str) -> None:
        """Set current track name"""
        self._cancel()
        self._title = None
        if len(title) > self._window:
            self._title = f' {title} '
            self._step()
        else:
            self['text'] = f' {title} '

    def _step(self) -> None:
        delay: int = self._delay_ms
        end: int = self._window_pos + self._window
        self['text'] = self._title[self._window_pos: end]
        if self._scroll_direction > 0:
            if end == len(self._title):
                delay = self._delay_ms * 3
                self._scroll_direction = -1
        elif self._scroll_direction < 0:
            if self._window_pos == 0:
                delay = self._delay_ms * 3
                self._scroll_direction = 1
        self._window_pos += self._scroll_direction
        self._job = self.after(delay, self._step)

    def _cancel(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
            self._window_pos = 0
