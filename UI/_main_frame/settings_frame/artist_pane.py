"""STUB"""
from tkinter import MULTIPLE, SINGLE, END
from tkinter.ttk import  Entry, Frame
from typing import Dict, List, Tuple

from yandex_music import Value

import utils.config as cfg
from utils.constants.events import TYPE_QUERY_ARTISTS, TYPE_QUERY_ALBUMS, TYPE_QUERY_TRACKS, TYPE_KEY
from utils.constants.ui import ARTIST_ICON, ALBUM_ICON, TRACK_ICON, KEY_SETTINGS

from ...__utils.controls import SettingsButton, ValListbox
from ...__utils.styling import padding, main_font, ListBoxStyle_S

MODE_CANDIDATES : int = 0
MODE_ALBUMS     : int = 1
MODE_TRACKS     : int = 2

MOD_ICONS       : Dict[int,str] = {
    MODE_CANDIDATES: ARTIST_ICON,
    MODE_ALBUMS: ALBUM_ICON,
    MODE_TRACKS: TRACK_ICON,
}

class ArtistPane(Frame):
    """STUB"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, style='CFrame.TFrame', **kwargs)
        self.result_mode: str = ''
        self.artist_id: str = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.search_input: Entry = Entry(
            self, style='Search.TEntry', font=main_font, width=40)
        self.search_input.grid(row=0, column=0, padx=(0, padding / 2), pady=0, sticky='nsew')
        self.search_input.focus_force()
        self.search_input.bind('<Return>', lambda _ : self._query_candidates())
        self.search_input.bind('<Escape>', lambda _ : self._close())

        SettingsButton(
            self, text='', command=self._query_candidates, width=0
            ).grid(row=0, column=1, padx=0, pady=0, sticky='nsew')

        self.results_list: ValListbox = ValListbox(self, **ListBoxStyle_S)
        # self.scrollbar = ttk.Scrollbar(
        #     self, orient=tk.VERTICAL, style='Vertical.TScrollbar', command=self.results_list.yview)
        # self.results_list['yscrollcommand'] = self.scrollbar.set
        # self.scrollbar.grid(row=1, column=1, padx=0, pady=0, sticky='NEWS')
        self.results_list.bind('<Escape>', lambda _ : self._close())
        self.results_list.grid(row=1, column=0, columnspan=2, padx=0, pady=(padding / 2, 0), sticky='NEWS')

    def _close(self):
        self.master.ui_queue.put({'type': TYPE_KEY, 'keycode': KEY_SETTINGS})

    def _query_candidates(self):
        self.result_mode = MODE_CANDIDATES
        self.master.ui_queue.put({
            'type': TYPE_QUERY_ARTISTS,
            'query': self.search_input.get()})

    def _query_albums(self):
        self.result_mode = MODE_ALBUMS
        self.artist_id = self.results_list.selection_get()
        self.master.ui_queue.put({
            'type': TYPE_QUERY_ALBUMS,
            'query': self.results_list.selection_get()})
    
    def _query_tracks(self):
        self.result_mode = MODE_TRACKS
        self.master.ui_queue.put({
            'type': TYPE_QUERY_TRACKS,
            'query': self.results_list.selection_get()})

    def fill_results_list(self, values: List[Value]):
        self.results_list.set_values(values, MOD_ICONS[self.result_mode])
        self.results_list.activate(0)
        self.results_list.focus_force()
        if self.result_mode == MODE_CANDIDATES:
            self.results_list.select_set(0)
            self.results_list.bind('<Return>', lambda _ : self._query_albums())
        elif self.result_mode == MODE_ALBUMS:
            self.search_input.delete(0, END)
            self.results_list['selectmode'] = MULTIPLE
            self.results_list.bind('<Return>', lambda _ : self._query_tracks())
        elif self.result_mode == MODE_TRACKS:
            self.results_list['selectmode'] = SINGLE
            self.result_mode = MODE_CANDIDATES

    def get_updated_settings(self) -> Tuple[str, None]:
        if self.result_mode == MODE_ALBUMS:
            self._query_tracks()
        return (self.artist_id, None)
