"""STUB"""
import asyncio
import logging
from typing import Any, List, Optional

from yandex_music import (
    Album,
    Artist,
    ArtistAlbums,
    ClientAsync,
    SearchResult,
    Track,
    Value,
    )

from utils.config import get_key
from utils.decorators import aiohttp_retry
import utils.constants.events as ev
import utils.constants.ui as ui

from .error import ControllerError
from .source import (
    SourceController,
    RETRY_ARGS,
    RETRY_KWARGS,
    MY_API_TIMEOUT,
)
from .track import YaTrack

_LOGGER = logging.getLogger(__name__)

class ArtistController(SourceController):
    """
    Controls Yandex.Music playlist
    """
    def __init__(self, client: ClientAsync):
        super().__init__(client)
        self._artist_id: str = get_key('artist_id', default='')
        self._artist_name: str = None
        self._candidates: List[Artist] = None
        self._albums: List[Album] = None
        self._playlist: List[Track] = None
        self._position: int = 0

    async def init(self):
        """Initialize Yandex.Music client and populate list of available playlists"""
        await super().init()
        return self

    async def shutdown(self, played:float=0):
        """
        Stop controller
        """
        if self._current_track:
            await self._inform_track_playback_ended(
                self._current_track, self._current_play_id, played=played)
        if self._client:
            del self._client
        _LOGGER.debug('Shut down.')

    async def set_source(self, source_id: str=None,
            source_settings:Any=None, played:float=0) -> YaTrack:
        """
        Opens given playlist, and returns first track
        """
        if not source_settings:
            pass
        if not self._playlist:
            return None
        if self._current_track is not None:
            # Switching to another artist
            asyncio.create_task(
                self._inform_track_playback_ended(
                    self._current_track, self._current_play_id, played)
            )
            self._cleanup_current_track()
        self._position = 0
        _LOGGER.debug('Playing %d album(s) of "%s".', len(self._albums), self._artist_name)

        await self._setup_current_track()

        asyncio.create_task(
            self._inform_track_playback_started(self._current_track, self._current_play_id))

        return self._current_track_int

    async def apply_source_settings(self, settings: Any, force: bool=False) -> bool:
        """
        Apply settings for current playlist and store them to current config
        """
        return True

    async def get_next_track(self, played:float=0) -> YaTrack:
        """
        Retrieve next track from playlist.
        in skipped param pass number seconds played
        """
        asyncio.create_task(
            self._inform_track_playback_ended(
                self._current_track, self._current_play_id, played=played
                )
            )
        self._cleanup_current_track()

        self._position += 1
        if self._position >= len(self._playlist):
            self._position = 0

        await self._setup_current_track()

        asyncio.create_task(
            self._inform_track_playback_started(self._current_track, self._current_play_id))

        return self._current_track_int

    def get_sources_list(self) -> List[Value]:
        """Return available albums"""
        return [Value(name=a.title, value=a.id) for a in self._albums or []]

    def get_short_playlist(self) -> List[YaTrack]:
        """
        Return list of internal representations of tracks in current playlist
        download and user_likes info is not provided
        """
        return [self._to_internal_short(t) for t in self._playlist or []]

    def get_playlist_position(self) -> int:
        """
        Return position of current track in playlist
        """
        return self._position

    async def query_artists(self, query: str, callback: Any) -> None:
        """Queries Yandex Music Artist search API for an Artist's names"""
        self._candidates = await self._query_artists(query)
        return callback([Value(name=f'{a.name} ({", ".join(a.genres)}) {ui.ALBUM_ICON}{a.counts.direct_albums}', value=a.id) for a in self._candidates])

    async def query_albums(self, artist_id: str, callback: Any):
        """Queries Yandex Music Artist search API for an Artist's title"""
        for artist in self._candidates:
            if artist.id == artist_id:
                self._artist_name = artist.name
                self._artist_id = artist.id
                break
        self._albums = sorted((await self._query_albums(artist_id)).albums, key=lambda x: x.year)
        return callback([Value(name=f'({a.year})-{a.title}', value=a.id) for a in self._albums])
    
    async def query_tracks(self, album_ids: List[str], callback: Any):
        """Queries Yandex Music Album search API for an Album's tracks"""
        self._playlist = await self._query_tracks(album_ids)
        return callback([Value(name=f'({a.albums[0].year}) {a.albums[0].title} - {a.title}', value=a.id) for a in self._playlist])
    
    def query(self, type=None, query=None, callback=None) -> None:
        """
        Perform API queries for different content
        """
        if type == ev.TYPE_QUERY_ARTISTS:
            asyncio.create_task(self.query_artists(query, callback))
        elif type == ev.TYPE_QUERY_ALBUMS:
            asyncio.create_task(self.query_albums(query, callback))
        elif type == ev.TYPE_QUERY_TRACKS:
            asyncio.create_task(self.query_tracks(query, callback))

    async def set_playlist_position(self, position: int, played:float=0) -> YaTrack:
        """
        Set index of current playlist
        """
        if position  < 0 or position >= len(self._playlist):
            raise ControllerError(f'Position {position} is out of playlist bounds.')
        asyncio.create_task(
            self._inform_track_playback_ended(
                self._current_track, self._current_play_id, played=played
                )
            )
        self._cleanup_current_track()

        self._position = position

        await self._setup_current_track()

        asyncio.create_task(
            self._inform_track_playback_started(self._current_track, self._current_play_id))

        return self._current_track_int

    ### API wrappers
    # Track controls
    async def _setup_current_track(self) -> None:
        self._current_track = await self._get_track(self._playlist[self._position].track_id)
        self._current_track_int = YaTrack(
            title=self._current_track.title,
            artist=",".join(self._current_track.artists_name()),
            uri=await self._get_track_url(self._current_track, high_res=self.high_res),
            duration=int(self._current_track.duration_ms / 1000),
            )
        self._current_play_id = self._generate_play_id()

    # Helpers
    @property
    def source_name(self) -> str:
        """Returns the name of current playlist"""
        return self._artist_name

    @property
    def source_id(self) -> str:
        """Returns ID of current playlist"""
        return self._artist_id

    ### Low-level API methods
    # Artist controls
    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _query_artists(
        self, title_query: str, timeout: float=MY_API_TIMEOUT) -> List[Artist]:
        result: SearchResult = await self._client.search(
            text=f'"{title_query}"', type_='artist', timeout=timeout)
        if not result or not result.artists:
            return []
        return list(result.artists.results) or []

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _query_albums(
        self, artist_id: str, timeout: float=MY_API_TIMEOUT) -> Optional[ArtistAlbums]:
        """Queries Yandex Music Artist API for Artist's albums"""
        return await self._client.artists_direct_albums(
            artist_id=artist_id, sort_by='year', timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _query_tracks(
        self, album_ids: List[str], timeout: float=MY_API_TIMEOUT) -> List[Track]:
        """Queries Yandex Music Albums API for list of tracks for given albums"""
        _playlist :List[Track] = []
        for album_id in album_ids:
            album_full: Album = await self._client.albums_with_tracks(
                album_id=album_id, timeout=timeout)
            for volume in album_full.volumes:
                for track in volume:
                    _playlist.append(track)
        return _playlist
