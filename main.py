from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static, Input
from textual.containers import Vertical, Horizontal

import os
import platform
import time
import threading
import requests
from textual.screen import Screen

from textual.reactive import var

def get_live_clock():
    return time.strftime("%H:%M:%S %A %d %b %Y")

def get_weather():
    # Placeholder: Replace with real API call if desired
    return "Weather: 25°C, Clear (Demo)"

def get_news():
    # Placeholder: Replace with real API call if desired
    return "News: Zelda TUI OS launched! (Demo)"

from textual.reactive import var
from textual.binding import Binding

class MainMenu(Static):
    BINDINGS = [
        Binding("enter", "press_focused_button", "Select"),
        Binding("space", "press_focused_button", "Select"),
    ]

    time_display = var(get_live_clock())
    _live_clock_widget = None

    def watch_time_display(self, time_display: str) -> None:
        # Only update if the widget has been composed and assigned
        if self._live_clock_widget:
            self._live_clock_widget.update(time_display)

    def on_mount(self) -> None:
        self._live_clock_widget = self.query_one("#live_clock", Static)
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        self.time_display = get_live_clock()

    def compose(self) -> ComposeResult:
        yield Static(self.time_display, id="live_clock")
        yield Static(get_weather())
        yield Static(get_news())
        yield Horizontal(
            Button("File Browser", id="file_browser"),
            Button("Calculator", id="calculator"),
            Button("System Info", id="system_info"),
            Button("Maze Game", id="maze_game"),
            Button("Nano Editor", id="nano_editor"),
            Button("Web Browser", id="web_browser"),
            Button("Pomodoro Timer", id="pomodoro_timer"),
            Button("Backgrounds", id="backgrounds"),
            Button("Exit", id="exit"),
            id="main_menu_buttons"
        )

    def action_press_focused_button(self) -> None:
        focused_widget = self.app.focused
        if isinstance(focused_widget, Button):
            focused_widget.press()

class ZeldaTUIOS(App):
    CSS_PATH = "zelda.css"
    TITLE = "Zelda TUI OS"
    SUB_TITLE = "A Textual-based OS in your terminal"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Static(get_live_clock(), id="clock"), # This will still be static, but the MainMenu's clock will be live
            Static(get_weather(), id="weather"),
            Static(get_news(), id="news"),
            id="dashboard"
        )
        yield Horizontal(MainMenu(), id="mainmenu")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.log(f"Button pressed: {event.button.id}") # Add logging
        button_id = event.button.id
        if button_id == "file_browser":
            self.push_screen(FileBrowserScreen())
        elif button_id == "calculator":
            self.push_screen(CalculatorScreen())
        elif button_id == "system_info":
            self.push_screen(SystemInfoScreen())
        elif button_id == "maze_game":
            self.push_screen(MazeGameScreen())
        elif button_id == "nano_editor":
            self.push_screen(NanoEditorScreen())
        elif button_id == "web_browser":
            self.push_screen(WebBrowserScreen())
        elif button_id == "pomodoro_timer":
            self.push_screen(PomodoroTimerScreen())
        elif button_id == "backgrounds":
            self.push_screen(BackgroundSelectorScreen())
        elif button_id == "exit":
            self.exit()
class MazeGameScreen(Screen):
    def __init__(self):
        super().__init__()
        self.maze = [
            "#########",
            "#S      #",
            "# # ### #",
            "# #   # #",
            "# ### # #",
            "#   # # #",
            "### # # #",
            "#     E #",
            "#########",
        ]
        self.player_pos = self.find_start()
        self.message = "Find the 'E' to exit!"

    def find_start(self):
        for r, row in enumerate(self.maze):
            for c, char in enumerate(row):
                if char == 'S':
                    return [r, c]
        return [1, 1] # Default if 'S' not found

    def compose(self) -> ComposeResult:
        maze_display = "\n".join([
            "".join([
                "P" if [r_idx, c_idx] == self.player_pos else char
                for c_idx, char in enumerate(row)
            ])
            for r_idx, row in enumerate(self.maze)
        ])
        yield Static(maze_display, id="maze_display")
        yield Static(self.message, id="maze_message")
        yield Horizontal(
            Button("Up", id="move_up"),
            Button("Down", id="move_down"),
            Button("Left", id="move_left"),
            Button("Right", id="move_right"),
        )
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        else:
            self.move_player(event.button.id)
            self.update_maze_display()

    def move_player(self, direction_id):
        r, c = self.player_pos
        new_r, new_c = r, c
        self.message = ""

        if direction_id == "move_up":
            new_r -= 1
        elif direction_id == "move_down":
            new_r += 1
        elif direction_id == "move_left":
            new_c -= 1
        elif direction_id == "move_right":
            new_c += 1

        if 0 <= new_r < len(self.maze) and 0 <= new_c < len(self.maze[0]):
            target_char = self.maze[new_r][new_c]
            if target_char == '#':
                self.message = "Can't go through walls!"
            else:
                self.player_pos = [new_r, new_c]
                if target_char == 'E':
                    self.message = "Congratulations! You found the exit!"
        else:
            self.message = "Out of bounds!"

    def update_maze_display(self):
        maze_display = "\n".join([
            "".join([
                "P" if [r_idx, c_idx] == self.player_pos else char
                for c_idx, char in enumerate(row)
            ])
            for r_idx, row in enumerate(self.maze)
        ])
        self.query_one("#maze_display", Static).update(maze_display)
        self.query_one("#maze_message", Static).update(self.message)

