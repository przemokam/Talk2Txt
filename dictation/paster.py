"""Paste text into the currently focused application via clipboard + Cmd+V."""

import time
from AppKit import NSPasteboard, NSPasteboardTypeString
from Quartz.CoreGraphics import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand,
)

V_KEYCODE = 0x09  # macOS virtual keycode for 'V'


def paste_text(text: str):
    """Copy text to clipboard via NSPasteboard and simulate Cmd+V."""
    # Use NSPasteboard directly — no encoding issues with Unicode/Polish
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)

    time.sleep(0.05)

    # Simulate Cmd+V keypress
    event_down = CGEventCreateKeyboardEvent(None, V_KEYCODE, True)
    CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event_down)

    event_up = CGEventCreateKeyboardEvent(None, V_KEYCODE, False)
    CGEventSetFlags(event_up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, event_up)
