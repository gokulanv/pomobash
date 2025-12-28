"""Configuration constants for Pomobash timer application"""

from pathlib import Path

# Paths
HOME_DIR = Path.home()
POMOBASH_DIR = HOME_DIR / "work" / "pomobash"
DATA_DIR = POMOBASH_DIR / "data"

# File paths
TASKS_FILE = DATA_DIR / "tasks.json"
COMPLETED_FILE = DATA_DIR / "completed.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

# Timer configurations (in minutes)
TIMER_DURATIONS = {
    "short": 24,
    "medium": 40,
    "long": 60
}

BREAK_DURATIONS = {
    "short": 5,
    "medium": 10,
    "long": 20
}

# UI Configuration
THEME = {
    "timer": "bold cyan",
    "progress": "green",
    "task": "yellow",
    "break": "magenta",
    "completed": "green",
    "warning": "red",
    "info": "blue",
    "heading": "bold white"
}

# macOS notification sound
COMPLETION_SOUND = "/System/Library/Sounds/Glass.aiff"

# Auto-save interval (seconds)
AUTOSAVE_INTERVAL = 60
