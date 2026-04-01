"""Talk2Txt configuration — load/save settings to JSON."""

import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/talk2txt")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS = {
    "hotkey": "<ctrl>+<shift>+d",
    "microphone": None,  # None = system default
    "sound_feedback": True,
    "auto_start": False,
}

HOTKEY_OPTIONS = {
    "Ctrl+Shift+D": "<ctrl>+<shift>+d",
    "Ctrl+Shift+R": "<ctrl>+<shift>+r",
    "Ctrl+Shift+Space": "<ctrl>+<shift>+space",
    "Option+D": "<alt>+d",
    "Option+Space": "<alt>+space",
    "F5": "<f5>",
    "F6": "<f6>",
    "F8": "<f8>",
}


def load() -> dict:
    """Load settings from disk, falling back to defaults."""
    config = DEFAULTS.copy()
    try:
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        config.update(saved)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return config


def save(config: dict):
    """Save settings to disk."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_hotkey_label(hotkey_value: str) -> str:
    """Get human-readable label for a hotkey value."""
    for label, value in HOTKEY_OPTIONS.items():
        if value == hotkey_value:
            return label
    return hotkey_value
