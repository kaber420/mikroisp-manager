from textual.screen import ModalScreen
from textual.widgets import Button, Label, OptionList
from textual.containers import Container
from textual.app import ComposeResult

class MenuScreen(ModalScreen):
    """Modal Menu Screen"""

    CSS = """
    MenuScreen {
        align: center middle;
    }
    
    #menu-container {
        width: 60;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1;
    }
    
    OptionList {
        height: auto;
        max-height: 20;
    }
    """

    def __init__(self, items):
        super().__init__()
        self.items = items # List of (label, callback_name)

    def on_mount(self) -> None:
        self.query_one(OptionList).focus()

    def compose(self) -> ComposeResult:
        with Container(id="menu-container"):
            yield Label("Main Menu", classes="title")
            # We use OptionList to allow keyboard navigation
            options = [label for label, _ in self.items]
            yield OptionList(*options, id="menu-list")
            yield Button("Close", variant="error", id="close_btn")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        callback_name = self.items[idx][1]
        self.dismiss(callback_name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_btn":
            self.dismiss(None)
