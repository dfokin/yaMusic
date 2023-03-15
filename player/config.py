"""Config file routines"""
from os import makedirs
from os.path import join, expanduser, exists, isdir, isfile
from pathlib import Path
from typing import Dict, Optional, Union, List

import yaml

from player.constants import APP_NAME, CONFIG_NAME


CONFIG: Dict = None

class ConfigError(Exception):
    """General config error"""

_XDG_CONFIG_DIR: str = join(expanduser('~'), '.config')

if not exists(_XDG_CONFIG_DIR) or not isdir(_XDG_CONFIG_DIR):
    raise ConfigError('No valid $XDG_CONFIG_DIR found!')

_CONFIG_DIR: str = join(_XDG_CONFIG_DIR, APP_NAME)

if not exists(_CONFIG_DIR):
    makedirs(_CONFIG_DIR)

if not isdir(_CONFIG_DIR):
    raise ConfigError(f'{_CONFIG_DIR} is not a directory!')

_CONFIG_PATH: str = join(_CONFIG_DIR, CONFIG_NAME)

if not exists(_CONFIG_PATH):
    Path(_CONFIG_PATH).touch(mode=0o600)

if not isfile(_CONFIG_PATH):
    raise ConfigError(f'{_CONFIG_PATH} is not a file!')

try:
    with open(_CONFIG_PATH, 'r', encoding='utf-8') as infile:
        CONFIG = yaml.load(infile, Loader=yaml.FullLoader)
        if not CONFIG:
            CONFIG = {}
except OSError as exc:
    raise ConfigError(f'Failed to load config: {exc}')              # pylint: disable=raise-missing-from

def save() -> None:
    """Save current version of config"""
    try:
        with open(_CONFIG_PATH, 'w', encoding='utf-8') as outfile:
            outfile.write(yaml.dump(CONFIG))
    except OSError as err:
        raise ConfigError(f'Failed to save config: {err}')          # pylint: disable=raise-missing-from

def get_key(key: str, default=None) -> Optional[Union[int, float, str, Dict, List]]:
    """Get config value by key"""
    return CONFIG.get(key, default)

def get_station_settings(station_id: str, default=None) -> Optional[Dict]:
    """Get station settings by its id"""
    if not CONFIG.get('station_settings'):
        return default
    return CONFIG['station_settings'].get(station_id, default)

def set_station_settings(station_id: str, val: Dict) -> None:
    """Set station settings by its id"""
    if not CONFIG['station_settings']:
        CONFIG['station_settings'] = {}
    CONFIG['station_settings'][station_id] = val

def set_key(key: str, val: Union[int, float, str, Dict, List]) -> None:
    """Set config value by key"""
    CONFIG[key] = val
