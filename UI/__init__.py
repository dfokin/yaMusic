"""UI classes"""
from ._ui import UI

async def run_ui() -> None:
    """Run UI until its shutdown"""
    gui: UI = UI()
    await gui.shutdown
    gui.destroy()
