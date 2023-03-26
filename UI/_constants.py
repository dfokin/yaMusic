"""UI constants"""
from typing import Dict
from constants.player import MODE_PLAYLIST, MODE_RADIO

# UI keycodes
KEY_ESCAPE          : int = 9   # Esc
KEY_ZERO            : int = 19  # 0
KEY_EXIT            : int = 24  # q
KEY_REPEAT          : int = 27  # r
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

# Icons
HI_RES_ICON             : str = 'ﳍ'
LIKE_ICON               : str = '♥'
REPEAT_ICON             : str = '累'
MODE_ICONS              : Dict[str, str] ={
    MODE_PLAYLIST:  '',
    MODE_RADIO:     '露',
}
