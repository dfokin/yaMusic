"""UI styling helpers"""
from tkinter import SOLID
from tkinter.font import Font
from tkinter.ttk import Style

borderwidth = 1
fontsize = 8
padding = 10
bgcolor = '#875F00'
fgcolor = '#222222'
progress_chars = 60
PLAYLIST_HEIGHT = 500

MAIN_FONT: str = 'Iosevka NF SNV Sans Fixed'
PROGRESS_FONT: str = 'Terminus'

main_font: Font = (MAIN_FONT, fontsize)
spinner_font: Font = (MAIN_FONT, fontsize)
status_font: Font = (MAIN_FONT, fontsize-2)
progress_font: Font = (PROGRESS_FONT, fontsize + 2)

def build_styles(style: Style) -> None:
    """Build custom styles used in application UI"""
    style.configure('MainFrame.TFrame',
        background=bgcolor,
        )

    style.configure('DisplayFrame.TLabelframe',
        background=bgcolor,
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

    style.configure('SpinnerLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=spinner_font,
        )

    style.configure('ProgressLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=progress_font
        )

    style.configure('VolumeLabel.TLabel',
        background=bgcolor,
        foreground=fgcolor,
        font=spinner_font,
        )

    style.configure('SettingsFrame.TLabelframe',
        background=bgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
    )
    style.configure('SettingsFrame.TLabelframe.Label',
        background=bgcolor,
        foreground=fgcolor,
        font=main_font
    )

    style.configure('PlaylistFrame.TLabelframe',
        background=bgcolor,
        borderwidth=borderwidth,
        relief=SOLID,
    )
    style.configure('PlaylistFrame.TLabelframe.Label',
        background=bgcolor,
        foreground=fgcolor,
        font=main_font
    )
    style.configure('Vertical.TScrollbar',
        background=fgcolor,
        arrowcolor=bgcolor,
        troughcolor=bgcolor,
        arrowsize=25,
        relief='flat',
    )
    style.configure('ComboBox.TCombobox',
        font=main_font,
        arrowsize=25,
        borderwidth=1,
        relief='flat',
    )
    style.map('ComboBox.TCombobox',
        arrowcolor=      [('!focus', '!pressed', fgcolor), ('focus', bgcolor), ('pressed', bgcolor)],
        insertcolor=     [('!focus', '!pressed', fgcolor), ('focus', bgcolor), ('pressed', bgcolor)],
        foreground=      [('!focus', '!pressed', fgcolor), ('focus', bgcolor), ('pressed', bgcolor)],
        background=      [('!focus', '!pressed', bgcolor), ('focus', fgcolor), ('pressed', fgcolor)],
        fieldforeground= [('!focus', '!pressed', fgcolor), ('focus', bgcolor), ('pressed', bgcolor)],
        fieldbackground= [('!focus', '!pressed', bgcolor), ('focus', fgcolor), ('pressed', fgcolor)],
        selectforeground=[('!focus', '!pressed', bgcolor), ('focus', bgcolor), ('pressed', bgcolor)],
        selectbackground=[('!focus', '!pressed', fgcolor), ('focus', fgcolor), ('pressed', fgcolor)],
    )
    style.configure('SettingsLabel.TLabel',
        font=main_font,
        background=bgcolor,
        foreground=fgcolor,
    )
    style.configure('SettingsButton.TButton',
        font=main_font,
        bordercolor=fgcolor,
        relief='flat',
    )
    style.map('SettingsButton.TButton',
        foreground=[('!active', '!focus', fgcolor), ('focus', bgcolor), ('active', bgcolor)],
        background=[('!active', '!focus', bgcolor), ('focus', fgcolor), ('active', fgcolor)],
    )

def apply_custom_combo_styling(obj) -> None:
    """Apply to object custom Combobox style"""
    obj.option_add('*TCombobox*Listbox.font', main_font)
    obj.option_add('*TCombobox*Listbox.background', bgcolor)
    obj.option_add('*TCombobox*Listbox.foreground', fgcolor)
    obj.option_add('*TCombobox*Listbox.selectBackground', fgcolor)
    obj.option_add('*TCombobox*Listbox.selectForeground', bgcolor)
