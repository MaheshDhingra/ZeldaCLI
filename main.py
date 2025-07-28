import os
import json
from dotenv import load_dotenv
from textual.app import App, ComposeResult
from textual.widgets import Static, Button, Header, Footer, Input, Label, ListView, ListItem
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive, var
from textual import events
import time
from datetime import datetime, timedelta
import psutil
import subprocess
import calendar
from textual.screen import Screen
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
import platform
import httpx # Added httpx for async HTTP requests
import html # Added html for HTML escaping
from rich.syntax import Syntax # For code display
from rich.text import Text # For rich text display
from textual.binding import Binding # Added Binding import

load_dotenv()

CONFIG_DIR = "users"
if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

THEMES = {
    "retro": {
        "background": "#000080",
        "text": "#00FF00",
        "border": "#FFFF00",
    },
    "modern": {
        "background": "#1E1E1E",
        "text": "#FFFFFF",
        "border": "#007ACC",
    },
    "matrix": {
        "background": "#000000",
        "text": "#00FF41",
        "border": "#00FF41",
    },
}

ASCII_ARTS = {
    "zelda": r"""
  /\\
 /  \\
/____\\
|    |
|____|
""",
    "triforce": r"""
  /\\
 /__\\
/__  __\\
\  /  /
 \/  /
  \/
""",
}

def get_user_config_path(username):
    return os.path.join(CONFIG_DIR, f"{username}.json")

def load_config(username):
    config_path = get_user_config_path(username)
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

def save_config(username, data):
    config_path = get_user_config_path(username)
    with open(config_path, "w") as f:
        json.dump(data, f, indent=4)

def load_notes(username):
    config = load_config(username)
    return config.get("notes", "")

def save_notes(username, notes):
    config = load_config(username)
    config["notes"] = notes
    save_config(username, config)

def load_reminders(username):
    config = load_config(username)
    return config.get("reminders", [])

def save_reminders(username, reminders):
    config = load_config(username)
    config["reminders"] = reminders
    save_config(username, config)

def notify(app_instance, message, style="info"):
    app_instance.notifications.append({"message": message, "style": style})
    app_instance.update_taskbar()
    app_instance.refresh()

class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Container(
            Static("ZeldaCLI OS - Login", id="login_title"),
            Input(placeholder="Username", id="username_input"),
            Input(placeholder="Password (any)", password=True, id="password_input"),
            Button("Login", id="login_button"),
            id="login_container"
        )
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "login_button":
            username = self.query_one("#username_input", Input).value
            # For simplicity, any non-empty username and password works
            if username and self.query_one("#password_input", Input).value:
                self.app.login(username)
                self.app.pop_screen()
            else:
                self.query_one("#login_title", Static).update("Login Failed: Enter username and password")

class SettingsWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Settings[/]")
        yield Button("Change Theme", id="change_theme")
        yield Button("Change ASCII Art", id="change_ascii")
        yield Button("Set Avatar", id="set_avatar")
        yield Button("Manage Favorites", id="manage_favorites")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "change_theme":
            self.app.add_widget(ThemeWidget(), "Theme Switcher")
        elif event.button.id == "change_ascii":
            self.app.add_widget(AsciiArtSelector(), "ASCII Art Selector")
        elif event.button.id == "set_avatar":
            self.app.add_widget(AvatarSelector(), "Avatar Selector")
        elif event.button.id == "manage_favorites":
            self.app.add_widget(FavoritesManager(), "Favorites Manager")

class ThemeWidget(Static):
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Theme Switcher[/]")
        for theme_name in THEMES.keys():
            yield Button(theme_name.capitalize(), id=f"theme_{theme_name}")
    def on_button_pressed(self, event: Button.Pressed):
        theme_name = event.button.id.replace("theme_", "")
        self.app.set_theme(theme_name)

