"""UI controls"""

from tkinter.ttk import Frame

from aioprocessing import AioQueue
from yamusic import YaPlayer

from ._display_frame import DisplayFrame
from ._playlist_frame import PlaylistFrame
from ._settings_frame import SettingsFrame


class MainFrame(Frame):
    """Container for DisplayFrame, SettingsFrame and PlaylistFrame"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid(row=0, column=0, padx=0, pady=0, sticky='NSEW')
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.display_frame: DisplayFrame = DisplayFrame(self)
        self.settings_frame: SettingsFrame = None
        self.playlist_frame: PlaylistFrame = None

    def toggle_playlist(self) -> None:
        """
        Toggle visibility of the PlaylistFrame. 
        """
        if not self.playlist_frame:
            self.playlist_frame = PlaylistFrame(self)
            self.playlist_frame.show()
        else:
            self.playlist_frame.hide()
            self.playlist_frame = None

    def toggle_settings(self, queue: AioQueue, player: YaPlayer, **kwargs) -> None:
        """
        Toggle visibility of the SettingsFrame. 
        Content of the SettingsFrame depends on given mode and restrictions.
        """
        if not self.settings_frame:
            self.settings_frame = SettingsFrame(queue, player, self, **kwargs)
        else:
            self.settings_frame.hide()
