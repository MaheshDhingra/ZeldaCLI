from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static, Input
from textual.containers import Vertical, Horizontal

import os
import platform
import time
import threading
import requests
from textual.screen import Screen

class MainMenu(Static):
    def compose(self) -> ComposeResult:
        yield Static(get_live_clock())
        yield Static(get_weather())
        yield Static(get_news())
        yield Button("File Browser", id="file_browser")
        yield Button("Calculator", id="calculator")
        yield Button("System Info", id="system_info")
        yield Button("Maze Game", id="maze_game")
        yield Button("Nano Editor", id="nano_editor")
        yield Button("Web Browser", id="web_browser")
        yield Button("Pomodoro Timer", id="pomodoro_timer")
        yield Button("Backgrounds", id="backgrounds")
        yield Button("Exit", id="exit")
def get_live_clock():
    return time.strftime("🕒 %H:%M:%S %A %d %b %Y")

def get_weather():
    # Placeholder: Replace with real API call if desired
    return "🌤️ Weather: 25°C, Clear (Demo)"

def get_news():
    # Placeholder: Replace with real API call if desired
    return "📰 News: Zelda TUI OS launched! (Demo)"

class ZeldaTUIOS(App):
    CSS_PATH = "zelda.css"
    TITLE = "Zelda TUI OS"
    SUB_TITLE = "A Textual-based OS in your terminal"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(
            Static(get_live_clock(), id="clock"),
            Static(get_weather(), id="weather"),
            Static(get_news(), id="news"),
            id="dashboard"
        )
        yield Vertical(MainMenu(), id="mainmenu")
        yield Footer()
def get_live_clock():
    import time
    return time.strftime("🕒 %H:%M:%S %A %d %b %Y")

def get_weather():
    return "🌤️ Weather: 25°C, Clear (Demo)"

def get_news():
    return "📰 News: Zelda TUI OS launched! (Demo)"

    def on_button_pressed(self, event: Button.Pressed) -> None:
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
    def compose(self) -> ComposeResult:
        yield Static("Maze game coming soon!")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class NanoEditorScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("Nano-like editor coming soon!")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class WebBrowserScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("TUI Web browser coming soon!")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

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
        yield Static("Select a live or custom background (feature coming soon!)")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()


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
        files = os.listdir(self.path)
        file_list = "\n".join(files)
        yield Static(f"Current Directory: {self.path}\n\n{file_list}")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class CalculatorScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Static("Calculator coming soon!")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

if __name__ == "__main__":
    ZeldaTUIOS().run()
