"""Manage auto-start at login via macOS LaunchAgent."""

import os
import plistlib
import logging

log = logging.getLogger("talk2txt")

PLIST_LABEL = "com.przemo.talk2txt"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_LABEL}.plist")


def is_enabled() -> bool:
    return os.path.exists(PLIST_PATH)


def enable():
    """Create LaunchAgent plist to start Talk2Txt at login."""
    app_path = _find_app_path()
    if not app_path:
        log.warning("Cannot enable auto-start: Talk2Txt.app not found in /Applications")
        return False

    plist = {
        "Label": PLIST_LABEL,
        "ProgramArguments": [f"{app_path}/Contents/MacOS/Talk2Txt"],
        "RunAtLoad": True,
        "KeepAlive": False,
    }

    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(plist, f)

    log.info(f"Auto-start enabled: {PLIST_PATH}")
    return True


def disable():
    """Remove LaunchAgent plist."""
    try:
        os.remove(PLIST_PATH)
        log.info("Auto-start disabled")
        return True
    except FileNotFoundError:
        return True


def _find_app_path() -> str | None:
    """Find Talk2Txt.app in /Applications."""
    path = "/Applications/Talk2Txt.app"
    if os.path.exists(path):
        return path
    return None
