# widgets.py
from textual.widgets import Static
from textual.reactive import var
import time

class ClockWidget(Static):
    time_display = var(time.strftime("%H:%M:%S"))

    def on_mount(self) -> None:
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        self.time_display = time.strftime("%H:%M:%S")

    def render(self) -> str:
        return f"Clock: {self.time_display}"

class WeatherWidget(Static):
    def render(self) -> str:
        # This will be a static placeholder as httpx is not guaranteed to be installed
        return "Weather: N/A (Install httpx and set API key)"

class NewsWidget(Static):
    def render(self) -> str:
        # This will be a static placeholder as httpx is not guaranteed to be installed
        return "News: N/A (Install httpx and set API key)"

class CalculatorWidget(Static):
    def render(self) -> str:
        return "Calculator Widget (Click to open app)"

class MazeWidget(Static):
    def render(self) -> str:
        return "Maze Widget (Click to open app)"
