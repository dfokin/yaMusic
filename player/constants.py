"""
Constants used in player components
"""
from typing import Dict

# UI keycodes
KEY_ESCAPE          : int = 9   # Esc
KEY_ZERO            : int = 19  # 0
KEY_EXIT            : int = 24  # q
KEY_PLAYLIST        : int = 33  # p
KEY_SETTINGS        : int = 39  # s
KEY_LIKE            : int = 46  # l
KEY_SKIP            : int = 57  # n
KEY_MUTE            : int = 58  # m
KEY_PLAY            : int = 65  # Spacebar
KEY_VOLUP           : int = 111 # arrow_up
KEY_BACK            : int = 113 # arrow_left
KEY_FWD             : int = 114 # arrow right
KEY_VOLDOWN         : int = 116 # arrow_down

# UI event types
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


APP_NAME                : str = 'yaMusic'
APP_CODEC               : str = 'mp3'
YANDEX_APP_NAME         : str = 'desktop_win-home-playlist_of_the_day-playlist-default'
CONFIG_NAME             : str = f'{APP_NAME}.yaml'
MODE_RADIO              : str = 'radio'
MODE_PLAYLIST           : str = 'playlist'
DEFAULT_MODE            : str = MODE_RADIO
DEFAULT_RADIO_SOURCE    : str = 'onyourwave'
DEFAULT_PLAYLIST_SOURCE : str = 'my_likes'

HI_RES_ICON             : str = 'ﳍ'
LIKE_ICON               : str = '♥'
MODE_ICONS              : Dict[str, str] ={
    MODE_PLAYLIST:  '',
    MODE_RADIO:     '露',
}
