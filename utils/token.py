"""
    Get API token
"""
import keyring
from keyring.backends import SecretService
from utils.config import get_key

def get_token() -> str:
    """
        Get API token from config or keyring
    """
    token: str = get_key('token', default='gnome_keyring')
    if token == 'gnome_keyring':
        keyring.set_keyring(SecretService.Keyring())
        token = keyring.get_password("yaMusic", "token")
    return token
