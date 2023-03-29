"""STUB"""
from tkinter.ttk import LabelFrame
from typing import Optional

from aioprocessing import AioQueue

from yamusic.player import YaPlayer

from ...__utils.styling import padding

from .mode_source import ModeSourceState
from .progress_pane import ProgressPane


class DisplayFrame(LabelFrame):
    """Container for ProgressFrame and source selector, also displays current status"""
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            style='DisplayFrame.TLabelframe',
            labelanchor='sw',
            **kwargs)
        self.mode_source: ModeSourceState = ModeSourceState(self)
        self.config(labelwidget=self.mode_source)
        self.progress_frame = ProgressPane(self, padding=padding)
        self.grid(row=0, column=0, padx=padding, pady=padding, sticky='NEWS')

    @property
    def player(self) -> Optional[YaPlayer]:
        """Accessor for player instance"""
        if hasattr(self.master, 'player'):
            return self.master.player
        return None

    @property
    def ui_queue(self) -> Optional[AioQueue]:
        """Accessor for UI event queue"""
        if hasattr(self.master, 'ui_queue'):
            return self.master.ui_queue
        return None
