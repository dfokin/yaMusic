"""Internal track representation"""
class YaTrack:
    """Internal representation of the track"""
    def __init__(self, title:str=None, artist:str=None,
                 uri:str=None, duration:int=0, is_liked:bool=None) -> None:
        self.title: str = title
        self.artist: str = artist
        self.uri: str = uri
        self.duration: int = duration
        self.is_liked: bool = is_liked

    def _str_duration(self) -> str:
        ''' Convert seconds to 'HH:MM:SS' '''
        hour: int = 0
        minute: int = 0
        second: int = 0

        minute, second = divmod(self.duration, 60)
        hour, minute = divmod(minute, 60)
        if hour == 0:
            if minute == 0:
                return f'00:{second:02}'
            return f'{minute}:{second:02}'
        return f'{hour}::{minute:02}::{second:02}'

    def __str__(self) -> str:
        return f'{self.artist} - {self.title} ({self._str_duration()})'

    def fixed_width(self, width: int) -> str:
        """Returns track description formatted to given string width"""
        dur: str = f'({self._str_duration()})'
        title: str = f'{self.artist} - {self.title}'
        if len(title) + len(dur) <= width:
            return f'{title: <{width-len(dur)}}{dur}'
        title = f'{title[:(width-len(dur)-4)]}...'
        return f'{title: <{width-len(dur)}}{dur}'
