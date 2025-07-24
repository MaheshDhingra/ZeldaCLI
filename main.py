from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Static, Input
from textual.containers import Vertical, Horizontal, ScrollableContainer

import os
import platform
import time
import threading
import requests
from textual.screen import Screen
import asyncio
import httpx
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv # Import load_dotenv
import html2text # Import html2text

# Load environment variables from .env file
load_dotenv()

def get_live_clock():
    return time.strftime("%H:%M:%S %A %d %b %Y")

async def get_weather():
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    city = os.getenv("DEFAULT_CITY", "London") # Use DEFAULT_CITY from .env
    if not api_key or api_key == "YOUR_OPENWEATHERMAP_API_KEY":
        return "Weather Error: OpenWeatherMap API key not configured in .env"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            weather_desc = data["weather"][0]["description"].capitalize()
            temp = data["main"]["temp"]
            return f"Weather: {temp}°C, {weather_desc} ({city})"
    except httpx.RequestError as e:
        return f"Weather Error: {e} (Check API key and 'httpx' installation)"
    except json.JSONDecodeError:
        return "Weather Error: Invalid API response (Check API key)"
    except Exception as e:
        return f"Weather Error: {e}"

async def get_news():
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key or api_key == "YOUR_NEWSAPI_API_KEY":
        return "News Error: NewsAPI API key not configured in .env"
    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data["articles"]:
                first_article = data["articles"][0]
                return f"News: {first_article['title']} (Source: {first_article['source']['name']})"
            else:
                return "News: No top headlines found."
    except httpx.RequestError as e:
        return f"News Error: {e} (Check API key and 'httpx' installation)"
    except json.JSONDecodeError:
        return "News Error: Invalid API response (Check API key)"
    except Exception as e:
        return f"News Error: {e}"

from textual.reactive import var
from textual.binding import Binding

class ChessBoard:
    def __init__(self):
        self.board = self._initialize_board()
        self.current_player = "White" # White starts

    def _initialize_board(self):
        # A simplified board for display purposes
        # R=Rook, N=Knight, B=Bishop, Q=Queen, K=King, P=Pawn
        # Lowercase for black, uppercase for white
        return [
            ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
            ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
            [' ', '.', ' ', '.', ' ', '.', ' ', '.'],
            ['.', ' ', '.', ' ', '.', ' ', '.', ' '],
            [' ', '.', ' ', '.', ' ', '.', ' ', '.'],
            ['.', ' ', '.', ' ', '.', ' ', '.', ' '],
            ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
            ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
        ]

    def display(self):
        board_str = "  a b c d e f g h\n"
        board_str += " +-----------------+\n"
        for i, row in enumerate(self.board):
            board_str += f"{8 - i}|"
            for piece in row:
                board_str += f"{piece} "
            board_str += "|\n"
        board_str += " +-----------------+\n"
        return board_str

    def make_move(self, move_str):
        return f"Attempted move: {move_str}. (Move logic not fully implemented)"

    def get_status(self):
        return f"{self.current_player} to move."

    def is_game_over(self):
        return False

    def switch_player(self):
        self.current_player = "Black" if self.current_player == "White" else "White"

MAZES = [
    # Maze 1 (Current one)
    [
        "#########",
        "#S      #",
        "# # ### #",
        "# #   # #",
        "# ### # #",
        "#   # # #",
        "### # # #",
        "#     E #",
        "#########",
    ],
    # Maze 2 (A slightly different one)
    [
        "###########",
        "#S #      #",
        "#  # # ## #",
        "## # # #  #",
        "#  # # # ##",
        "# ## # #  #",
        "#  # # # ##",
        "## # # #  #",
        "#  #   # E#",
        "###########",
    ],
    # Maze 3 (Another example)
    [
        "#############",
        "#S          #",
        "### ### ### #",
        "#   #   #   #",
        "# ### ### ###",
        "# #   #   # #",
        "# # ### ### #",
        "# #   #   # #",
        "# ### ### ###",
        "#           E#",
        "#############",
    ]
]

