import os
import json
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Header, Footer, Input, Label, ListView, ListItem
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual import events
from datetime import datetime, timedelta
import psutil
import subprocess
import calendar
from textual.screen import Screen

load_dotenv()

CONFIG_DIR = "users"
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

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
            app.screen.mount(bar)
        except Exception:
            app.mount(bar)
    def remove_bar():
        try:
            bar.remove()
        except Exception:
            pass
    app.set_timer(2.5, remove_bar)

# --- Notification Center ---
class NotificationCenter(Static):
    def on_mount(self):
        self.notifications = self.app.notifications
        self.refresh()
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Notification Center[/]")
        for n in self.app.notifications:
            yield Label(f"[{n['style']}]• {n['message']}")
        yield Button("Clear All", id="clearall")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "clearall":
            self.app.notifications = []
            self.refresh()

# --- Desktop Shortcuts/Favorites ---
class DesktopShortcut(Button):
    def __init__(self, widget_name, icon, *args, **kwargs):
        super().__init__(f"{icon} {widget_name}", id=f"shortcut_{widget_name.lower()}", *args, **kwargs)
        self.widget_name = widget_name
        self.icon = icon
    def on_button_pressed(self, event: Button.Pressed):
        self.app.open_favorite(self.widget_name)

# --- Demo Widgets ---
class ClosableWidget(Container):
    dragging = reactive(False)
    resizing = reactive(False)
    offset_x = reactive(0)
    offset_y = reactive(0)
    resize_start_x = reactive(0)
    resize_start_y = reactive(0)
    pos_x = reactive(0)
    pos_y = reactive(0)
    width = reactive(30)
    height = reactive(5)
    minimized = reactive(False)
    maximized = reactive(False)
    def __init__(self, content_widget, title, app_ref, pos_x=0, pos_y=0, width=30, height=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content_widget = content_widget
        self.title = title
        self.app_ref = app_ref
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.width = width
        self.height = height
        self.styles.width = self.width
        self.styles.height = self.height
        self.styles.offset = (self.pos_x, self.pos_y)
        self.styles.display = "block"
    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label(f"[b]{self.title}", id="titlebar"),
            Button("_", id="minbtn"),
            Button("⬜", id="maxbtn"),
            Button("✖", id="closebtn"),
            id="titlebarrow"
        )
        if not self.minimized:
            yield self.content_widget
            yield Button("⤡", id="resize_handle", classes="resize-handle")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "closebtn":
            self.app_ref.remove_widget(self)
        elif event.button.id == "minbtn":
            self.minimized = True
            self.styles.display = "none"
            self.app_ref.update_taskbar()
        elif event.button.id == "maxbtn":
            if not self.maximized:
                self.styles.width = "80%"
                self.styles.height = "80%"
                self.styles.offset = (0, 0)
                self.maximized = True
            else:
                self.styles.width = self.width
                self.styles.height = self.height
                self.styles.offset = (self.pos_x, self.pos_y)
                self.maximized = False
            self.refresh()
    def on_mouse_down(self, event: events.MouseDown) -> None:
        if getattr(event.control, "id", None) == "titlebar":
            self.dragging = True
            self.offset_x = event.x - self.pos_x
            self.offset_y = event.y - self.pos_y
        elif getattr(event.control, "id", None) == "resize_handle":
            self.resizing = True
            self.resize_start_x = event.x
            self.resize_start_y = event.y
    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.dragging = False
        self.resizing = False
        self.app_ref.save_layout()
    def on_mouse_move(self, event: events.MouseMove) -> None:
        if self.dragging and not self.maximized:
            self.pos_x = max(0, event.x - self.offset_x)
            self.pos_y = max(0, event.y - self.offset_y)
            self.styles.offset = (self.pos_x, self.pos_y)
            self.refresh()
        elif self.resizing and not self.maximized:
            new_width = max(18, self.width + (event.x - self.resize_start_x))
            new_height = max(4, self.height + (event.y - self.resize_start_y))
            self.width = new_width
            self.height = new_height
            self.styles.width = self.width
            self.styles.height = self.height
            self.refresh()

class ClockWidget(Static):
    def on_mount(self):
        self.set_interval(1, self.refresh_clock)
        self.refresh_clock()
    def refresh_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update(f"[b][#00ffae]🕒 {now}[/]")

