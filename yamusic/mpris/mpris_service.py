""" MPRIS service implementation """
import logging

from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess
from dbus_next import Variant
from strenum import StrEnum

from utils.constants.app import APP_NAME
from yamusic.controllers import YaTrack

_LOGGER = logging.getLogger(__name__)

class PlayState(StrEnum):
    PAUSED:  str = 'Paused'
    PLAYING: str = 'Playing'
    STOPPED: str = 'Stopped'

class MprisRoot(ServiceInterface):
    def __init__(self, name):
        super().__init__('org.mpris.MediaPlayer2')
        self._name = name

    @dbus_property(name='DesktopEntry', access=PropertyAccess.READ)
    def desktop_entry(self) -> 's':
        return self._name

class MprisPlayer(ServiceInterface):
    def __init__(self, name):
        super().__init__('org.mpris.MediaPlayer2.Player')
        self._name: str = name
        self._playback_status: str = 'Stopped'
        self._metadata = {
            'mpris:trackid': Variant('o', '/track/1'),
            'mpris:length': Variant('x', 0),
            'xesam:title': Variant('s', 'Not set'),
            'xesam:album': Variant('s', 'Not set'),
            'xesam:artist': Variant('as', ['Not set'])
        }

        # ... other properties

    @method()
    def Play(self):
        # Your play logic here
        self.emit_properties_changed({'PlaybackStatus': PlayState.PLAYING})

    @method()
    def Pause(self):
        # Your pause logic here
        self.emit_properties_changed({'PlaybackStatus': PlayState.PAUSED})

    @method()
    def Stop(self):
        # Your pause logic here
        self.emit_properties_changed({'PlaybackStatus': PlayState.STOPPED})

    @dbus_property(name='DesktopEntry', access=PropertyAccess.READ)
    def desktop_entry(self) -> 's':
        return self._name

    @dbus_property(name='PlaybackStatus', access=PropertyAccess.READ)
    def playback_status(self) -> 's':
        return self._playback_status

    @dbus_property(name='Metadata', access=PropertyAccess.READ)
    def metadata(self) -> 'a{sv}':
        return self._metadata

    def update_state(self, state: str) -> None:
        self._playback_status = state
        self.emit_properties_changed(
            changed_properties={
                'PlaybackStatus': self._playback_status,
            },
            invalidated_properties=[]
        )

    def update_metadata(self, track: YaTrack) -> None:
        if track is None:
            self._metadata = {
                    'mpris:trackid': Variant('o', '/track/none'),
                    'mpris:length': Variant('x', 0),
                    'xesam:title': Variant('s', 'Not set'),
                    'xesam:album': Variant('s', 'Not set'),
                    'xesam:artist': Variant('as', ['Not set'])
                }
        else:
            self._metadata = {
                    'mpris:trackid': Variant('o', '/track/none'),
                    'mpris:length': Variant('x', track.duration * 1000000),
                    'xesam:title': Variant('s', track.title),
                    'xesam:album': Variant('s', track.album),
                    'xesam:artist': Variant('as', [track.artist])
                }
        self.emit_properties_changed(
            changed_properties={
                'Metadata': self._metadata
            },
            invalidated_properties=[]
        )

    # ... implement other MPRIS Player methods like Next, Previous, Stop, etc.

class MprisService(object):
    def __init__(self):
        self._dbus: MessageBus = None
        self._root = MprisRoot(APP_NAME)
        self._player = MprisPlayer(APP_NAME)

    async def init(self) -> None:
        self._dbus = await MessageBus().connect()
        self._dbus.export('/org/mpris/MediaPlayer2', self._root)
        self._dbus.export('/org/mpris/MediaPlayer2', self._player)
        _LOGGER.debug("Exported")

    async def register(self) -> None:
        await self._dbus.request_name(f'org.mpris.MediaPlayer2.{APP_NAME}')
        _LOGGER.debug("MPRIS service running.")

    async def shutdown(self) -> None:
        self._player.update_state(PlayState.STOPPED)
        self._player.update_metadata(None)
        self._dbus.unexport('/org/mpris/MediaPlayer2', self._player)
        self._dbus.unexport('/org/mpris/MediaPlayer2', self._root)
        _LOGGER.debug("MPRIS service shutting down.")
        # await self._dbus.release_name(f'org.mpris.MediaPlayer2.{APP_NAME}')
        self._dbus.disconnect()
        await self._dbus.wait_for_disconnect()
        _LOGGER.debug("MPRIS service shut down.")

    def set_player_metadata(self, track: YaTrack) -> None:
        self._player.update_metadata(track)

    def set_player_state(self, state: str) -> None:
        self._player.update_state(state)