class MailService:
    def __init__(self, smtp_server, smtp_port, smtp_username, smtp_password, sender_email):
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port) # Ensure port is an integer
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.inbox = [] # Still simulated for receiving, as a full IMAP/POP3 client is out of scope
        self.sent_items = []
        self.current_user = sender_email # Use the actual sender email as the current user

    def send_message(self, recipient, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls() # Secure the connection
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)

            message = {
                "from": self.sender_email,
                "to": recipient,
                "subject": subject,
                "body": body,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.sent_items.append(message)
            return "Message sent successfully!"
        except Exception as e:
            return f"Failed to send message: {e}"

    def get_inbox(self):
        return self.inbox

    def get_sent_items(self):
        return self.sent_items

    def clear_inbox(self):
        self.inbox = []
        return "Inbox cleared."

    def clear_sent_items(self):
        self.sent_items = []
        return "Sent items cleared."

class ClockWidget(Static):
    time_display = var(time.strftime("%H:%M:%S"))

    def on_mount(self) -> None:
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        self.time_display = time.strftime("%H:%M:%S")

    def render(self) -> str:
        return f"Clock: {self.time_display}"

class WeatherWidget(Static):
    weather_data = var("Loading weather...")

    def on_mount(self) -> None:
        self.update_weather()
        self.set_interval(60 * 15, self.update_weather) # Update every 15 minutes

    async def update_weather(self) -> None:
        self.weather_data = await get_weather()

    def render(self) -> str:
        return self.weather_data

class NewsWidget(Static):
    news_data = var("Loading news...")

    def on_mount(self) -> None:
        self.update_news()
        self.set_interval(60 * 30, self.update_news) # Update every 30 minutes

    async def update_news(self) -> None:
        self.news_data = await get_news()

    def render(self) -> str:
        return self.news_data

class CalculatorWidget(Static):
    def render(self) -> str:
        return "Calculator Widget (Click to open app)"

class MazeWidget(Static):
    def render(self) -> str:
        return "Maze Widget (Click to open app)"

class BaseScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Footer()
        yield from self.body() # Placeholder for screen-specific content

    def body(self) -> ComposeResult:
        # This method should be overridden by subclasses
        yield Static("Default Body Content")

class ZeldaTUIOS(App):
    CSS_PATH = "zelda.css"
    TITLE = "Zelda TUI OS"
    SUB_TITLE = "A Textual-based OS in your terminal"

    # Global state for widgets
    enabled_widgets = {
        "clock": True,
        "weather": True,
        "news": True,
        "calculator": False,
        "maze": False,
    }

    def __init__(self): # Removed mail_service parameter
        super().__init__()
        # Initialize MailService using environment variables
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = os.getenv("SMTP_PORT")
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")
        sender_email = os.getenv("SENDER_EMAIL")

        if all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
            self.mail_service = MailService(
                smtp_server, smtp_port, smtp_username, smtp_password, sender_email
            )
        else:
            self.mail_service = None
            self.log("MailService not fully configured in .env. Mail functionality may be limited.")

    def compose(self) -> ComposeResult:
        # The app will start with the DashboardScreen
        yield DashboardScreen()

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
        elif button_id == "chess_game":
            self.push_screen(ChessScreen())
        elif button_id == "mail_service":
            self.push_screen(MailScreen())
        elif button_id == "music_player_app":
            self.push_screen(MusicPlayerScreen())
        elif button_id == "clock_app":
            self.push_screen(ClockAppScreen())
        elif button_id == "settings_app":
            self.push_screen(SettingsScreen())
        elif button_id == "exit":
            self.exit()

# Rename MainMenu to DashboardScreen
class DashboardScreen(BaseScreen): # Renamed from MainMenu
    BINDINGS = [
        Binding("enter", "press_focused_button", "Select"),
        Binding("space", "press_focused_button", "Select"),
    ]

    async def on_mount(self) -> None:
        pass # No specific mount logic for dashboard itself, widgets handle their own updates

    def body(self) -> ComposeResult:
        yield Static("Zelda TUI OS - Dashboard", id="dashboard_test_message", classes="dashboard_message")
        yield Horizontal(
            Vertical(
                ClockWidget(id="dashboard_clock_widget") if self.app.enabled_widgets["clock"] else Static(""),
                WeatherWidget(id="dashboard_weather_widget") if self.app.enabled_widgets["weather"] else Static(""),
                NewsWidget(id="dashboard_news_widget") if self.app.enabled_widgets["news"] else Static(""),
                CalculatorWidget(id="dashboard_calculator_widget") if self.app.enabled_widgets["calculator"] else Static(""),
                MazeWidget(id="dashboard_maze_widget") if self.app.enabled_widgets["maze"] else Static(""),
                id="dashboard_widgets"
            ),
            Vertical(
                Button("File Browser", id="file_browser"),
                Button("Calculator", id="calculator"),
                Button("System Info", id="system_info"),
                Button("Maze Game", id="maze_game"),
                Button("Nano Editor", id="nano_editor"),
                Button("Web Browser", id="web_browser"),
                Button("Pomodoro Timer", id="pomodoro_timer"),
                Button("Backgrounds", id="backgrounds"),
                Button("Chess Game", id="chess_game"),
                Button("Mail Service", id="mail_service"),
                Button("Music Player", id="music_player_app"),
                Button("Clock App", id="clock_app"),
                Button("Settings", id="settings_app"),
                Button("Exit", id="exit"),
                id="main_menu_buttons"
            ),
            id="dashboard_container"
        )

    def action_press_focused_button(self) -> None:
        focused_widget = self.app.focused
        if isinstance(focused_widget, Button):
            focused_widget.press()

class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Settings", id="settings_title")
        yield Static("Toggle Widgets:")
        for widget_name, is_enabled in self.app.enabled_widgets.items():
            yield Button(f"{widget_name.capitalize()} {'(ON)' if is_enabled else '(OFF)'}", id=f"toggle_widget_{widget_name}")
        yield Button("Back", id="back_settings")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_settings":
            self.app.pop_screen()
        elif event.button.id.startswith("toggle_widget_"):
            widget_name = event.button.id[len("toggle_widget_"):]
            self.app.enabled_widgets[widget_name] = not self.app.enabled_widgets[widget_name]
            self.refresh_compose()
            # Find the DashboardScreen and refresh it
            # Refresh the dashboard screen to reflect widget changes
            self.app.pop_screen() # Pop current settings screen
            self.app.push_screen(DashboardScreen()) # Push a new dashboard screen to re-compose

    def refresh_compose(self):
        # Clear existing content and recompose
        for widget in self.query("Button, Static"): # Clear all buttons and statics
            widget.remove()
        self.compose() # Re-run compose to update content based on current_view

class ChessScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.chess_board = ChessBoard()
        self.move_input = ""

    def body(self) -> ComposeResult:
        yield Static("Chess Game", id="chess_title")
        yield Static(self.chess_board.display(), id="chess_board_display")
        yield Static(self.chess_board.get_status(), id="chess_status")
        yield Input(placeholder="Enter move (e.g., e2e4)", id="move_input")
        yield Horizontal(
            Button("Make Move", id="make_move"),
            Button("Back", id="back")
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "make_move":
            self.move_input = self.query_one("#move_input", Input).value
            if self.move_input:
                result_message = self.chess_board.make_move(self.move_input)
                self.chess_board.switch_player() # For simple turn-taking
                self.query_one("#chess_board_display", Static).update(self.chess_board.display())
                self.query_one("#chess_status", Static).update(f"{self.chess_board.get_status()} {result_message}")
                self.query_one("#move_input", Input).value = "" # Clear input
            else:
                self.query_one("#chess_status", Static).update("Please enter a move.")

class MazeGameScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.maze = self.load_random_maze()
        self.player_pos = self.find_start()
        self.message = "Find the 'E' to exit!"

    def load_random_maze(self):
        return random.choice(MAZES)

    def find_start(self):
        for r, row in enumerate(self.maze):
            for c, char in enumerate(row):
                if char == 'S':
                    return [r, c]
        return [1, 1] # Default if 'S' not found

    def body(self) -> ComposeResult:
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
        yield Button("New Maze", id="new_maze")
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "new_maze":
            self.maze = self.load_random_maze()
            self.player_pos = self.find_start()
            self.message = "Find the 'E' to exit!"
            self.update_maze_display()
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

class MailScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.current_view = "compose" # "compose", "inbox", "sent"
        self.message = ""

    def body(self) -> ComposeResult:
        yield Static("Mail Service", id="mail_title")
        yield Horizontal(
            Button("Compose", id="view_compose", classes="mail_nav_button"),
            Button("Inbox", id="view_inbox", classes="mail_nav_button"),
            Button("Sent", id="view_sent", classes="mail_nav_button"),
        )
        yield Static(self.message, id="mail_message")

        if self.current_view == "compose":
            yield Input(placeholder="Recipient Email", id="mail_recipient")
            yield Input(placeholder="Subject", id="mail_subject")
            yield Input(placeholder="Body", id="mail_body", classes="mail_body_input")
            yield Button("Send Email", id="send_email")
        elif self.current_view == "inbox":
            if self.app.mail_service and self.app.mail_service.get_inbox():
                inbox_content = "\n".join([
                    f"From: {msg['from']}, Subject: {msg['subject']}, Time: {msg['timestamp']}\nBody: {msg['body']}"
                    for msg in self.app.mail_service.get_inbox()
                ])
                yield ScrollableContainer(Static(inbox_content, id="inbox_display"))
            else:
                yield Static("Inbox is empty or Mail Service not configured.")
            yield Button("Clear Inbox", id="clear_inbox")
        elif self.current_view == "sent":
            if self.app.mail_service and self.app.mail_service.get_sent_items():
                sent_content = "\n".join([
                    f"To: {msg['to']}, Subject: {msg['subject']}, Time: {msg['timestamp']}\nBody: {msg['body']}"
                    for msg in self.app.mail_service.get_sent_items()
                ])
                yield ScrollableContainer(Static(sent_content, id="sent_display"))
            else:
                yield Static("Sent items is empty or Mail Service not configured.")
            yield Button("Clear Sent Items", id="clear_sent_items")

        yield Button("Back", id="back_mail")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_mail":
            self.app.pop_screen()
        elif event.button.id.startswith("view_"):
            self.current_view = event.button.id[len("view_"):]
            self.message = ""
            self.refresh_compose()
        elif event.button.id == "send_email":
            if self.app.mail_service:
                recipient = self.query_one("#mail_recipient", Input).value
                subject = self.query_one("#mail_subject", Input).value
                body = self.query_one("#mail_body", Input).value
                if recipient and subject and body:
                    self.message = self.app.mail_service.send_message(recipient, subject, body)
                    self.query_one("#mail_recipient", Input).value = ""
                    self.query_one("#mail_subject", Input).value = ""
                    self.query_one("#mail_body", Input).value = ""
                else:
                    self.message = "Please fill in all fields."
            else:
                self.message = "Mail Service not configured. Check .env file."
            self.query_one("#mail_message", Static).update(self.message)
        elif event.button.id == "clear_inbox":
            if self.app.mail_service:
                self.message = self.app.mail_service.clear_inbox()
            else:
                self.message = "Mail Service not configured."
            self.refresh_compose()
        elif event.button.id == "clear_sent_items":
            if self.app.mail_service:
                self.message = self.app.mail_service.clear_sent_items()
            else:
                self.message = "Mail Service not configured."
            self.refresh_compose()

    def refresh_compose(self):
        for widget in self.query("Static, Input, Button, ScrollableContainer"):
            widget.remove()
        self.compose()

class MusicPlayerScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.current_song = "No song loaded"
        self.playlist = ["Song A - Artist 1", "Song B - Artist 2", "Song C - Artist 3"]
        self.current_song_index = 0

    def body(self) -> ComposeResult:
        yield Static("Music Player (Simulated)", id="music_title")
        yield Static(f"Now Playing: {self.current_song}", id="current_song_display")
        yield Horizontal(
            Button("Play", id="play_music"),
            Button("Pause", id="pause_music"),
            Button("Stop", id="stop_music"),
            Button("Next", id="next_song"),
            Button("Previous", id="prev_song"),
        )
        yield Static("Playlist:", id="playlist_header")
        yield ScrollableContainer(Static("\n".join(self.playlist), id="playlist_display"))
        yield Button("Back", id="back_music")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_music":
            self.app.pop_screen()
        elif event.button.id == "play_music":
            if not self.is_playing:
                self.is_playing = True
                self.current_song = self.playlist[self.current_song_index]
                self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} (Playing)")
        elif event.button.id == "pause_music":
            if self.is_playing:
                self.is_playing = False
                self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} (Paused)")
        elif event.button.id == "stop_music":
            self.is_playing = False
            self.current_song = "No song loaded"
            self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song}")
        elif event.button.id == "next_song":
            self.current_song_index = (self.current_song_index + 1) % len(self.playlist)
            self.current_song = self.playlist[self.current_song_index]
            self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} {'(Playing)' if self.is_playing else ''}")
        elif event.button.id == "prev_song":
            self.current_song_index = (self.current_song_index - 1 + len(self.playlist)) % len(self.playlist)
            self.current_song = self.playlist[self.current_song_index]
            self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} {'(Playing)' if self.is_playing else ''}")