class SysMonWidget(Static):
    def on_mount(self):
        self.set_interval(1, self.refresh_sysmon)
        self.refresh_sysmon()
    def refresh_sysmon(self):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        self.update(f"[b][#ffd700]CPU:[/] {cpu}%  [#ffd700]MEM:[/] {mem}%  [#ffd700]DISK:[/] {disk}%")

class NotesWidget(Static):
    notes = reactive("")
    def compose(self) -> ComposeResult:
        yield Label("[b][#ff00c8]Notes[/]")
        yield Input(placeholder="Type a note and press Enter...", id="note_input")
        yield Static(self.notes, id="note_display")
    def on_mount(self):
        self.notes = load_notes(self.app.username)
    def on_input_submitted(self, event: Input.Submitted):
        self.notes += event.value + "\n"
        self.query_one("#note_display", Static).update(self.notes)
        event.input.value = ""
        save_notes(self.app.username, self.notes)

class FileExplorerWidget(Static):
    cwd = reactive(os.getcwd())
    def compose(self) -> ComposeResult:
        yield Label(f"[b][#00ffae]File Explorer[/] [dim]{self.cwd}[/]")
        files = os.listdir(self.cwd)
        lv = ListView(*[ListItem(Label(f"[b]{f}")) for f in files], id="filelist")
        yield lv
        yield Static("[dim]Select a file to view its contents.[/]", id="fileview")
        yield Button("New File", id="newfile")
        yield Button("New Folder", id="newfolder")
        yield Button("Delete", id="delete")
        yield Button("Rename", id="rename")
    def on_list_view_selected(self, event: ListView.Selected):
        selected = event.item.query_one(Label).renderable.plain
        path = os.path.join(self.cwd, selected)
        if os.path.isdir(path):
            self.cwd = path
            self.refresh()
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(5000)
                self.query_one("#fileview", Static).update(f"[dim]{selected}[/]\n[white]{content}[/]")
            except Exception as e:
                self.query_one("#fileview", Static).update(f"[red]Error opening file:[/] {e}")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "newfile":
            fname = f"newfile_{datetime.now().strftime('%H%M%S')}.txt"
            path = os.path.join(self.cwd, fname)
            with open(path, "w") as f:
                f.write("")
            notify(self.app, f"Created file: {fname}", "success")
            self.refresh()
        elif event.button.id == "newfolder":
            fname = f"newfolder_{datetime.now().strftime('%H%M%S')}"
            path = os.path.join(self.cwd, fname)
            os.makedirs(path)
            notify(self.app, f"Created folder: {fname}", "success")
            self.refresh()
        elif event.button.id == "delete":
            lv = self.query_one("#filelist", ListView)
            if lv.index is not None:
                selected = lv.children[lv.index].query_one(Label).renderable.plain
                path = os.path.join(self.cwd, selected)
                try:
                    if os.path.isdir(path):
                        os.rmdir(path)
                    else:
                        os.remove(path)
                    notify(self.app, f"Deleted: {selected}", "warning")
                except Exception as e:
                    notify(self.app, f"Error: {e}", "error")
                self.refresh()
        elif event.button.id == "rename":
            lv = self.query_one("#filelist", ListView)
            if lv.index is not None:
                selected = lv.children[lv.index].query_one(Label).renderable.plain
                path = os.path.join(self.cwd, selected)
                newname = f"renamed_{selected}"
                newpath = os.path.join(self.cwd, newname)
                try:
                    os.rename(path, newpath)
                    notify(self.app, f"Renamed to: {newname}", "info")
                except Exception as e:
                    notify(self.app, f"Error: {e}", "error")
                self.refresh()

class CalculatorWidget(Static):
    expr = reactive("")
    result = reactive("")
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Calculator[/]")
        yield Input(placeholder="Enter expression and press Enter...", id="calc_input")
        yield Static(self.result, id="calc_result")
    def on_input_submitted(self, event: Input.Submitted):
        self.expr = event.value
        try:
            self.result = str(eval(self.expr, {}, {}))
        except Exception as e:
            self.result = f"Error: {e}"
        self.query_one("#calc_result", Static).update(self.result)
        event.input.value = ""

class TerminalWidget(Static):
    output = reactive("")
    def compose(self) -> ComposeResult:
        yield Label("[b][#00ffae]Terminal[/]")
        yield Input(placeholder="Enter command and press Enter...", id="term_input")
        yield Static(self.output, id="term_output")
    def on_input_submitted(self, event: Input.Submitted):
        cmd = event.value
        try:
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, encoding="utf-8", timeout=5)
        except Exception as e:
            result = str(e)
        self.output = result
        self.query_one("#term_output", Static).update(self.output)
        event.input.value = ""