class NanoEditorScreen(Screen):
    def __init__(self, path=None):
        super().__init__()
        self.path = path
        self.content = ""
        if self.path and os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.content = f.read()

    def compose(self) -> ComposeResult:
        yield Static(f"Editing: {self.path or 'New File'}")
        yield Input(value=self.content, placeholder="Start typing...", id="editor_input", classes="editor")
        yield Horizontal(
            Button("Save", id="save_file"),
            Button("Back", id="back")
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "save_file":
            new_content = self.query_one("#editor_input", Input).value
            if self.path:
                try:
                    with open(self.path, "w") as f:
                        f.write(new_content)
                    self.query_one(Static).update(f"Saved: {self.path}")
                except Exception as e:
                    self.query_one(Static).update(f"Error saving file: {e}")
            else:
                # For new files, prompt for a path or save to a default location
                self.query_one(Static).update("Please specify a file path to save.")

class WebBrowserScreen(Screen):
    def __init__(self):
        super().__init__()
        self.url = ""

    def compose(self) -> ComposeResult:
        yield Static("TUI Web Browser (Limited Functionality)")
        yield Input(placeholder="Enter URL (e.g., example.com)", id="url_input")
        yield Button("Go", id="go_button")
        yield Static("", id="browser_content")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "go_button":
            self.url = self.query_one("#url_input", Input).value
            if self.url:
                display_url = self.url
                if not display_url.startswith("http://") and not display_url.startswith("https://"):
                    display_url = "http://" + display_url
                try:
                    response = requests.get(display_url)
                    self.query_one("#browser_content", Static).update(response.text)
                except requests.exceptions.RequestException as e:
                    self.query_one("#browser_content", Static).update(f"Error fetching URL: {e}\n\nNote: A full TUI web browser is a complex feature requiring a dedicated rendering engine. This is a placeholder.")
                except Exception as e:
                    self.query_one("#browser_content", Static).update(f"An unexpected error occurred: {e}\n\nNote: A full TUI web browser is a complex feature requiring a dedicated rendering engine. This is a placeholder.")
            else:
                self.query_one("#browser_content", Static).update("Please enter a URL.")

class PomodoroTimerScreen(Screen):
    def __init__(self):
        super().__init__()
        self.timer_running = False
        self.time_left = 25 * 60  # 25 minutes
        self.timer_thread = None

    def compose(self) -> ComposeResult:
        mins, secs = divmod(self.time_left, 60)
        yield Static(f"Pomodoro Timer: {mins:02d}:{secs:02d}")
        yield Button("Start", id="start")
        yield Button("Stop", id="stop")
        yield Button("Reset", id="reset")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start":
            if not self.timer_running:
                self.timer_running = True
                self.timer_thread = threading.Thread(target=self.run_timer, daemon=True)
                self.timer_thread.start()
                self.refresh()
        elif event.button.id == "stop":
            self.timer_running = False
        elif event.button.id == "reset":
            self.timer_running = False
            self.time_left = 25 * 60
            self.refresh()
        elif event.button.id == "back":
            self.timer_running = False
            self.app.pop_screen()

    def run_timer(self):
        while self.timer_running and self.time_left > 0:
            time.sleep(1)
            self.time_left -= 1
            self.refresh()

class BackgroundSelectorScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("Select a background:")
        yield Button("Default Background", id="bg_default")
        yield Button("Blue Theme", id="bg_blue")
        yield Button("Green Theme", id="bg_green")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "bg_default":
            self.app.query_one("Header").styles.background = "black"
            self.app.query_one("Footer").styles.background = "black"
            self.app.query_one("#dashboard").styles.background = "black"
            self.app.query_one("#mainmenu").styles.background = "black"
            self.query_one(Static).update("Background set to Default.")
        elif event.button.id == "bg_blue":
            self.app.query_one("Header").styles.background = "darkblue"
            self.app.query_one("Footer").styles.background = "darkblue"
            self.app.query_one("#dashboard").styles.background = "blue"
            self.app.query_one("#mainmenu").styles.background = "darkblue"
            self.query_one(Static).update("Background set to Blue Theme.")
        elif event.button.id == "bg_green":
            self.app.query_one("Header").styles.background = "darkgreen"
            self.app.query_one("Footer").styles.background = "darkgreen"
            self.app.query_one("#dashboard").styles.background = "green"
            self.app.query_one("#mainmenu").styles.background = "darkgreen"
            self.query_one(Static).update("Background set to Green Theme.")


class SystemInfoScreen(Screen):
    def compose(self) -> ComposeResult:
        sysinfo = f"OS: {platform.system()} {platform.release()}\n"
        sysinfo += f"Python: {platform.python_version()}\n"
        sysinfo += f"Machine: {platform.machine()}\n"
        sysinfo += f"Processor: {platform.processor()}\n"
        yield Static(sysinfo)
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class FileBrowserScreen(Screen):
    def __init__(self, path=None):
        super().__init__()
        self.path = path or os.getcwd()

    def compose(self) -> ComposeResult:
        yield Static(f"Current Directory: {self.path}")
        yield Button("..", id="parent_dir") # Button to go up one directory

        try:
            for item in os.listdir(self.path):
                full_path = os.path.join(self.path, item)
                if os.path.isdir(full_path):
                    yield Button(f"DIR: {item}", id=f"dir_{item}")
                else:
                    yield Button(f"FILE: {item}", id=f"file_{item}")
        except Exception as e:
            yield Static(f"Error: {e}")

        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "parent_dir":
            self.path = os.path.dirname(self.path)
            self.clear_screen()
            self.compose()
        elif event.button.id.startswith("dir_"):
            dir_name = event.button.id[4:]
            self.path = os.path.join(self.path, dir_name)
            self.clear_screen()
            self.compose()
        elif event.button.id.startswith("file_"):
            file_name = event.button.id[5:]
            # For now, just display file content. Later, integrate with Nano Editor.
            try:
                with open(os.path.join(self.path, file_name), "r") as f:
                    content = f.read()
                self.app.push_screen(FileContentScreen(file_name, content))
            except Exception as e:
                self.query_one(Static).update(f"Error reading file: {e}")

    def clear_screen(self):
        for widget in self.query():
            widget.remove()

class FileContentScreen(Screen):
    def __init__(self, filename, content):
        super().__init__()
        self.filename = filename
        self.content = content

    def compose(self) -> ComposeResult:
        yield Static(f"--- {self.filename} ---\n\n{self.content}")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class CalculatorScreen(Screen):
    def __init__(self):
        super().__init__()
        self.expression = ""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Enter expression...", id="expression")
        yield Static("", id="result")
        yield Horizontal(
            Button("7", id="btn_7"), Button("8", id="btn_8"), Button("9", id="btn_9"), Button("/", id="btn_divide"),
        )
        yield Horizontal(
            Button("4", id="btn_4"), Button("5", id="btn_5"), Button("6", id="btn_6"), Button("*", id="btn_multiply"),
        )
        yield Horizontal(
            Button("1", id="btn_1"), Button("2", id="btn_2"), Button("3", id="btn_3"), Button("-", id="btn_subtract"),
        )
        yield Horizontal(
            Button("0", id="btn_0"), Button(".", id="btn_dot"), Button("C", id="btn_clear"), Button("+", id="btn_add"),
        )
        yield Button("=", id="equals")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.app.pop_screen()
        elif button_id == "btn_clear":
            self.expression = ""
            self.query_one("#expression", Input).value = ""
            self.query_one("#result", Static).update("")
        elif button_id == "equals":
            try:
                result = str(eval(self.expression))
                self.query_one("#result", Static).update(result)
            except Exception as e:
                self.query_one("#result", Static).update("Error")
            self.expression = ""
        else:
            # Extract the numeric or operator part from the button_id
            if button_id.startswith("btn_"):
                self.expression += button_id[4:]
            elif button_id.startswith("btn_divide"):
                self.expression += "/"
            elif button_id.startswith("btn_multiply"):
                self.expression += "*"
            elif button_id.startswith("btn_subtract"):
                self.expression += "-"
            elif button_id.startswith("btn_add"):
                self.expression += "+"
            elif button_id.startswith("btn_dot"):
                self.expression += "."
            self.query_one("#expression", Input).value = self.expression

if __name__ == "__main__":
    ZeldaTUIOS().run()