class ClockAppScreen(BaseScreen): # Renamed from ClockScreen to avoid confusion with ClockWidget
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    live_time = var(time.strftime("%H:%M:%S %A %d %b %Y"))

    def on_mount(self) -> None:
        self.set_interval(1, self.update_live_time)

    def update_live_time(self) -> None:
        self.live_time = time.strftime("%H:%M:%S %A %d %b %Y")

    def watch_live_time(self, live_time: str) -> None:
        self.query_one("#full_clock_display", Static).update(live_time)

    def body(self) -> ComposeResult:
        yield Static("Clock App", id="clock_app_title")
        yield Static(self.live_time, id="full_clock_display")
        yield Button("Back", id="back_clock_app")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_clock_app":
            self.app.pop_screen()

class NanoEditorScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self, path=None):
        super().__init__()
        self.path = path
        self.content = ""
        if self.path and os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.content = f.read()

    def body(self) -> ComposeResult:
        yield Static(f"Editing: {self.path or 'New File'}", id="editor_status")
        yield Input(value=self.content, placeholder="Start typing...", id="editor_input", classes="editor")
        if not self.path:
            yield Input(placeholder="Enter file path to save as...", id="save_path_input")
        yield Horizontal(
            Button("Save", id="save_file"),
            Button("Back", id="back")
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "save_file":
            new_content = self.query_one("#editor_input", Input).value
            save_path = self.path
            if not save_path:
                save_path = self.query_one("#save_path_input", Input).value

            if save_path:
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "w") as f:
                        f.write(new_content)
                    self.query_one("#editor_status", Static).update(f"Saved: {save_path}")
                    self.path = save_path # Update path if it was a new file
                except Exception as e:
                    self.query_one("#editor_status", Static).update(f"Error saving file: {e}")
            else:
                self.query_one("#editor_status", Static).update("Please specify a file path to save.")

class WebBrowserScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.url = ""

    def body(self) -> ComposeResult:
        yield Static("TUI Web Browser (Limited Functionality)", id="browser_status")
        yield Input(placeholder="Enter URL (e.g., example.com)", id="url_input")
        yield Button("Go", id="go_button")
        yield ScrollableContainer(Static("", id="browser_content"))
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
                    self.query_one("#browser_status", Static).update(f"Fetching: {display_url}")
                    response = requests.get(display_url, timeout=5) # Add a timeout
                    self.query_one("#browser_content", Static).update(response.text)
                    self.query_one("#browser_status", Static).update(f"Displaying: {display_url}")
                except requests.exceptions.RequestException as e:
                    self.query_one("#browser_content", Static).update(f"Error fetching URL: {e}")
                    self.query_one("#browser_status", Static).update("Error fetching URL.")
                except Exception as e:
                    self.query_one("#browser_content", Static).update(f"An unexpected error occurred: {e}")
                    self.query_one("#browser_status", Static).update("An unexpected error occurred.")
            else:
                self.query_one("#browser_content", Static).update("Please enter a URL.")
                self.query_one("#browser_status", Static).update("TUI Web Browser (Limited Functionality)")

class MusicPlayerScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.is_playing = False
        self.current_song = "No song loaded"
        self.playlist = ["Song A - Artist 1", "Song B - Artist 2", "Song C - Artist 3"]
        self.current_song_index = 0

    def body(self) -> ComposeResult:
        yield Static("Music Player (Simulated)", id="music_title")
        yield Static(f"Now Playing: {self.current_song}", id="current_song_display")
        yield Horizontal(
            Button("Play", id="play_music"),
            Button("Pause", id="pause_music"),
            Button("Stop", id="stop_music"),
            Button("Next", id="next_song"),
            Button("Previous", id="prev_song"),
        )
        yield Static("Playlist:", id="playlist_header")
        yield ScrollableContainer(Static("\n".join(self.playlist), id="playlist_display"))
        yield Button("Back", id="back_music")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_music":
            self.app.pop_screen()
        elif event.button.id == "play_music":
            if not self.is_playing:
                self.is_playing = True
                self.current_song = self.playlist[self.current_song_index]
                self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} (Playing)")
        elif event.button.id == "pause_music":
            if self.is_playing:
                self.is_playing = False
                self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} (Paused)")
        elif event.button.id == "stop_music":
            self.is_playing = False
            self.current_song = "No song loaded"
            self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song}")
        elif event.button.id == "next_song":
            self.current_song_index = (self.current_song_index + 1) % len(self.playlist)
            self.current_song = self.playlist[self.current_song_index]
            self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} {'(Playing)' if self.is_playing else ''}")
        elif event.button.id == "prev_song":
            self.current_song_index = (self.current_song_index - 1 + len(self.playlist)) % len(self.playlist)
            self.current_song = self.playlist[self.current_song_index]
            self.query_one("#current_song_display", Static).update(f"Now Playing: {self.current_song} {'(Playing)' if self.is_playing else ''}")

