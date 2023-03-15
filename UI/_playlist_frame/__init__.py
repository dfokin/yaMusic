"""STUB"""
from tkinter.ttk import LabelFrame

from UI._styling import padding, PLAYLIST_HEIGHT


class PlaylistFrame(LabelFrame):
    """Displays list of tracks"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args, style='PlaylistFrame.TLabelframe', 
            text='Playlist', height=PLAYLIST_HEIGHT, **kwargs)

    def show(self) -> None:
        """Show the frame"""
        self.grid(row=1, column=0, padx=padding, pady=padding, sticky='NSEW')

    def hide(self):
        """Hide the frame"""
        self.grid_forget()
        self.destroy()
