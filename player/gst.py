"""
Home of GstPlayer
"""
import logging
from queue import Empty
from typing import List

from aioprocessing import AioManager, AioQueue
import gi                                       # pylint: disable=import-error
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst             # pylint: disable=import-error,wrong-import-position

import player.constants as const                # pylint: disable=wrong-import-position


_FORMAT_TIME        : Gst.Format = Gst.Format(Gst.Format.TIME)
_NANOSEC_MULT       : int = 10 ** 9
_ATF_THRESHOLD      : float = 0.95
_GST_STATE_TIMEOUT  : int = 200 * Gst.MSECOND

_LOGGER: logging.Logger = logging.getLogger(__name__)


class GstPlayerException(Exception):
    """Is fired when something goes wrong"""


class GstPlayer:
    """
    Wrapper around Gstreamer process executing playbin.
    All communications with Python are handled by AioQueues and AioManager.
    """
    def __init__(
        self,
        dashboard: AioManager,
        command_queue: AioQueue,
        media_queue: AioQueue,
        ui_event_queue: AioQueue
    ):
        self._ui_event_queue: AioQueue = ui_event_queue
        self._command_queue: AioQueue = command_queue
        self._media_queue: AioQueue = media_queue
        self._dashboard: AioManager = dashboard

        self._atf_sent: bool = False

        # Create gst playbin and set event callbacks
        Gst.init(None)
        self._playbin: Gst.Element = Gst.ElementFactory.make('playbin', 'player')
        self._dashboard[const.ATTR_VOLUME] = self._playbin.get_property(const.PROP_VOLUME)
        self._playbin.connect("about-to-finish", self._on_atf)
        bus: Gst.Bus = self._playbin.get_bus()
        bus.add_signal_watch()
        bus.connect('message::error', self._on_error)
        bus.connect('message::eos', self._on_eos)
        bus.connect('message::state-changed', self._on_state_changed)
        # Visualizer
        # self._set_visualizer(self._playbin, 'goom')
        self._loop: GLib.MainLoop = GLib.MainLoop()
        _LOGGER.debug('Created Gstreamer playbin.')

    def run(self) -> None:
        """
        Gstreamer's main loop.
        Must be executed as a separate OS process to avoid GIL locks of Python's threads.
        """
        self._set_playbin_state(Gst.State.READY)

        _LOGGER.debug('Gstreamer playbin is starting.')
        GLib.timeout_add(500, self._periodic_task)
        self._loop.run()

        self._set_playbin_state(Gst.State.NULL)
        self._playbin = None
        _LOGGER.debug('Gstreamer playbin is shut down.')

    def _periodic_task(self) -> bool:
        """
        Is called periodically by the GLib's main loop.
        Dequeues pending commands and executes them.
        Updates own state, queues new track URIs to the playbin.
        """
        try:
            result = self._command_queue.get(False)
        except Empty:
            result = None

        try:
            if result:
                method, args = result
                getattr(self, method)(**args)
            if self._state == Gst.State.PLAYING:
                position: float = self._get_media_position()
                self._dashboard[const.ATTR_POSITION] = position
                if self._dashboard[const.ATTR_DURATION] == 0:
                    duration: float = self._get_media_duration()
                    self._dashboard[const.ATTR_DURATION] = duration
            elif self._state == Gst.State.READY:
                self._dequeue_next_media()
        except GstPlayerException as exc:
            self._error_handler(exc)
            return False

        return True

    def shutdown(self) -> None:
        """Shutdown process."""
        if self._state != Gst.State.NULL:
            self.stop()
        if self._loop.is_running():
            self._loop.quit()

    def play(self) -> None:
        """Change state to playing."""
        if self._state == Gst.State.PAUSED:
            self._set_playbin_state(Gst.State.PLAYING)

    def pause(self) -> None:
        """Change state to paused."""
        if self._state == Gst.State.PLAYING:
            self._set_playbin_state(Gst.State.PAUSED)

    def stop(self) -> None:
        """Stop pipeline."""
        self._set_playbin_state(Gst.State.READY)

    def skip(self) -> None:
        """Skip to next media."""
        self._set_playbin_state(Gst.State.READY)

    def play_again(self) -> None:
        """Start from the beginning."""
        self.set_position(0)

    def skip_forward(self) -> None:
        """Skip 5% of media."""
        inc = self._get_media_duration() / 20
        current = self._get_media_position()
        self.set_position(current + inc)

    def skip_back(self) -> None:
        """Back 5% of media."""
        inc = self._get_media_duration() / 20
        current = self._get_media_position()
        self.set_position(current - inc)

    def set_position(self, position: float) -> None:
        """Set media position."""
        duration: float = self._get_media_duration()
        if position > duration - (duration * 0.01):
            # Emission of ATF during seek is unreliable,
            # leave some time for track to complete and fire ATF
            return
        position = max(position, 0)
        self._playbin.seek_simple(
            _FORMAT_TIME, Gst.SeekFlags.FLUSH,
            position * _NANOSEC_MULT
        )
        self._dashboard[const.ATTR_POSITION] = position
        _LOGGER.debug('Set position to %d s.', position)

    def set_volume(self, volume: float) -> None:
        """Set volume."""
        self._playbin.set_property(const.PROP_VOLUME, volume)
        self._dashboard[const.ATTR_VOLUME] = volume
        _LOGGER.debug('volume set to %.2f', volume)

    def _get_media_duration(self) -> float:
        """Get media duration."""
        duration = 0.0
        if self._state in [Gst.State.PAUSED, Gst.State.PLAYING]:
            ok, dur = self._playbin.query_duration(_FORMAT_TIME)
            if ok:
                duration = dur // _NANOSEC_MULT
        return duration

    def _get_media_position(self) -> float:
        """Get media position."""
        position: float = 0.0
        if self._state in [Gst.State.PAUSED, Gst.State.PLAYING]:
            position = self._dashboard[const.ATTR_POSITION]
            ok, pos = self._playbin.query_position(_FORMAT_TIME)
            if ok:
                position = pos // _NANOSEC_MULT
        return position

    def _dequeue_next_media(self) -> None:
        """Get next uri from media queue and set it as next uri in the playbin"""
        try:
            uri: str = self._media_queue.get(False)
        except Empty:
            return
        _LOGGER.debug('Next track is %s.', uri)
        self._atf_sent = False
        self._dashboard[const.ATTR_URI] = uri
        self._dashboard[const.ATTR_POSITION] = 0
        self._dashboard[const.ATTR_DURATION] = 0
        self._playbin.set_property(const.PROP_URI, uri)
        if self._state == Gst.State.READY:
            self._set_playbin_state(Gst.State.PLAYING)

    def _set_own_state(self, state: str, emit: bool = True) -> None:
        self._dashboard[const.ATTR_STATE] = state
        if emit:
            self._emit_state_event()

    @property
    def _state(self) -> Gst.State:
        """Return only final state, wait if state change is currently transient"""
        result, current, pending = self._playbin.get_state(_GST_STATE_TIMEOUT)
        while result != Gst.StateChangeReturn.SUCCESS and pending != Gst.State.VOID_PENDING:
            if result == Gst.StateChangeReturn.FAILURE:
                raise GstPlayerException('Unable to get current playbin state.')
            _LOGGER.debug('---TRANSIENT STATE---')
            result, current, pending = self._playbin.get_state(_GST_STATE_TIMEOUT)

        return current

    def _set_playbin_state(self, state: Gst.State):
        if self._playbin.set_state(state) == Gst.StateChangeReturn.FAILURE:
            raise GstPlayerException(f'Unable to set the pipeline to the {state.name} state.')

    def _emit_state_event(self) -> None:
        self._ui_event_queue.put(dict(type=const.TYPE_STATE))

    def _emit_atf_event(self) -> None:
        if not self._atf_sent:
            self._ui_event_queue.put(dict(type=const.TYPE_ATF))
            self._atf_sent = True

    def _eos_handler(self):
        self._set_playbin_state(Gst.State.READY)
        _LOGGER.debug('Finished %s.', self._dashboard[const.ATTR_URI])

    def _error_handler(self, error: str):
        # Stop and shutdown if something goes wrong.
        _LOGGER.error('Gstreamer fired error: %s. Shutting down.', error)
        self._dashboard[const.ATTR_ERROR] = error
        self._set_own_state(const.STATE_ERR)
        self.shutdown()

    # Handle events from Gstreamer
    def _on_atf(self, stream: Gst.Stream) -> None:                              # pylint: disable=unused-argument
        _LOGGER.debug('Track about to finish.')
        self._emit_atf_event()

    def _on_error(self, bus: Gst.Bus, message: Gst.Message) -> None:            # pylint: disable=unused-argument
        error, debug = message.parse_error()
        _LOGGER.debug('Gstreamer error details: %s.', debug)
        self._error_handler(error)

    def _on_eos(self, bus: Gst.Bus, message: Gst.Message) -> None:              # pylint: disable=unused-argument
        # Just change internal state, next media URI will be requested and
        # queued after ATF event and will be dequeued in the run loop.
        self._eos_handler()

    def _on_state_changed(self, bus: Gst.Bus, message: Gst.Message) -> None:    # pylint: disable=unused-argument
        if not message.src == self._playbin:
            return
        old, new, pending = message.parse_state_changed()
        _LOGGER.debug('GST state %s -> %s -> (%s).',
            Gst.Element.state_get_name(old),
            Gst.Element.state_get_name(new),
            Gst.Element.state_get_name(pending))
        if new == Gst.State.PLAYING:
            self._set_own_state(const.STATE_PLAYING)
        elif new == Gst.State.READY:
            self._set_own_state(const.STATE_READY)
        elif new == Gst.State.PAUSED:
            self._set_own_state(const.STATE_PAUSED)

    @staticmethod
    def _set_visualizer(playbin: Gst.Element, name: str):
        vis_list: List[Gst.ElementFactory] = Gst.Registry.feature_filter(
            Gst.Registry.get(),
            lambda e, _: isinstance(e, Gst.ElementFactory) and e.get_klass() == 'Visualization',
            False,
            None)
        for item in vis_list:
            if item.name == name:
                playbin.set_property(const.PROP_VIS, Gst.ElementFactory.create(item))
                playbin.set_property(const.PROP_FLAGS, 0x01+0x02+0x08+0x10+0x200+0x400)
