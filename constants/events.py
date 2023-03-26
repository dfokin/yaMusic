"""Player events"""
from typing import Dict


TYPE_STATE          : int = 0
TYPE_ATF            : int = 1
TYPE_KEY            : int = 2
TYPE_TAGS           : int = 3
TYPE_RESIZE         : int = 4
TYPE_SOURCE_UPD     : int = 5
TYPE_STATUS         : int = 6
TYPE_SHUTDOWN       : int = 255

TYPE_TO_STR :Dict[int, str] = {
    TYPE_ATF:           'TYPE_ATF',
    TYPE_KEY:           'TYPE_KEY',
    TYPE_RESIZE:        'TYPE_RESIZE',
    TYPE_SHUTDOWN:      'TYPE_SHUTDOWN',
    TYPE_STATE:         'TYPE_STATE',
    TYPE_STATUS:        'TYPE_STATUS',
    TYPE_SOURCE_UPD:    'TYPE_SOURCE_UPD',
    TYPE_TAGS:          'TYPE_TAGS',
}
