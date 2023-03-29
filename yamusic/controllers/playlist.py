"""STUB"""
import asyncio
import logging
from typing import List

from yandex_music import (
    ClientAsync,
    TracksList,
    Playlist,
    RotorSettings,
    Track,
    Value,
    )

from utils.config import get_key
from utils.decorators import aiohttp_retry

from .error import ControllerError
from .source import (
    SourceController,
    RETRY_ARGS,
    RETRY_KWARGS,
    MY_API_TIMEOUT,
)
from .track import YaTrack

_LOGGER = logging.getLogger(__name__)

DEFAULT_PLAYLIST_ID : str = 'my_likes'
DEFAULT_PLAYLIST_NAME : str = 'Моя коллекция'

class PlaylistController(SourceController):
    """
    Controls Yandex.Music playlist
    """
    def __init__(self, client: ClientAsync):
        super().__init__(client)
        self._playlist_id: str = get_key('playlist_id', default=DEFAULT_PLAYLIST_ID)
        self._playlists: List[Value] = []
        self._playlist: List[Track] = None
        self._playlist_name: str = None
        self._position: int = 0

    async def init(self):
        """Initialize Yandex.Music client and populate list of available playlists"""
        await super().init()
        self._playlists = [Value(name=DEFAULT_PLAYLIST_NAME, value=DEFAULT_PLAYLIST_ID)]
        self._playlists.extend(await self._get_user_playlists())
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
            source_settings:RotorSettings=None, played:float=0) -> YaTrack:
        """
        Opens given playlist, and returns first track
        """
        if not source_settings:
            pass
        if self._playlist is not None:
            # Switching to another playlist
            asyncio.create_task(
                self._inform_track_playback_ended(
                    self._current_track, self._current_play_id, played)
            )
            self._cleanup_current_track()
            self._position = 0
        if not await self._fill_playlist(source_id or self._playlist_id):
            raise ControllerError(f'No such Id: {self._playlist_id} in user\'s playlists.')
        _LOGGER.debug('Opened playlist "%s".', self._playlist_name)

        await self._setup_current_track()

        asyncio.create_task(
            self._inform_track_playback_started(self._current_track, self._current_play_id))

        return self._current_track_int

    async def apply_source_settings(self, settings: RotorSettings, force: bool=False) -> bool:
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
        """Return available playlists"""
        return self._playlists

    def get_short_playlist(self) -> List[YaTrack]:
        """
        Return list of internal representations of tracks in current playlist
        download and user_likes info is not provided
        """
        return [self._to_internal_short(t) for t in self._playlist]

    def get_playlist_position(self) -> int:
        """
        Return position of current track in playlist
        """
        return self._position

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
    # Playlist controls
    async def _get_user_playlists(self) -> List[Value]:
        try:
            return [
                Value(name=pl.title, value=pl.kind) for pl in await self._get_playlists()
                ]
        except ControllerError as err:
            _LOGGER.debug('Cannot retrieve user playlists: %s.', err)

    async def _fill_playlist(self, playlist_id: str) -> bool:
        for pl_short in self._playlists:
            if pl_short.value == playlist_id:
                try:
                    if playlist_id == DEFAULT_PLAYLIST_ID:
                        self._playlist = await self._get_liked_tracks()
                    else:
                        self._playlist = await self._get_playlist_tracks(pl_short.value)
                except ControllerError as err:
                    _LOGGER.error('Cannot retrieve playlist data: %s', err)
                    raise ControllerError(f'Cannot retrieve playlist data: {err}')                  # pylint: disable=raise-missing-from
                self._playlist_name = pl_short.name
                self._playlist_id = pl_short.value
                return True
        return False

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
        return self._playlist_name

    @property
    def source_id(self) -> str:
        """Returns ID of current playlist"""
        return self._playlist_id

    ### Low-level API methods
    # Playlist controls
    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_playlists(self, timeout: float=MY_API_TIMEOUT) -> List[Playlist]:
        return await self._client.users_playlists_list(timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_playlist_tracks(
        self, playlist_id: str, timeout: float=MY_API_TIMEOUT) -> List[Track]:
        pl_full: Playlist = await self._client.users_playlists(kind=playlist_id, timeout=timeout)
        tracks: TracksList = TracksList(
                pl_full.owner.uid, pl_full.revision, pl_full.tracks, self._client
            )
        return await tracks.fetch_tracks_async(timeout=timeout)

    @aiohttp_retry(*RETRY_ARGS, **RETRY_KWARGS)
    async def _get_liked_tracks(self, timeout: float=MY_API_TIMEOUT) -> List[Track]:
        liked_tracks_short: TracksList = await self._client.users_likes_tracks(timeout=timeout)
        return await liked_tracks_short.fetch_tracks_async(timeout=timeout)
