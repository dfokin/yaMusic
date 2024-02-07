"""UI controls"""

from tkinter.ttk import Frame
from typing import Optional

from aioprocessing import AioQueue
from yamusic import YaPlayer

from .display_frame import DisplayFrame
from .playlist_frame import PlaylistFrame
from .settings_frame import SettingsFrame


class MainFrame(Frame):
    """Container for DisplayFrame, SettingsFrame and PlaylistFrame"""
    def __init__(self, master, **kwargs):
        super().__init__(master, takefocus=True, **kwargs)
        self.grid(row=0, column=0, padx=0, pady=0, sticky='NEW')
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.display_frame: DisplayFrame = DisplayFrame(self)
        self.settings_frame: SettingsFrame = None
        self.playlist_frame: PlaylistFrame = None

    @property
    def player(self) -> Optional[YaPlayer]:
        """Accessor for player instance"""
        if hasattr(self.master, 'player'):
            return self.master.player
        return None

    @property
    def ui_queue(self) -> Optional[AioQueue]:
        """Accessor for UI event queue instance"""
        if hasattr(self.master, 'ui_queue'):
            return self.master.ui_queue
        return None

    def show_playlist(self) -> None:
        """
        Toggle visibility of the PlaylistFrame. 
        """
        if not self.playlist_frame:
            self.playlist_frame = PlaylistFrame(self)
            self.playlist_frame.show()
            self.playlist_frame.fill_playlist()

    def hide_playlist(self) -> None:
        """
        Toggle visibility of the PlaylistFrame. 
        """
        if self.playlist_frame:
            self.playlist_frame.hide()
            del self.playlist_frame
            self.playlist_frame = None

    def toggle_playlist(self) -> None:
        """
        Toggle visibility of the PlaylistFrame. 
        """
        if self.playlist_frame:
            self.hide_playlist()
        else:
            self.show_playlist()

    def update_playlist_position(self) -> None:
        """
        Update playlist position
        """
        if self.playlist_frame:
            self.playlist_frame.update_position()

    def update_playlist_content(self) -> None:
        """
        Update playlist content
        """
        if self.playlist_frame:
            self.playlist_frame.fill_playlist()

    def show_settings(self, **kwargs) -> None:
        """
        Toggle visibility of the SettingsFrame. 
        Content of the SettingsFrame depends on given mode and restrictions.
        """
        if not self.settings_frame:
            self.settings_frame = SettingsFrame(self, **kwargs)

    def toggle_settings(self, **kwargs) -> None:
        """
        Toggle visibility of the SettingsFrame. 
        Content of the SettingsFrame depends on given mode and restrictions.
        """
        if not self.settings_frame:
            self.settings_frame = SettingsFrame(self, **kwargs)
        else:
            self.settings_frame.hide()
