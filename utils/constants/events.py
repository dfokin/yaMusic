"""Player events"""
from typing import Dict


TYPE_STATE          : int = 0
TYPE_ATF            : int = 1
TYPE_KEY            : int = 2
TYPE_TAGS           : int = 3
TYPE_REPEAT         : int = 4
TYPE_RESIZE         : int = 5
TYPE_SOURCE_UPD     : int = 6
TYPE_STATUS         : int = 7
TYPE_SKIP_POS       : int = 8
TYPE_QUERY_ARTISTS  : int = 9
TYPE_QUERY_ALBUMS   : int = 10
TYPE_QUERY_TRACKS   : int = 11
TYPE_SHUTDOWN       : int = 255

TYPE_TO_STR :Dict[int, str] = {
    TYPE_ATF:           'TYPE_ATF',
    TYPE_KEY:           'TYPE_KEY',
    TYPE_REPEAT:        'TYPE_REPEAT',
    TYPE_RESIZE:        'TYPE_RESIZE',
    TYPE_SHUTDOWN:      'TYPE_SHUTDOWN',
    TYPE_SKIP_POS:      'TYPE_SKIP_POS',
    TYPE_STATE:         'TYPE_STATE',
    TYPE_STATUS:        'TYPE_STATUS',
    TYPE_SOURCE_UPD:    'TYPE_SOURCE_UPD',
    TYPE_QUERY_ARTISTS:  'TYPE_QUERY_ARTISTS',
    TYPE_QUERY_ALBUMS:  'TYPE_QUERY_ALBUMS',
    TYPE_QUERY_TRACKS:  'TYPE_QUERY_TRACKS',
    TYPE_TAGS:          'TYPE_TAGS',
}