# --- Reminders Widget ---
class RemindersWidget(Static):
    reminders = reactive([])
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Reminders[/]")
        yield Input(placeholder="Add reminder: text | YYYY-MM-DD HH:MM", id="reminder_input")
        for r in self.reminders:
            yield Label(f"[b]{r['text']}[/] [dim]{r['time']}[/]")
    def on_mount(self):
        self.reminders = load_reminders(self.app.username)
        self.set_interval(10, self.check_reminders)
    def on_input_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if "|" in val:
            text, tstr = val.split("|", 1)
            try:
                t = datetime.strptime(tstr.strip(), "%Y-%m-%d %H:%M")
                self.reminders.append({"text": text.strip(), "time": t.strftime("%Y-%m-%d %H:%M")})
                save_reminders(self.app.username, self.reminders)
                notify(self.app, f"Reminder set for {t}", "success")
                self.refresh()
            except Exception:
                notify(self.app, "Invalid date/time format!", "error")
        event.input.value = ""
    def check_reminders(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for r in self.reminders:
            if r["time"] == now:
                notify(self.app, f"Reminder: {r['text']}", "warning")

# --- Calendar Widget ---
class CalendarWidget(Static):
    month = reactive(datetime.now().month)
    year = reactive(datetime.now().year)
    events = reactive([])
    def compose(self) -> ComposeResult:
        yield Label(f"[b][#ffd700]Calendar {self.year}-{self.month:02d}[/]")
        cal = calendar.month(self.year, self.month)
        yield Static(f"[white]{cal}[/]")
        yield Input(placeholder="Add event: YYYY-MM-DD | text", id="event_input")
        for e in self.events:
            yield Label(f"[b]{e['date']}[/]: {e['text']}")
        yield Button("Prev Month", id="prev_month")
        yield Button("Next Month", id="next_month")
    def on_mount(self):
        self.events = self.app.calendar_events
    def on_input_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if "|" in val:
            dstr, text = val.split("|", 1)
            self.events.append({"date": dstr.strip(), "text": text.strip()})
            self.app.calendar_events = self.events
            notify(self.app, f"Event added for {dstr.strip()}", "success")
            self.refresh()
        event.input.value = ""
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "prev_month":
            if self.month == 1:
                self.month = 12
                self.year -= 1
            else:
                self.month -= 1
            self.refresh()
        elif event.button.id == "next_month":
            if self.month == 12:
                self.month = 1
                self.year += 1
            else:
                self.month += 1
            self.refresh()

# --- Widget Gallery ---
class WidgetGallery(Static):
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]App Store (Widget Gallery)[/]")
        yield Button("🕒 Clock", id="add_clock")
        yield Button("🖥️ SysMon", id="add_sysmon")
        yield Button("📝 Notes", id="add_notes")
        yield Button("📁 File Explorer", id="add_fileexplorer")
        yield Button("🧮 Calculator", id="add_calc")
        yield Button("💻 Terminal", id="add_terminal")
        yield Button("⏰ Reminders", id="add_reminders")
        yield Button("📅 Calendar", id="add_calendar")
        yield Label("[dim]More widgets coming soon![/]")
    def on_button_pressed(self, event: Button.Pressed):
        widget_map = {
            "add_clock": (ClockWidget, "Clock"),
            "add_sysmon": (SysMonWidget, "SysMon"),
            "add_notes": (NotesWidget, "Notes"),
            "add_fileexplorer": (FileExplorerWidget, "File Explorer"),
            "add_calc": (CalculatorWidget, "Calculator"),
            "add_terminal": (TerminalWidget, "Terminal"),
            "add_reminders": (RemindersWidget, "Reminders"),
            "add_calendar": (CalendarWidget, "Calendar"),
        }
        if event.button.id in widget_map:
            widget_cls, title = widget_map[event.button.id]
            self.app.add_widget(widget_cls(), title)

