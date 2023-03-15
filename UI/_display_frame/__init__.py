"""STUB"""
from tkinter.ttk import LabelFrame

from UI._styling import padding
from._progress_pane import ProgressPane


class DisplayFrame(LabelFrame):
    """Container for ProgressFrame, also displays current status"""
    def __init__(self, master, **kwargs):
        super().__init__(master, style='DisplayFrame.TLabelframe', labelanchor='sw', **kwargs)
        self.grid(row=0, column=0, padx=padding, pady=padding, sticky='NSEW')
        self.progress_frame = ProgressPane(self, padding=padding)

    def set_status(self, status: str) -> None:
        """Set widget's label text"""
        self['text'] = f' {status.strip()} '
