"""
Constants used in player components
"""
from typing import Dict


MODE_RADIO          : str = 'radio'
MODE_PLAYLIST       : str = 'playlist'

HI_RES              : str = 'ﳍ'

MODE_ICONS          : Dict[str, str] ={
    MODE_PLAYLIST:  '',
    MODE_RADIO:     '露',
}


TRACK_LIKE          : str = '♥'

STATE_READY         : str = 'ready'
STATE_PLAYING       : str = 'playing'
STATE_PAUSED        : str = 'paused'
STATE_ATF           : str = 'atf'
STATE_ERR           : str = 'err'

CMD_PLAY            : str = 'play'
CMD_PAUSE           : str = 'pause'
CMD_STOP            : str = 'stop'
CMD_SKIP            : str = 'skip'
CMD_AGAIN           : str = 'play_again'
CMD_SKIP_F          : str = 'skip_forward'
CMD_SKIP_B          : str = 'skip_back'
CMD_SET_POSITION    : str = 'set_position'
CMD_SET_VOLUME      : str = 'set_volume'
CMD_SHUTDOWN        : str = 'shutdown'

ATTR_STATE          : str = 'state'
ATTR_VOLUME         : str = 'volume'
ATTR_POSITION       : str = 'position'
ATTR_DURATION       : str = 'duration'
ATTR_URI            : str = 'uri'
ATTR_TITLE          : str = 'title'
ATTR_ERROR          : str = 'error'

PROP_VOLUME         : str = 'volume'
PROP_URI            : str = 'uri'
PROP_VIS            : str = 'vis-plugin'
PROP_FLAGS          : str = 'flags'

KEY_ESCAPE          : int = 9
KEY_ZERO            : int = 19
KEY_EXIT            : int = 24
KEY_PLAYLIST        : int = 33
KEY_SETTINGS        : int = 39
KEY_LIKE            : int = 46
KEY_SKIP            : int = 57
KEY_MUTE            : int = 58
KEY_PLAY            : int = 65
KEY_VOLUP           : int = 111
KEY_BACK            : int = 113
KEY_FWD             : int = 114
KEY_VOLDOWN         : int = 116


TYPE_SHUTDOWN       : int = 0
TYPE_KEY            : int = 1
TYPE_STATE          : int = 2
TYPE_TAGS           : int = 3
TYPE_ATF            : int = 4
TYPE_RESIZE         : int = 5
TYPE_SOURCE_UPD     : int = 6
TYPE_STATUS         : int = 7

TYPE_TO_STR :Dict[int, str] = {
    0: 'TYPE_SHUTDOWN',
    1: 'TYPE_KEY',
    2: 'TYPE_STATE',
    3: 'TYPE_TAGS',
    4: 'TYPE_ATF',
    5: 'TYPE_RESIZE',
    6: 'TYPE_SETTINGS',
    7: 'TYPE_STATUS',
}

APP_NAME            : str = 'yaMusic'
CONFIG_NAME         : str = f'{APP_NAME}.yaml'
DEFAULT_MODE        : str = MODE_RADIO
DEFAULT_SOURCE      : str = 'onyourwave'