# --- Custom Taskbar Context Menu ---
class TaskbarMenu(Vertical):
    def __init__(self, app, app_title):
        super().__init__()
        self.app = app
        self.app_title = app_title
        self.mount(Button("Restore", id="restore"))
        self.mount(Button("Minimize", id="minimize"))
        self.mount(Button("Close", id="close"))
    def on_button_pressed(self, event):
        if event.button.id == "restore":
            self.app.restore_app(self.app_title)
        elif event.button.id == "minimize":
            self.app.minimize_app(self.app_title)
        elif event.button.id == "close":
            self.app.close_app(self.app_title)
        self.remove()

# --- Dashboard Container ---
class Dashboard(Vertical):
    def compose(self) -> ComposeResult:
        for app in self.app.open_apps:
            yield app["widget"]

# --- AppLauncherMenu (unchanged except for one-at-a-time logic) ---
class AppLauncherMenu(Horizontal):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self.apps = [
            ("Weather", WeatherWidget, "☁️"),
            ("Time", TimeWidget, "🕒"),
            ("Notes", NotesWidget, "📝"),
            ("File Explorer", FileExplorerWidget, "📁"),
            ("Calculator", CalculatorWidget, "🧮"),
            ("Terminal", TerminalWidget, "💻"),
            ("Reminders", RemindersWidget, "⏰"),
            ("Calendar", CalendarWidget, "📅"),
        ]
    def compose(self) -> ComposeResult:
        for name, _, icon in self.apps:
            safe_id = f"launch_{name.replace(' ', '_')}"
            yield Button(f"{icon} {name}", id=safe_id)
    def on_button_pressed(self, event):
        for name, widget_cls, _ in self.apps:
            safe_id = f"launch_{name.replace(' ', '_')}"
            if event.button.id == safe_id:
                self._app.open_or_focus_app(widget_cls, name)
                self.remove()
                break

# --- Taskbar ---
class Taskbar(Horizontal):
    def compose(self) -> ComposeResult:
        yield Button("🪟", id="os_icon", variant="default")
        for app in self.app.open_apps:
            yield Button(f"{self.app.widget_icon(app['title'])} {app['title']}", id=f"task_{app['title']}", variant="primary" if app['focused'] else "default")
        yield Static(" ", id="spacer")
        yield Static(f"🕒 {self.app.system_time}", id="tray_clock")
        yield Button("🔔", id="tray_notif", variant="default")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "os_icon":
            self.app.show_app_launcher()
        elif event.button.id.startswith("task_"):
            app_title = event.button.id.replace("task_", "")
            self.app.focus_app(app_title)
        elif event.button.id == "tray_notif":
            self.app.add_widget(NotificationCenter(), "Notification Center")
    def on_mouse_down(self, event):
        if event.button == 3 and getattr(event.control, "id", None) and event.control.id.startswith("task_"):
            app_title = event.control.id.replace("task_", "")
            self.app.show_taskbar_menu(app_title, event.control)

# --- Desktop Widget Container ---
class Desktop(Container):
    ascii_art = reactive("")
    background = reactive(THEMES["retro"]["background"])
    def render(self):
        art = self.ascii_art
        bg = self.background
        return f"[on {bg}]{art}"

# --- Time Widget ---
class TimeWidget(Static):
    def on_mount(self):
        self.set_interval(1, self.refresh_time)
        self.refresh_time()
    def refresh_time(self):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self.update(f"[b][#569cd6]🕒 {now}[/]")

# --- Weather Widget (stub, can be expanded with real API) ---
class WeatherWidget(Static):
    def on_mount(self):
        self.set_interval(600, self.refresh_weather)  # Update every 10 min
        self.refresh_weather()
    def refresh_weather(self):
        # For now, just show a static message; can be replaced with real API call
        self.update("[b][#b5d4ff]☁️ 24°C, Mostly Cloudy[/]")