class AsciiArtSelector(Static):
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]ASCII Art Selector[/]")
        yield Button("None", id="ascii_none")
        for art_name in ASCII_ARTS.keys():
            yield Button(art_name.capitalize(), id=f"ascii_{art_name}")
    def on_button_pressed(self, event: Button.Pressed):
        art_name = event.button.id.replace("ascii_", "")
        if art_name == "none":
            self.app.set_ascii_art("")
        else:
            self.app.set_ascii_art(art_name)

class AvatarSelector(Static):
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Avatar Selector[/]")
        yield Input(placeholder="Enter avatar (e.g., :) )", id="avatar_input")
        yield Button("Set Avatar", id="set_avatar_btn")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "set_avatar_btn":
            avatar = self.query_one("#avatar_input", Input).value
            self.app.set_avatar(avatar)

class FavoritesManager(Static):
    def compose(self) -> ComposeResult:
        yield Label("[b][#ffd700]Manage Favorites[/]")
        for widget_name in ["Clock", "SysMon", "Notes", "File Explorer", "Calculator", "Terminal", "Reminders", "Calendar"]:
            is_fav = widget_name in self.app.favorites
            yield Button(f"{widget_name} {'(★)' if is_fav else '(☆)'}", id=f"toggle_fav_{widget_name}")
    def on_button_pressed(self, event: Button.Pressed):
        widget_name = event.button.id.replace("toggle_fav_", "")
        self.app.toggle_favorite(widget_name)
        self.refresh()

class ScrollableContainer(Container):
    pass

class WebBrowserScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]
    url = reactive("https://textual.textualize.io/")
    content = reactive("Loading...")
    status_message = reactive("")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Web Browser", id="browser_title")
        yield Input(placeholder="Enter URL (e.g., https://example.com)", id="url_input", value=self.url)
        yield Button("Go", id="go_button")
        yield ScrollableContainer(Static(self.content, id="browser_content"))
        yield Static(self.status_message, id="browser_status")
        yield Button("Back", id="back_browser")
        yield Footer()

    def on_mount(self) -> None:
        self.fetch_url()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_browser":
            self.app.pop_screen()
        elif event.button.id == "go_button":
            self.url = self.query_one("#url_input", Input).value
            self.fetch_url()

    async def fetch_url(self) -> None:
        self.content = "Loading..."
        self.status_message = f"Fetching {self.url}..."
        self.query_one("#browser_content", Static).update(self.content)
        self.query_one("#browser_status", Static).update(self.status_message)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, follow_redirects=True, timeout=10)
                response.raise_for_status()
                # Basic HTML to text conversion (very simplified)
                # For a real browser, you'd need a more robust HTML parser
                text_content = html.unescape(response.text)
                # Limit content to avoid excessive memory usage
                self.content = text_content[:5000] + ("..." if len(text_content) > 5000 else "")
                self.status_message = f"Loaded {self.url}"
        except httpx.RequestError as e:
            self.content = f"Error: Could not connect to {self.url}. {e}"
            self.status_message = "Connection Error"
        except httpx.HTTPStatusError as e:
            self.content = f"Error: HTTP {e.response.status_code} for {self.url}"
            self.status_message = f"HTTP Error: {e.response.status_code}"
        except Exception as e:
            self.content = f"An unexpected error occurred: {e}"
            self.status_message = "Unknown Error"
        finally:
            self.query_one("#browser_content", Static).update(self.content)
            self.query_one("#browser_status", Static).update(self.status_message)

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

from textual.binding import Binding

