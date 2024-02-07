"""UI constants"""
from typing import Dict
from utils.constants.player import MODE_PLAYLIST, MODE_RADIO, MODE_ARTIST

# UI keycodes
KEY_ESCAPE          : int = 9   # Esc
KEY_ZERO            : int = 19  # 0
KEY_EXIT            : int = 24  # q
KEY_RADIO           : int = 27  # r
KEY_PLAYLIST        : int = 33  # p
KEY_ARTIST          : int = 38  # a
KEY_SETTINGS        : int = 39  # s
KEY_LIKE            : int = 46  # l
KEY_REPEAT          : int = 54  # c
KEY_SKIP            : int = 57  # n
KEY_MUTE            : int = 58  # m
KEY_PLAY            : int = 65  # Spacebar
KEY_VOLUP           : int = 111 # arrow_up
KEY_BACK            : int = 113 # arrow_left
KEY_FWD             : int = 114 # arrow right
KEY_VOLDOWN         : int = 116 # arrow_down

# Icons
HI_RES_ICON         : str = 'ﳍ'
LIKE_ICON           : str = '♥'
REPEAT_ICON         : str = '累'
PLAYLIST_ICON       : str = ''
RADIO_ICON          : str = '露'
ARTIST_ICON         : str = ''
ALBUM_ICON          : str = ''
TRACK_ICON          : str = 'ﭵ'

MODE_ICONS          : Dict[str, str] ={
    MODE_PLAYLIST   : PLAYLIST_ICON,
    MODE_RADIO      : RADIO_ICON,
    MODE_ARTIST     : ARTIST_ICON,
}