# --- ZeldaCLIOS App (major changes) ---
class ZeldaCLIOS(App):
    CSS_PATH = "zelda.css"
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("ctrl+n", "open_notifcenter", "Notifications"),
        ("ctrl+f", "open_favorites", "Favorites"),
    ]
    background_color = reactive(THEMES["retro"]["background"])
    ascii_art = reactive("")
    running_widgets = reactive(set())
    widget_layouts = reactive([])
    username = reactive("")
    user_theme = reactive("retro")
    favorites = reactive([])
    avatar = reactive(":)")
    notifications = reactive([])
    calendar_events = reactive([])
    open_apps = reactive([])  # List of dicts: {title, widget, focused, minimized}
    focused_app = None
    system_time = reactive("")
    def compose(self) -> ComposeResult:
        yield Dashboard(id="dashboard")
        yield Taskbar(id="taskbar")
        yield Footer()
    def on_mount(self):
        self.dashboard = self.query_one("#dashboard", Dashboard)
        self.open_apps = []
        self.focused_app = None
        self.running_widgets = set()
        self.widget_layouts = []
        self.username = ""
        self.user_theme = "retro"
        self.favorites = []
        self.avatar = ":)"
        self.notifications = []
        self.calendar_events = []
        self.set_interval(1, self.update_system_time)
        self.push_screen(LoginScreen())
        # Always open Weather and Time widgets on startup
        self.open_or_focus_app(WeatherWidget, "Weather")
        self.open_or_focus_app(TimeWidget, "Time")
        notify(self, "ZeldaCLI OS started!", "info")
    def update_system_time(self):
        from datetime import datetime
        self.system_time = datetime.now().strftime("%H:%M:%S")
        self.refresh(layout=True)
    def login(self, username):
        self.username = username
        self.load_layout()
        notify(self, f"Welcome, {username}!", "success")
    def logout(self):
        self.save_layout()
        self.username = ""
        self.running_widgets = set()
        self.widget_layouts = []
        self.favorites = []
        self.avatar = ":)"
        self.desktop.remove_children()
        self.push_screen(LoginScreen())
    def add_widget(self, widget, title, *args, **kwargs):
        self.open_or_focus_app(lambda: widget, title)
    def remove_widget(self, widget):
        self.open_apps = [app for app in self.open_apps if app["widget"] != widget]
        self.update_taskbar()
        self.refresh()
        self.save_layout()
    def focus_app(self, title):
        for app in self.open_apps:
            app["focused"] = (app["title"] == title)
        self.update_taskbar()
        self.refresh()
    def set_background(self, color):
        self.background_color = color
        self.desktop.background = color
        self.save_layout()
        self.refresh()
    def set_ascii_art(self, art_name):
        if art_name in ASCII_ARTS:
            self.desktop.ascii_art = ASCII_ARTS[art_name]
        else:
            self.desktop.ascii_art = ""
        self.save_layout()
        self.refresh()
    def set_theme(self, theme):
        if theme in THEMES:
            self.user_theme = theme
            t = THEMES[theme]
            self.background_color = t["background"]
            self.desktop.background = t["background"]
            self.save_layout()
            self.refresh()
            notify(self, f"Theme set to {theme}", "info")
    def set_avatar(self, avatar):
        self.avatar = avatar
        self.save_layout()
        notify(self, f"Avatar set to {avatar}", "info")
    def save_layout(self):
        if not self.username:
            return
        widgets = []
        for w in self.desktop.children:
            if isinstance(w, ClosableWidget):
                widgets.append({
                    "title": w.title,
                    "pos_x": w.pos_x,
                    "pos_y": w.pos_y,
                    "width": w.width,
                    "height": w.height
                })
        data = {
            "background": self.background_color,
            "ascii_art": self.desktop.ascii_art,
            "widgets": widgets,
            "user_theme": self.user_theme,
            "favorites": self.favorites,
            "avatar": self.avatar,
            "calendar_events": self.calendar_events
        }
        save_config(self.username, data)
    def load_layout(self):
        if not self.username:
            return
        data = load_config(self.username)
        self.desktop.remove_children()
        self.running_widgets = set()
        self.favorites = data.get("favorites", ["Clock", "Notes"])
        self.avatar = data.get("avatar", ":)")
        self.calendar_events = data.get("calendar_events", [])
        if data:
            self.background_color = data.get("background", THEMES[self.user_theme]["background"])
            self.desktop.background = self.background_color
            self.desktop.ascii_art = data.get("ascii_art", "")
            self.user_theme = data.get("user_theme", "retro")
            for w in data.get("widgets", []):
                widget_map = {
                    "Clock": ClockWidget,
                    "SysMon": SysMonWidget,
                    "Notes": NotesWidget,
                    "File Explorer": FileExplorerWidget,
                    "Calculator": CalculatorWidget,
                    "Terminal": TerminalWidget,
                    "Reminders": RemindersWidget,
                    "Calendar": CalendarWidget,
                }
                widget_cls = widget_map.get(w["title"], ClockWidget)
                self.add_widget(widget_cls(), w["title"], w["pos_x"], w["pos_y"], w["width"], w["height"])
        else:
            self.add_widget(ClockWidget(), "Clock")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "clock":
            self.add_widget(ClockWidget(), "Clock")
        elif event.button.id == "sysmon":
            self.add_widget(SysMonWidget(), "SysMon")
        elif event.button.id == "notes":
            self.add_widget(NotesWidget(), "Notes")
        elif event.button.id == "fileexplorer":
            self.add_widget(FileExplorerWidget(), "File Explorer")
        elif event.button.id == "calc":
            self.add_widget(CalculatorWidget(), "Calculator")
        elif event.button.id == "terminal":
            self.add_widget(TerminalWidget(), "Terminal")
        elif event.button.id == "reminders":
            self.add_widget(RemindersWidget(), "Reminders")
        elif event.button.id == "calendar":
            self.add_widget(CalendarWidget(), "Calendar")
        elif event.button.id == "gallery":
            self.add_widget(WidgetGallery(), "App Store")
        elif event.button.id == "notifcenter":
            self.add_widget(NotificationCenter(), "Notification Center")
        elif event.button.id == "theme":
            self.add_widget(ThemeWidget(), "Theme Switcher")
        elif event.button.id == "settings":
            self.add_widget(SettingsWidget(), "Settings")
        elif event.button.id == "logout":
            self.logout()
    def toggle_favorite(self, widget_name):
        if widget_name in self.favorites:
            self.favorites.remove(widget_name)
            notify(self, f"Removed {widget_name} from favorites", "warning")
        else:
            self.favorites.append(widget_name)
            notify(self, f"Added {widget_name} to favorites", "success")
        self.save_layout()
        self.refresh()
    def open_favorite(self, widget_name):
        widget_map = {
            "Clock": ClockWidget,
            "SysMon": SysMonWidget,
            "Notes": NotesWidget,
            "File Explorer": FileExplorerWidget,
            "Calculator": CalculatorWidget,
            "Terminal": TerminalWidget,
            "Reminders": RemindersWidget,
            "Calendar": CalendarWidget,
        }
        widget_cls = widget_map.get(widget_name, ClockWidget)
        self.add_widget(widget_cls(), widget_name)
    def widget_icon(self, widget_name):
        icons = {
            "Clock": "🕒",
            "SysMon": "🖥️",
            "Notes": "📝",
            "File Explorer": "📁",
            "Calculator": "🧮",
            "Terminal": "💻",
            "Reminders": "⏰",
            "Calendar": "📅",
        }
        return icons.get(widget_name, "★")
    def action_open_notifcenter(self):
        self.add_widget(NotificationCenter(), "Notification Center")
    def action_open_favorites(self):
        for fav in self.favorites:
            self.open_favorite(fav)
    def show_taskbar_menu(self, app_title, button):
        menu = TaskbarMenu(self, app_title)
        self.mount(menu, after=button)
    def minimize_app(self, app_title):
        for app in self.open_apps:
            if app["title"] == app_title:
                app["minimized"] = True
                app["widget"].minimized = True
                app["widget"].styles.display = "none"
        self.update_taskbar()
        self.refresh()
    def restore_app(self, app_title):
        for app in self.open_apps:
            if app["title"] == app_title:
                app["minimized"] = False
                app["widget"].minimized = False
                app["widget"].styles.display = "block"
                self.focus_app(app_title)
        self.update_taskbar()
        self.refresh()
    def close_app(self, app_title):
        for app in self.open_apps:
            if app["title"] == app_title:
                self.remove_widget(app["widget"])
                break
        self.update_taskbar()
        self.refresh()
    def update_taskbar(self):
        try:
            taskbar = self.query_one("#taskbar")
            taskbar.refresh()
        except Exception:
            pass
        self.refresh()
    def show_app_launcher(self):
        # Only allow one launcher at a time
        for child in self.children:
            if isinstance(child, AppLauncherMenu):
                child.remove()
        menu = AppLauncherMenu(self)
        self.mount(menu, before="#taskbar")
    def open_or_focus_app(self, widget_cls, title):
        for app in self.open_apps:
            if app["title"] == title:
                self.focus_app(title)
                return
        widget = widget_cls()
        self.open_apps.append({"title": title, "widget": widget, "focused": True, "minimized": False})
        self.focus_app(title)
        self.update_taskbar()
        self.refresh()
        self.save_layout()

if __name__ == "__main__":
    ZeldaCLIOS().run()
