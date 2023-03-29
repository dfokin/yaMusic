"""STUB"""
from tkinter.ttk import Frame, Scrollbar
from tkinter import ACTIVE, Listbox, Variable, VERTICAL
from typing import List

import utils.constants.events as ev
from yamusic import YaTrack

from ...__utils.styling import (
    bgcolor,
    focuscolor,
    measure_main_font,
    padding,
    ListBoxStyle,
    PLAYLIST_HEIGHT
)

class PlaylistFrame(Frame):
    """Displays list of tracks in player"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            *args, style='PlaylistFrame.TLabelframe', height=PLAYLIST_HEIGHT, **kwargs)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        self._list_var = Variable()
        self.list: Listbox = Listbox(self,listvariable=self._list_var, **ListBoxStyle)
        scrollbar: Scrollbar = Scrollbar(self, orient=VERTICAL, command=self.list.yview)
        self.list['yscrollcommand'] = scrollbar.set
        scrollbar.grid(row=0, column=1, padx=0, pady=0, sticky='NSEW')
        self.list.grid(row=0, column=0, padx=0, pady=0, sticky='NSEW')

        self.list.bind('<FocusIn>',  self._on_enter)
        self.list.bind('<FocusOut>', self._on_leave)
        self.list.bind('<Escape>',   self._on_leave)
        self.list.bind('<space>',    self._on_select)
        self.list.bind('<Return>',   self._on_select)
        self.list.bind('<Double-1>', self._on_select)
        self.list.bind('<Motion>',   self._on_mouseover)

    def _on_select(self, _):
        self.list.select_clear(self.list.curselection()[0])
        self.list.select_set(self.list.index(ACTIVE))
        self.master.ui_queue.put(
            {'type': ev.TYPE_SKIP_POS, 'position': self.list.curselection()[0]})

    def _on_enter(self, _):
        self.list.config(selectforeground=focuscolor)
        self.list.focus_force()

    def _on_leave(self, _):
        self.list.config(selectforeground=bgcolor)
        self.update_position()
        self.master.focus_force()

    def _on_mouseover(self, event):
        index = self.list.index(f'@{event.x},{event.y}')
        self.list.activate(index)

    def show(self) -> None:
        """Show the frame"""
        self.grid(row=1, column=0, padx=padding, pady=padding, sticky='NSEW')

    def hide(self):
        """Hide the frame"""
        self.grid_forget()
        self.destroy()

    def update_position(self):
        """Set cursor to current playlist position"""
        position: int = self.master.player.get_playlist_position()
        if self.list.curselection():
            self.list.select_clear(self.list.curselection()[0])
        self.list.select_set(position)
        self.list.activate(position)
        self.list.see(position)

    def fill_playlist(self):
        """Set playlist content"""
        self.update_idletasks()
        tracks: List[YaTrack] = self.master.player.get_short_playlist()
        list_char_width = self.list.winfo_width() // measure_main_font()
        self._list_var.set([t.fixed_width(list_char_width) for t in tracks])
        self.update_position()