class TicTacToeBoard:
    def __init__(self):
        self.board = [' ' for _ in range(9)]
        self.current_player = 'X'
        self.game_over = False
        self.winner = None

    def display(self):
        return (
            f" {self.board[0]} | {self.board[1]} | {self.board[2]} \n"
            "---+---+---\n"
            f" {self.board[3]} | {self.board[4]} | {self.board[5]} \n"
            "---+---+---\n"
            f" {self.board[6]} | {self.board[7]} | {self.board[8]} "
        )

    def make_move(self, position):
        if self.game_over:
            return "Game is over. Start a new game."
        try:
            pos = int(position) - 1
            if 0 <= pos < 9 and self.board[pos] == ' ':
                self.board[pos] = self.current_player
                self.check_game_status()
                if not self.game_over:
                    self.switch_player()
                return "Move successful."
            else:
                return "Invalid move. Position taken or out of bounds."
        except ValueError:
            return "Invalid input. Please enter a number 1-9."

    def switch_player(self):
        self.current_player = 'O' if self.current_player == 'X' else 'X'

    def check_game_status(self):
        winning_combinations = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # Rows
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # Columns
            (0, 4, 8), (2, 4, 6)              # Diagonals
        ]
        for combo in winning_combinations:
            if (self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]]) and self.board[combo[0]] != ' ':
                self.winner = self.board[combo[0]]
                self.game_over = True
                return

        if ' ' not in self.board:
            self.game_over = True
            self.winner = "Draw"

class ChessBoard:
    def __init__(self):
        self.board = self._initialize_board()
        self.current_player = "White" # White starts

    def _initialize_board(self):
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
        self.smtp_port = int(smtp_port)
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.inbox = []
        self.sent_items = []
        self.current_user = sender_email

    def send_message(self, recipient, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
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
        self.set_interval(60 * 15, self.update_weather)

    async def update_weather(self) -> None:
        self.weather_data = await get_weather()

    def render(self) -> str:
        return self.weather_data

class NewsWidget(Static):
    news_data = var("Loading news...")

    def on_mount(self) -> None:
        self.update_news()
        self.set_interval(60 * 30, self.update_news)

    async def update_news(self) -> None:
        self.news_data = await get_news()

    def render(self) -> str:
        return self.news_data

class CalculatorScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]
    expr = reactive("")
    result = reactive("")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Calculator", id="calc_title")
        yield Input(placeholder="Enter expression and press Enter...", id="calc_input")
        yield Static(self.result, id="calc_result")
        yield Button("Calculate", id="calculate_button")
        yield Button("Back", id="back_calc")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_calc":
            self.app.pop_screen()
        elif event.button.id == "calculate_button":
            self.expr = self.query_one("#calc_input", Input).value
            try:
                self.result = str(eval(self.expr, {}, {}))
            except Exception as e:
                self.result = f"Error: {e}"
            self.query_one("#calc_result", Static).update(self.result)
            self.query_one("#calc_input", Input).value = ""

class CalculatorWidget(Static):
    def render(self) -> str:
        return "Calculator Widget (Click to open app)"

class MazeWidget(Static):
    def render(self) -> str:
        return "Maze Widget (Click to open app)"

class TicTacToeWidget(Static):
    def render(self) -> str:
        return "Tic-Tac-Toe Widget (Click to open app)"

class BaseScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Footer()
        yield Static("Default Body Content")

class TicTacToeScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.game = TicTacToeBoard()
        self.message = "Enter position (1-9) to make a move."

    def compose(self) -> ComposeResult:
        yield Static("Tic-Tac-Toe", id="tictactoe_title")
        yield Static(self.game.display(), id="tictactoe_board_display")
        yield Static(self.message, id="tictactoe_message")
        yield Input(placeholder="Enter position (1-9)", id="tictactoe_input")
        yield Horizontal(
            Button("Make Move", id="make_tictactoe_move"),
            Button("New Game", id="new_tictactoe_game"),
            Button("Back", id="back_tictactoe")
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_tictactoe":
            self.app.pop_screen()
        elif event.button.id == "new_tictactoe_game":
            self.game = TicTacToeBoard()
            self.message = "New game started! X to move."
            self.update_display()
        elif event.button.id == "make_tictactoe_move":
            position = self.query_one("#tictactoe_input", Input).value
            if position:
                result = self.game.make_move(position)
                self.message = result
                if self.game.game_over:
                    if self.game.winner == "Draw":
                        self.message = "Game Over: It's a Draw!"
                    elif self.game.winner:
                        self.message = f"Game Over: Player {self.game.winner} wins!"
                self.update_display()
                self.query_one("#tictactoe_input", Input).value = ""
            else:
                self.message = "Please enter a position."
                self.query_one("#tictactoe_message", Static).update(self.message)

    def update_display(self):
        self.query_one("#tictactoe_board_display", Static).update(self.game.display())
        self.query_one("#tictactoe_message", Static).update(self.message)

class ChessScreen(BaseScreen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def __init__(self):
        super().__init__()
        self.chess_board = ChessBoard()
        self.move_input = ""

    def compose(self) -> ComposeResult:
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
                self.chess_board.switch_player()
                self.query_one("#chess_board_display", Static).update(self.chess_board.display())
                self.query_one("#chess_status", Static).update(f"{self.chess_board.get_status()} {result_message}")
                self.query_one("#move_input", Input).value = ""
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
        return [1, 1]

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
        self.current_view = "compose"
        self.message = ""

    def compose(self) -> ComposeResult:
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
                inbox_content = Text()
                for i, msg in enumerate(self.app.mail_service.get_inbox()):
                    inbox_content.append(f"--- Message {i+1} ---\n", style="bold green")
                    inbox_content.append(f"From: {msg['from']}\n", style="blue")
                    inbox_content.append(f"Subject: {msg['subject']}\n", style="yellow")
                    inbox_content.append(f"Time: {msg['timestamp']}\n", style="dim")
                    inbox_content.append(f"Body:\n{msg['body']}\n\n", style="white")
                yield ScrollableContainer(Static(inbox_content, id="inbox_display"))
            else:
                yield Static("Inbox is empty or Mail Service not configured.")
            yield Button("Clear Inbox", id="clear_inbox")
        elif self.current_view == "sent":
            if self.app.mail_service and self.app.mail_service.get_sent_items():
                sent_content = Text()
                for i, msg in enumerate(self.app.mail_service.get_sent_items()):
                    sent_content.append(f"--- Sent Message {i+1} ---\n", style="bold green")
                    sent_content.append(f"To: {msg['to']}\n", style="blue")
                    sent_content.append(f"Subject: {msg['subject']}\n", style="yellow")
                    sent_content.append(f"Time: {msg['timestamp']}\n", style="dim")
                    sent_content.append(f"Body:\n{msg['body']}\n\n", style="white")
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

class BackgroundSelectorScreen(BaseScreen):
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


class FileBrowserScreen(BaseScreen):
    def __init__(self, path=None):
        super().__init__()
        self.path = path or os.getcwd()

    def compose(self) -> ComposeResult:
        yield Static(f"Current Directory: {self.path}")
        yield Button("..", id="parent_dir")
        yield Button("New File", id="new_file")
        files = os.listdir(self.path)
        lv = ListView(*[ListItem(Label(f)) for f in files], id="filelist")
        yield lv
        yield Static("[dim]Select a file or folder.[/]", id="file_content_display")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "parent_dir":
            self.path = os.path.dirname(self.path)
            self.refresh()
        elif event.button.id == "new_file":
            self.app.push_screen(NewFileScreen(self.path))

    def on_list_view_selected(self, event: ListView.Selected):
        selected_item = event.item.query_one(Label).renderable.plain
        selected_path = os.path.join(self.path, selected_item)
        if os.path.isdir(selected_path):
            self.path = selected_path
            self.refresh()
        else:
            try:
                with open(selected_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.query_one("#file_content_display", Static).update(Syntax(content, "python", theme="monokai", line_numbers=True))
            except Exception as e:
                self.query_one("#file_content_display", Static).update(f"[red]Error reading file: {e}[/]")

class NewFileScreen(Screen):
    def __init__(self, current_path):
        super().__init__()
        self.current_path = current_path

    def compose(self) -> ComposeResult:
        yield Static("Create New File", id="new_file_title")
        yield Input(placeholder="Enter filename", id="new_file_name")
        yield Input(placeholder="Enter content (optional)", id="new_file_content")
        yield Button("Create", id="create_file_button")
        yield Button("Cancel", id="cancel_button")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create_file_button":
            file_name = self.query_one("#new_file_name", Input).value
            file_content = self.query_one("#new_file_content", Input).value
            if file_name:
                file_path = os.path.join(self.current_path, file_name)
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(file_content)
                    self.app.notify(f"File '{file_name}' created successfully.", "success")
                    self.app.pop_screen()
                except Exception as e:
                    self.app.notify(f"Error creating file: {e}", "error")
            else:
                self.app.notify("Filename cannot be empty.", "warning")
        elif event.button.id == "cancel_button":
            self.app.pop_screen()

# --- Help/About Screen ---
class HelpScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("ZeldaCLI OS - About", id="help_title")
        yield Static(
            "[b]Version:[/b] 1.0.0\n"
            "[b]Developer:[/b] Cline\n"
            "[b]Description:[/b] A command-line interface operating system built with Textual.\n"
            "Features include: Clock, System Monitor, Notes, File Explorer, Calculator, Terminal, Reminders, Calendar, Chess, Maze Game, Mail Client, and a basic Web Browser.\n\n"
            "[b]Usage Tips:[/b]\n"
            "  - Use Tab/Shift+Tab to navigate between widgets/inputs.\n"
            "  - Use Ctrl+N for Notifications, Ctrl+F for Favorites.\n"
            "  - Right-click taskbar items for window controls.\n"
            "  - Configure API keys in .env for Weather and News widgets.\n"
            "  - Mail service requires SMTP server details in .env.\n"
            "  - Drag and resize widgets on the desktop.\n"
            "  - Enjoy exploring the CLI OS!\n",
            id="help_content"
        )
        yield Button("Back", id="back_help")
        yield Footer()
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back_help":
            self.app.pop_screen()

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
class HelpWidget(Static):
    def render(self) -> str:
        return "Help/About Widget (Click to open app)"

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
        yield Button("🌐 Web Browser", id="add_web_browser")
        yield Button("❌⭕ Tic-Tac-Toe", id="add_tictactoe")
        yield Button("❓ Help/About", id="add_help")
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
            "add_web_browser": (WebBrowserScreen, "Web Browser"),
            "add_tictactoe": (TicTacToeScreen, "Tic-Tac-Toe"),
            "add_help": (HelpScreen, "Help_About"), # Changed "Help/About" to "Help_About"
        }
        if event.button.id in widget_map:
            widget_cls, title = widget_map[event.button.id]
            if title in ["Web Browser", "Tic-Tac-Toe", "Help_About"]: # These are screens, not widgets
                self.app.push_screen(widget_cls())
            else:
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

# --- Desktop Widget Container ---
class Desktop(Container):
    ascii_art = reactive("")
    background = reactive(THEMES["retro"]["background"])

# --- Dashboard Container ---
class Dashboard(Desktop):
    def compose(self) -> ComposeResult:
        # Add a Static widget for ASCII art if it exists
        if self.app.ascii_art:
            yield Static(self.app.ascii_art, id="ascii_art_display")
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
            ("Web Browser", WebBrowserScreen, "🌐"),
            ("Tic-Tac-Toe", TicTacToeScreen, "❌⭕"),
            ("Help/About", HelpScreen, "❓"),
        ]
    def compose(self) -> ComposeResult:
        for name, _, icon in self.apps:
            safe_id = f"launch_{name.replace(' ', '_').replace('/', '_')}" # Replaced / with _
            yield Button(f"{icon} {name}", id=safe_id)
    def on_button_pressed(self, event):
        for name, widget_cls, _ in self.apps:
            safe_id = f"launch_{name.replace(' ', '_').replace('/', '_')}" # Replaced / with _
            if event.button.id == safe_id:
                self._app.open_app(widget_cls, name)
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
        self.open_app(WeatherWidget, "Weather")
        self.open_app(TimeWidget, "Time")
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
        self.dashboard.remove_children()
        self.push_screen(LoginScreen())
    def open_app(self, widget_cls, title, pos_x=0, pos_y=0, width=30, height=5):
        # Check if a widget of this title is already open
        for app_info in self.open_apps:
            if app_info["title"] == title:
                if app_info["minimized"]:
                    self.restore_app(title)
                self.focus_app(title)
                return

        # If not open, create and add it
        if title in ["Web Browser", "Tic-Tac-Toe", "Help_About", "Chess Game", "Maze Game", "Mail Service"]: # These are screens
            self.push_screen(widget_cls())
        else: # These are desktop widgets
            new_widget_instance = widget_cls()
            closable_widget = ClosableWidget(new_widget_instance, title, self, pos_x, pos_y, width, height)
            self.dashboard.mount(closable_widget)
            self.open_apps.append({"title": title, "widget": closable_widget, "focused": True, "minimized": False})
            self.focus_app(title) # Focus the newly added widget
        self.update_taskbar()
        self.refresh()
        self.save_layout()

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
        self.dashboard.background = color
        self.save_layout()
        self.refresh()
    def set_ascii_art(self, art_name):
        if art_name in ASCII_ARTS:
            self.dashboard.ascii_art = ASCII_ARTS[art_name]
        else:
            self.dashboard.ascii_art = ""
        self.save_layout()
        self.refresh()
    def set_theme(self, theme):
        if theme in THEMES:
            self.user_theme = theme
            t = THEMES[theme]
            self.background_color = t["background"]
            self.dashboard.background = t["background"]
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
        for w in self.dashboard.children:
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
            "ascii_art": self.dashboard.ascii_art,
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
        self.dashboard.remove_children()
        self.running_widgets = set()
        self.favorites = data.get("favorites", ["Clock", "Notes"])
        self.avatar = data.get("avatar", ":)")
        self.calendar_events = data.get("calendar_events", [])
        if data:
            self.background_color = data.get("background", THEMES[self.user_theme]["background"])
            self.dashboard.background = self.background_color
            self.dashboard.ascii_art = data.get("ascii_art", "")
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
                self.open_app(widget_cls, w["title"], w["pos_x"], w["pos_y"], w["width"], w["height"])
        else:
            self.open_app(ClockWidget, "Clock")
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "clock":
            self.open_app(ClockWidget, "Clock")
        elif event.button.id == "sysmon":
            self.open_app(SysMonWidget, "SysMon")
        elif event.button.id == "notes":
            self.open_app(NotesWidget, "Notes")
        elif event.button.id == "fileexplorer":
            self.open_app(FileExplorerWidget, "File Explorer")
        elif event.button.id == "calc":
            self.open_app(CalculatorWidget, "Calculator")
        elif event.button.id == "terminal":
            self.open_app(TerminalWidget, "Terminal")
        elif event.button.id == "reminders":
            self.open_app(RemindersWidget, "Reminders")
        elif event.button.id == "calendar":
            self.open_app(CalendarWidget, "Calendar")
        elif event.button.id == "gallery":
            self.open_app(WidgetGallery, "App Store")
        elif event.button.id == "notifcenter":
            self.open_app(NotificationCenter, "Notification Center")
        elif event.button.id == "theme":
            self.open_app(ThemeWidget, "Theme Switcher")
        elif event.button.id == "settings":
            self.open_app(SettingsWidget, "Settings")
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
        self.open_app(widget_cls, widget_name)
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
            "Web Browser": "🌐",
            "Tic-Tac-Toe": "❌⭕",
            "Help_About": "❓", # Changed "Help/About" to "Help_About"
        }
        return icons.get(widget_name, "★")
    def action_open_notifcenter(self):
        self.open_app(NotificationCenter, "Notification Center")
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

if __name__ == "__main__":
    ZeldaCLIOS().run()
