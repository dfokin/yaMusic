"""Controls used in SettingsFrame"""
from tkinter.ttk import Button, Label


class SettingsButton(Button):
    """
    Ordinary button, but may be pressed by hitting Enter key
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args,  style='SettingsButton.TButton', **kwargs)
        self.bind('<Return>', lambda _: self.invoke())

class ColonLabel(Label):
    """
    Ordinary label, but with custom style and colon with space is added after the text
    """
    def __init__(self, *args, text: str = "", **kwargs):
        super().__init__(*args,  text=f'{text}: ', style='SettingsLabel.TLabel', **kwargs)