class ClockAppScreen(BaseScreen): # Renamed from ClockScreen to avoid confusion with ClockWidget
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    live_time = var(time.strftime("%H:%M:%S %A %d %b %Y"))

    def on_mount(self) -> None:
        self.set_interval(1, self.update_live_time)

    def update_live_time(self) -> None:
        self.live_time = time.strftime("%H:%M:%S %A %d %b %Y")

    def watch_live_time(self, live_time: str) -> None:
        self.query_one("#full_clock_display", Static).update(live_time)

    def body(self) -> ComposeResult:
        yield Static("Clock App", id="clock_app_title")
        yield Static(self.live_time, id="full_clock_display")
        yield Button("Back", id="back_clock_app")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_clock_app":
            self.app.pop_screen()

class NanoEditorScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self, path=None):
        super().__init__()
        self.path = path
        self.content = ""
        if self.path and os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.content = f.read()

    def body(self) -> ComposeResult:
        yield Static(f"Editing: {self.path or 'New File'}", id="editor_status")
        yield Input(value=self.content, placeholder="Start typing...", id="editor_input", classes="editor")
        if not self.path:
            yield Input(placeholder="Enter file path to save as...", id="save_path_input")
        yield Horizontal(
            Button("Save", id="save_file"),
            Button("Back", id="back")
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "save_file":
            new_content = self.query_one("#editor_input", Input).value
            save_path = self.path
            if not save_path:
                save_path = self.query_one("#save_path_input", Input).value

            if save_path:
                try:
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                    with open(save_path, "w") as f:
                        f.write(new_content)
                    self.query_one("#editor_status", Static).update(f"Saved: {save_path}")
                    self.path = save_path # Update path if it was a new file
                except Exception as e:
                    self.query_one("#editor_status", Static).update(f"Error saving file: {e}")
            else:
                self.query_one("#editor_status", Static).update("Please specify a file path to save.")

class WebBrowserScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.url = ""

    def body(self) -> ComposeResult:
        yield Static("TUI Web Browser (Limited Functionality)", id="browser_status")
        yield Input(placeholder="Enter URL (e.g., example.com)", id="url_input")
        yield Button("Go", id="go_button")
        yield ScrollableContainer(Static("", id="browser_content"))
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
                    self.query_one("#browser_status", Static).update(f"Fetching: {display_url}")
                    response = requests.get(display_url, timeout=5) # Add a timeout
                    
                    # Convert HTML to Markdown for better TUI display
                    h = html2text.HTML2Text()
                    h.ignore_links = False
                    h.ignore_images = True
                    markdown_content = h.handle(response.text)
                    
                    self.query_one("#browser_content", Static).update(markdown_content)
                    self.query_one("#browser_status", Static).update(f"Displaying: {display_url}")
                except requests.exceptions.RequestException as e:
                    self.query_one("#browser_content", Static).update(f"Error fetching URL: {e}\n\nNote: A full TUI web browser is a complex feature requiring a dedicated rendering engine. This is a placeholder. Ensure 'html2text' is installed via 'pip install html2text'.")
                    self.query_one("#browser_status", Static).update("Error fetching URL.")
                except Exception as e:
                    self.query_one("#browser_content", Static).update(f"An unexpected error occurred: {e}\n\nNote: A full TUI web browser is a complex feature requiring a dedicated rendering engine. This is a placeholder. Ensure 'html2text' is installed via 'pip install html2text'.")
                    self.query_one("#browser_status", Static).update("An unexpected error occurred.")
            else:
                self.query_one("#browser_content", Static).update("Please enter a URL.")
                self.query_one("#browser_status", Static).update("TUI Web Browser (Limited Functionality)")

class PomodoroTimerScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.timer_running = False
        self.time_left = 25 * 60  # 25 minutes
        self.timer_thread = None

    def body(self) -> ComposeResult:
        mins, secs = divmod(self.time_left, 60)
        yield Static(f"Pomodoro Timer: {mins:02d}:{secs:02d}", id="timer_display")
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
        elif event.button.id == "stop":
            self.timer_running = False
        elif event.button.id == "reset":
            self.timer_running = False
            self.time_left = 25 * 60
            self.update_timer_display()
        elif event.button.id == "back":
            self.timer_running = False
            self.app.pop_screen()

    def run_timer(self):
        while self.timer_running and self.time_left > 0:
            time.sleep(1)
            self.time_left -= 1
            self.call_from_thread(self.update_timer_display) # Use call_from_thread for UI updates

    def update_timer_display(self):
        mins, secs = divmod(self.time_left, 60)
        self.query_one("#timer_display", Static).update(f"Pomodoro Timer: {mins:02d}:{secs:02d}")

class BackgroundSelectorScreen(BaseScreen):
    def body(self) -> ComposeResult:
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
            self.app.query_one("#dashboard_container").styles.background = "black"
            self.query_one(Static).update("Background set to Default.")
        elif event.button.id == "bg_blue":
            self.app.query_one("Header").styles.background = "darkblue"
            self.app.query_one("Footer").styles.background = "darkblue"
            self.app.query_one("#dashboard_container").styles.background = "blue"
            self.query_one(Static).update("Background set to Blue Theme.")
        elif event.button.id == "bg_green":
            self.app.query_one("Header").styles.background = "darkgreen"
            self.app.query_one("Footer").styles.background = "darkgreen"
            self.app.query_one("#dashboard_container").styles.background = "green"
            self.query_one(Static).update("Background set to Green Theme.")


class SystemInfoScreen(BaseScreen):
    def body(self) -> ComposeResult:
        sysinfo = f"OS: {platform.system()} {platform.release()}\n"
        sysinfo += f"Python: {platform.python_version()}\n"
        sysinfo += f"Machine: {platform.machine()}\n"
        sysinfo += f"Processor: {platform.processor()}\n"
        yield Static(sysinfo)
        yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()

class FileBrowserScreen(BaseScreen):
    def __init__(self, path=None):
        super().__init__()
        self.path = path or os.getcwd()

    def body(self) -> ComposeResult:
        yield Static(f"Current Directory: {self.path}")
        yield Button("..", id="parent_dir") # Button to go up one directory
        yield Button("New File", id="new_file") # Button to create a new file

        try:
            items = os.listdir(self.path)
            # Sort directories first, then files, filtering out dotfiles/dotdirs
            dirs = sorted([item for item in items if os.path.isdir(os.path.join(self.path, item)) and not item.startswith('.')])
            files = sorted([item for item in items if os.path.isfile(os.path.join(self.path, item)) and not item.startswith('.')])

            for item in dirs:
                yield Button(f"DIR: {item}", id=f"dir_{item}")
            for item in files:
                # Replace dots with hyphens for valid Textual IDs
                safe_item_id = item.replace('.', '-')
                yield Button(f"FILE: {item}", id=f"file_{safe_item_id}")
        except PermissionError:
            yield Static("Permission denied to access this directory.", id="file_browser_status")
        except FileNotFoundError:
            yield Static("Directory not found.", id="file_browser_status")
        except Exception as e:
            yield Static(f"Error: {e}", id="file_browser_status")

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
        elif event.button.id == "new_file":
            self.app.push_screen(NanoEditorScreen()) # Open Nano Editor for a new file
        elif event.button.id.startswith("file_"):
            # Reconstruct original file name from safe ID
            safe_file_id = event.button.id[5:]
            # Assuming original file names might have dots, this is a simplification.
            # A more robust solution might store original names in a dictionary.
            # For now, we'll try to find the original name from the directory listing.
            original_file_name = None
            for item in os.listdir(self.path):
                if os.path.isfile(os.path.join(self.path, item)) and item.replace('.', '-') == safe_file_id:
                    original_file_name = item
                    break
            
            if original_file_name:
                self.app.push_screen(NanoEditorScreen(path=os.path.join(self.path, original_file_name)))
            else:
                self.query_one("#file_browser_status", Static).update(f"Error: Could not find original file for ID {safe_file_id}")

    def clear_screen(self):
        for widget in self.query():
            widget.remove()

class CalculatorScreen(BaseScreen):
    def __init__(self):
        super().__init__()
        self.expression = ""

    def body(self) -> ComposeResult:
        yield Input(value=self.expression, placeholder="Enter expression...", id="expression_input")
        yield Static("Result: ", id="result_display")
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
            self.query_one("#expression_input", Input).value = ""
            self.query_one("#result_display", Static).update("Result: ")
        elif button_id == "equals":
            try:
                # Evaluate the expression
                result = str(eval(self.expression))
                self.query_one("#result_display", Static).update(f"Result: {result}")
                self.expression = result # Set expression to result for chained operations
                self.query_one("#expression_input", Input).value = self.expression
            except Exception:
                self.query_one("#result_display", Static).update("Result: Error")
                self.expression = "" # Clear expression on error
                self.query_one("#expression_input", Input).value = ""
        else:
            # Append the appropriate character to the expression
            if button_id.startswith("btn_"):
                char_to_add = button_id[4:]
                if char_to_add == "divide": char_to_add = "/"
                elif char_to_add == "multiply": char_to_add = "*"
                elif char_to_add == "subtract": char_to_add = "-"
                elif char_to_add == "add": char_to_add = "+"
                elif char_to_add == "dot": char_to_add = "."
                self.expression += char_to_add
            self.query_one("#expression_input", Input).value = self.expression

if __name__ == "__main__":
    ZeldaTUIOS().run()
