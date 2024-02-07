"""UI styling helpers"""
from tkinter import SOLID, SINGLE, BROWSE
from tkinter.font import Font
from tkinter.ttk import Style

from typing import Dict, Tuple, Union

PROGRESS_FONT   :str = 'Terminus'
MAIN_FONT       :str = 'Iosevka NF SNV Sans Fixed'

borderwidth     :int = 1
fontsize        :int = 8
padding         :int = 10
bgcolor         :str = '#875F00'
fgcolor         :str = '#252525'
focuscolor      :str = '#C2B790'
progress_chars  :int = 60

main_font       :Tuple[str, int] = (MAIN_FONT,      fontsize)
mode_font       :Tuple[str, int] = (MAIN_FONT,      fontsize + 4)
status_font     :Tuple[str, int] = (MAIN_FONT,      fontsize - 2)
progress_font   :Tuple[str, int] = (PROGRESS_FONT,  fontsize + 2)

def measure_main_font() -> int:
    """Returns width of one character in pixels"""
    font: Font = Font(family=main_font[0], size=main_font[1])
    return font.measure(' ')

def build_styles(style: Style) -> None:
    """Build custom styles used in application UI"""
    style.theme_use('black')

    style.configure('MainFrame.TFrame',
        background=bgcolor,
        )
    style.configure('ModeSource.TFrame',
        background=bgcolor,
        )
    style.configure('CFrame.TFrame',
        background=bgcolor,
        borderwidth=0,
        bordercolor=fgcolor,
        relief=SOLID,
    )

    style.configure('Search.TEntry',
        insertwidth=3,
        borderwidth=2,
        selectborderwidth=0,
        fieldbackground=bgcolor,
        lightcolor=fgcolor,
        insertbackground=fgcolor,
        foreground=fgcolor,
        selectforeground=bgcolor,
        selectbackground=fgcolor,
        exportselection=0,
        relief=SOLID,
    )
    style.map('Search.TEntry',
        selectforeground=[('!active', '!focus', bgcolor), ('focus', bgcolor), ('active', bgcolor)],
    )

    style.configure('DisplayFrame.TLabelframe',
        background=bgcolor,
        foreground=fgcolor,
        bordercolor=fgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
    )
    style.configure('DisplayFrame.TLabelframe.Label',
        background=bgcolor,
        foreground=fgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
        font=status_font
    )

    style.configure('ProgressFrame.TLabelframe',
        background=bgcolor,
        foreground=fgcolor,
        bordercolor=fgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
    )
    style.configure('ProgressFrame.TLabelframe.Label',
        background=bgcolor,
        foreground=fgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
        font=main_font
    )

    style.configure('SettingsFrame.TLabelframe',
        background=bgcolor,
        foreground=fgcolor,
        borderwidth=borderwidth,
        bordercolor=fgcolor,
        relief=SOLID,
    )
    style.configure('SettingsFrame.TLabelframe.Label',
        background=bgcolor,
        foreground=fgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
        font=main_font
    )

    style.configure('PlaylistFrame.TLabelframe',
        background=bgcolor,
        foreground=fgcolor,
        borderwidth=borderwidth,
        bordercolor=fgcolor,
        relief=SOLID,
    )
    style.configure('PlaylistFrame.TLabelframe.Label',
        background=bgcolor,
        foreground=fgcolor,
        font=main_font
    )

    style.configure('SpinnerLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=main_font,
        )
    style.configure('VolumeLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=main_font,
        )

    style.configure('SettingsLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=main_font,
    )
    style.configure('ModeLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=mode_font,
        )

    style.configure('ProgressLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=progress_font
        )

    style.configure('SettingsButton.TButton',
        font=main_font,
        anchor='center',
        borderwidth=borderwidth,
        bordercolor=fgcolor,
        relief=SOLID,
    )
    style.map('SettingsButton.TButton',
        foreground=[('!active', '!focus', fgcolor), ('focus', bgcolor), ('active', bgcolor)],
        background=[('!active', '!focus', bgcolor), ('focus', fgcolor), ('active', fgcolor)],
    )

    style.configure('Vertical.TScrollbar',
        highlightthickness=0,
        borderwidth=2,
        arrowsize=20,
        relief='solid',
    )
    style.map('Vertical.TScrollbar',
        arrowcolor= [
            ('!active', '!disabled', fgcolor),
            ('active', '!disabled', fgcolor),
            ('disabled', bgcolor)
        ],
        bordercolor=[
            ('!active', '!disabled', fgcolor),
            ('active', '!disabled', fgcolor),
            ('disabled', bgcolor)
        ],
        lightcolor= [
            ('!active', '!disabled', fgcolor),
            ('active', '!disabled', fgcolor),
            ('disabled', fgcolor)
        ],
        darkcolor=  [
            ('!active', '!disabled', fgcolor),
            ('active', '!disabled', fgcolor),
            ('disabled', fgcolor)
        ],
        troughcolor=[
            ('!active', '!disabled', bgcolor),
            ('active', '!disabled', bgcolor),
            ('disabled', bgcolor)
        ],
        background= [
            ('!active', '!disabled', bgcolor),
            ('active', '!disabled', bgcolor),
            ('disabled', bgcolor)
        ],
    )

    style.configure('ComboBox.TCombobox',
        arrowsize=25,
        bordercolor=fgcolor,
        lightcolor=fgcolor,
        darkcolor=fgcolor,
        relief='flat',
    )
    style.map('ComboBox.TCombobox',
        arrowcolor=[
            ('!focus', '!pressed', fgcolor),
            ('focus', bgcolor),
            ('pressed', bgcolor)
        ],
        insertcolor=[
            ('!focus', '!pressed', fgcolor),
            ('focus', bgcolor),
            ('pressed', bgcolor)
        ],
        foreground=[
            ('!focus', '!pressed', fgcolor),
            ('focus', bgcolor),
            ('pressed', bgcolor)
        ],
        background=[
            ('!focus', '!pressed', bgcolor),
            ('focus', fgcolor),
            ('pressed', fgcolor)
        ],
        fieldforeground=[
            ('!focus', '!pressed', fgcolor),
            ('focus', bgcolor),
            ('pressed', bgcolor)
        ],
        fieldbackground=[
            ('!focus', '!pressed', bgcolor),
            ('focus', fgcolor),
            ('pressed', fgcolor)
        ],
        selectforeground=[
            ('!focus', '!pressed', bgcolor),
            ('focus', bgcolor),
            ('pressed', bgcolor)
        ],
        selectbackground=[
            ('!focus', '!pressed', fgcolor),
            ('focus', fgcolor),
            ('pressed', fgcolor)
        ],
    )

ListBoxStyle: Dict[str, Union[int, str]] = dict(
    font=main_font,
    borderwidth=0,
    highlightthickness=borderwidth,
    highlightbackground=fgcolor,
    highlightcolor=fgcolor,
    background=bgcolor,
    foreground=fgcolor,
    selectbackground=fgcolor,
    selectforeground=bgcolor,
    selectborderwidth=0,
    relief='flat',
    selectmode=SINGLE,
    exportselection=False,
)

ListBoxStyle_S: Dict[str, Union[int, str]] = ListBoxStyle
ListBoxStyle_S['selectmode'] = BROWSE

def apply_custom_combo_styling(obj) -> None:
    """Apply to object custom Combobox style"""
    obj.option_add('*TCombobox*Listbox.font', main_font)
    obj.option_add('*TCombobox*Listbox.background', bgcolor)
    obj.option_add('*TCombobox*Listbox.foreground', fgcolor)
    obj.option_add('*TCombobox*Listbox.selectBackground', fgcolor)
    obj.option_add('*TCombobox*Listbox.selectForeground', bgcolor)
