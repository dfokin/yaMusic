""" MPRIS service implementation """
import logging
from typing import Dict

from dbus_next.glib import MessageBus
from dbus_next.service import ServiceInterface, dbus_property
from dbus_next.constants import PropertyAccess
from dbus_next import Variant
from strenum import StrEnum

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

    def update_metadata(self, track: Dict) -> None:
        if track is None:
            self._metadata = {
                    'mpris:trackid': Variant('o', '/track/none'),
                    'mpris:length': Variant('x', 0),
                    'xesam:title': Variant('s', ''),
                    'xesam:album': Variant('s', ''),
                    'xesam:artist': Variant('as', [''])
                }
        else:
            self._metadata = {
                    'mpris:trackid': Variant('o', '/track/none'),
                    'mpris:length': Variant('x', track.get('duration') * 1000000),
                    'xesam:title': Variant('s', track.get('title')),
                    'xesam:album': Variant('s', track.get('album')),
                    'xesam:artist': Variant('as', [track.get('artist')])
                }

        self.emit_properties_changed(
            changed_properties={
                'Metadata': self._metadata
            },
            invalidated_properties=[]
        )

class MprisService(object):
    def __init__(self, name):
        self._name = name
        self._dbus: MessageBus = None
        self._dbus = MessageBus().connect_sync()
        self._root = MprisRoot(self._name)
        self._player = MprisPlayer(self._name)
        self._dbus.export('/org/mpris/MediaPlayer2', self._root)
        self._dbus.export('/org/mpris/MediaPlayer2', self._player)
        self._dbus.request_name_sync(f'org.mpris.MediaPlayer2.{self._name}')
        _LOGGER.debug("MPRIS service is running.")

    def shutdown(self) -> None:
        self._player.update_state(PlayState.STOPPED)
        self._player.update_metadata(None)
        self._dbus.unexport('/org/mpris/MediaPlayer2', self._player)
        self._dbus.unexport('/org/mpris/MediaPlayer2', self._root)
        self._dbus.release_name_sync(f'org.mpris.MediaPlayer2.{self._name}')
        self._dbus.disconnect()
        _LOGGER.debug("MPRIS service is shut down.")

    def set_player_metadata(self, track: Dict) -> None:
        self._player.update_metadata(track)

    def set_player_state(self, state: str) -> None:
        self._player.update_state(state)
