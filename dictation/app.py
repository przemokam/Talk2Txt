#!/usr/bin/env python3
"""Talk2Txt — local dictation app. Sits in the menu bar, toggle recording with a hotkey."""

import os
import sys
import logging

# Ensure imports work regardless of working directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# Ensure Homebrew tools are in PATH (for potential system dependencies)
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

# Log to writable location (APP_DIR may be inside read-only .app bundle)
LOG_DIR = os.path.expanduser("~/.config/talk2txt")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "talk2txt.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger("talk2txt")

import subprocess
import threading
import time
import rumps
import sounddevice as sd
from pynput import keyboard
from recorder import Recorder
from transcriber import Transcriber
from paster import paste_text
import config

VERSION = "1.1.0"

ICON_IDLE = "🎤"
ICON_RECORDING = "⏺"
ICON_PROCESSING = "⏳"


def play_sound(name: str):
    """Play a macOS system sound (non-blocking)."""
    path = f"/System/Library/Sounds/{name}.aiff"
    if os.path.exists(path):
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class DictationApp(rumps.App):
    def __init__(self):
        super().__init__("Talk2Txt", title=ICON_IDLE)
        self.cfg = config.load()
        self.recorder = Recorder(device=self.cfg.get("microphone"))
        self.transcriber = Transcriber()
        self._hotkey_listener = None

        # Build menu
        self._status_item = rumps.MenuItem("Status: Starting...")
        self._hotkey_menu = rumps.MenuItem("Hotkey")
        self._mic_menu = rumps.MenuItem("Microphone")
        self._sound_item = rumps.MenuItem(
            "Sound Feedback",
            callback=self._toggle_sound,
        )
        self._sound_item.state = self.cfg.get("sound_feedback", True)

        self.menu = [
            self._status_item,
            None,
            self._hotkey_menu,
            self._mic_menu,
            self._sound_item,
            None,
            rumps.MenuItem("About Talk2Txt", callback=self._show_about),
            None,
        ]

        self._populate_hotkey_submenu()
        self._populate_mic_submenu()

    # --- Menu builders ---

    def _populate_hotkey_submenu(self):
        current = self.cfg["hotkey"]
        for label, value in config.HOTKEY_OPTIONS.items():
            item = rumps.MenuItem(label, callback=self._change_hotkey)
            item._hotkey_value = value
            item.state = value == current
            self._hotkey_menu.add(item)

    def _populate_mic_submenu(self):
        current_device = self.cfg.get("microphone")

        default_item = rumps.MenuItem("System Default", callback=self._change_mic)
        default_item._device_index = None
        default_item.state = current_device is None
        self._mic_menu.add(default_item)

        self._mic_menu.add(rumps.separator)

        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev["max_input_channels"] > 0:
                item = rumps.MenuItem(dev["name"], callback=self._change_mic)
                item._device_index = i
                item.state = current_device == i
                self._mic_menu.add(item)

    # --- Settings callbacks ---

    def _change_hotkey(self, sender):
        new_hotkey = sender._hotkey_value
        self.cfg["hotkey"] = new_hotkey
        config.save(self.cfg)
        # Update checkmarks
        for item in self._hotkey_menu.values():
            if hasattr(item, '_hotkey_value'):
                item.state = item._hotkey_value == new_hotkey
        self._restart_hotkey_listener()
        label = config.get_hotkey_label(new_hotkey)
        rumps.notification("Talk2Txt", "", f"Hotkey changed to {label}")

    def _change_mic(self, sender):
        new_device = sender._device_index
        self.cfg["microphone"] = new_device
        config.save(self.cfg)
        self.recorder = Recorder(device=new_device)
        # Update checkmarks
        for item in self._mic_menu.values():
            if hasattr(item, '_device_index'):
                item.state = item._device_index == new_device
        rumps.notification("Talk2Txt", "", f"Microphone: {sender.title}")

    def _toggle_sound(self, sender):
        sender.state = not sender.state
        self.cfg["sound_feedback"] = sender.state
        config.save(self.cfg)

    def _show_about(self, _):
        rumps.alert(
            title=f"Talk2Txt v{VERSION}",
            message=(
                "Local, offline speech-to-text dictation for macOS.\n\n"
                f"Hotkey: {config.get_hotkey_label(self.cfg['hotkey'])}\n"
                "Press the hotkey to start recording, press again to stop and paste.\n\n"
                "Supported languages: 25 European languages with auto-detection\n"
                "(English, Polish, German, French, Spanish, and more)\n\n"
                "Model: NVIDIA Parakeet TDT 0.6B v3 (MLX)\n\n"
                "Requirements:\n"
                "• macOS with Apple Silicon (M1/M2/M3/M4)\n"
                "• Accessibility & Input Monitoring permissions\n"
                "• ffmpeg (brew install ffmpeg)"
            ),
            ok="OK",
        )

    # --- Status ---

    def _set_status(self, icon: str, status: str):
        self.title = icon
        self._status_item.title = f"Status: {status}"

    # --- Recording flow ---

    def _toggle_recording(self):
        if self.recorder.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self):
        log.info("Recording START")
        self.recorder.start()
        self._set_status(ICON_RECORDING, "Recording...")
        if self.cfg.get("sound_feedback"):
            play_sound("Tink")

    def _stop_and_transcribe(self):
        audio = self.recorder.stop()
        samples = len(audio) if audio is not None else 0
        log.info(f"Recording STOP, samples={samples}")

        if self.cfg.get("sound_feedback"):
            play_sound("Pop")

        if audio is None or samples < 1600:
            self._set_status(ICON_IDLE, "Ready")
            return

        self._set_status(ICON_PROCESSING, "Transcribing...")
        threading.Thread(target=self._transcribe_and_paste, args=(audio,), daemon=True).start()

    def _transcribe_and_paste(self, audio):
        try:
            t0 = time.time()
            log.info(f"Transcription start, {len(audio)} samples, {len(audio)/16000:.1f}s audio")
            text = self.transcriber.transcribe(audio)
            elapsed = time.time() - t0
            log.info(f"Transcription done in {elapsed:.1f}s: '{text}'")

            if text:
                paste_text(text)
                self._set_status(ICON_IDLE, f"Ready ({elapsed:.1f}s, {len(audio)/16000:.0f}s audio)")
            else:
                self._set_status(ICON_IDLE, "Ready (no speech)")
        except Exception as e:
            log.error(f"Error: {e}", exc_info=True)
            self._set_status(ICON_IDLE, f"Error: {e}")

    # --- Hotkey listener ---

    def start_hotkey_listener(self):
        hotkey = self.cfg["hotkey"]
        log.info(f"Hotkey listener: {hotkey}")

        def on_activate():
            threading.Thread(target=self._toggle_recording, daemon=True).start()

        self._hotkey_listener = keyboard.GlobalHotKeys({hotkey: on_activate})
        self._hotkey_listener.start()

    def _restart_hotkey_listener(self):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        self.start_hotkey_listener()

    # --- Model preload ---

    def _preload_model(self):
        self.transcriber._ensure_model()
        self._set_status(ICON_IDLE, "Ready")
        rumps.notification("Talk2Txt", "", "Model loaded. Ready to dictate!")


def check_and_prompt_accessibility():
    """Check Accessibility permission after app starts. Non-blocking."""
    try:
        from ApplicationServices import AXIsProcessTrusted
        if AXIsProcessTrusted():
            log.info("Accessibility: OK")
            return
    except ImportError:
        return

    log.warning("Missing Accessibility permissions")
    rumps.notification(
        "Talk2Txt — Permissions Required",
        "",
        "Open System Settings → Privacy → Accessibility & Input Monitoring. Enable Talk2Txt, then restart.",
    )
    subprocess.Popen([
        "open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    ])


def main():
    log.info("Starting Talk2Txt...")
    app = DictationApp()
    app.start_hotkey_listener()
    threading.Thread(target=app._preload_model, daemon=True).start()
    threading.Timer(2.0, check_and_prompt_accessibility).start()
    hotkey_label = config.get_hotkey_label(app.cfg["hotkey"])
    log.info(f"Menu bar ready. Hotkey: {hotkey_label}")
    app.run()


if __name__ == "__main__":
    main()
