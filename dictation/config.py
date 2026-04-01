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


_VALID_HOTKEYS = set(HOTKEY_OPTIONS.values())


def load() -> dict:
    """Load settings from disk, falling back to defaults. Validates values."""
    config = DEFAULTS.copy()
    try:
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
        if saved.get("hotkey") in _VALID_HOTKEYS:
            config["hotkey"] = saved["hotkey"]
        if isinstance(saved.get("microphone"), (int, type(None))):
            config["microphone"] = saved["microphone"]
        if isinstance(saved.get("sound_feedback"), bool):
            config["sound_feedback"] = saved["sound_feedback"]
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
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
