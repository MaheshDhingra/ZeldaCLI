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

THEMES = {
    "retro": {
        "background": "#181818",
        "foreground": "#e0e0e0",
        "primary": "#00ffae",
        "secondary": "#ff00c8",
        "accent": "#ffd700",
        "error": "#ff5555",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "info": "#8be9fd",
    },
    "dark": {
        "background": "#222831",
        "foreground": "#eeeeee",
        "primary": "#00adb5",
        "secondary": "#393e46",
        "accent": "#ffd369",
        "error": "#ff5555",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "info": "#8be9fd",
    },
    "light": {
        "background": "#f8f8f8",
        "foreground": "#222831",
        "primary": "#00adb5",
        "secondary": "#393e46",
        "accent": "#ffd369",
        "error": "#ff5555",
        "success": "#50fa7b",
        "warning": "#f1fa8c",
        "info": "#8be9fd",
    },
}

ASCII_ARTS = {
    "triforce": r"""
      ▲
     ▲ ▲
    ▲▲▲▲▲
    """,
    "zelda": r"""
   ______      _     _        _____ _     ___  ___ ___ 
  |___  /     | |   | |      /  __ \ |    |  \/  ||  \
     / / _ __ | |__ | |_ ___ | /  \/ |    | .  . || . \
    / / | '_ \| '_ \| __/ _ \| |   | |    | |\/| || |\/|
  ./ /__| | | | | | | || (_) | \__/\ |____| |  | || |  |
  \____/_| |_|_| |_|\__\___/ \____/\_____/_|  |_/\_|  |_/
    """
}

# --- Utility: Save/Load Config ---
def user_config_path(username):
    return os.path.join(CONFIG_DIR, f"{username}_config.json")

def user_notes_path(username):
    return os.path.join(CONFIG_DIR, f"{username}_notes.txt")

def user_reminders_path(username):
    return os.path.join(CONFIG_DIR, f"{username}_reminders.json")

def save_config(username, data):
    with open(user_config_path(username), "w") as f:
        json.dump(data, f)

def load_config(username):
    path = user_config_path(username)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_notes(username, notes):
    with open(user_notes_path(username), "w", encoding="utf-8") as f:
        f.write(notes)

def load_notes(username):
    path = user_notes_path(username)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""

def save_reminders(username, reminders):
    with open(user_reminders_path(username), "w", encoding="utf-8") as f:
        json.dump(reminders, f)

def load_reminders(username):
    path = user_reminders_path(username)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []

# --- Login Screen ---
class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("[b][#ffd700]ZeldaCLI OS Login[/]"),
            Input(placeholder="Enter username...", id="user_input")
        )
    def on_input_submitted(self, event: Input.Submitted):
        username = event.value.strip()
        if username:
            self.app.login(username)
            self.app.pop_screen()

# --- Custom Notification System ---
class NotificationBar(Static):
    def __init__(self, message, style, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.style = style
    def compose(self) -> ComposeResult:
        yield Label(f"[{self.style}] {self.message}")

# --- Notification Helper ---
def notify(app, message, style="info"):
    app.notifications.append({"message": message, "style": style})
    bar = NotificationBar(message, style)
    # Try to mount before #desktop on the main screen, else mount on the current screen
    try:
        app.mount(bar, before="#desktop")
    except Exception:
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
