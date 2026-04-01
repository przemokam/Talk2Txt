#!/usr/bin/env python3
"""Talk2Txt — local dictation app. Sits in the menu bar, toggle recording with Ctrl+Shift+D."""

import os
import sys
import logging

# Ensure imports work regardless of working directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

# Ensure ffmpeg and other Homebrew tools are in PATH (needed for .app bundles)
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

# Log to file so we can debug .app launches
LOG_FILE = os.path.join(APP_DIR, "talk2txt.log")
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
from pynput import keyboard
from recorder import Recorder
from transcriber import Transcriber
from paster import paste_text

HOTKEY = "<ctrl>+<shift>+d"

ICON_IDLE = "🎤"
ICON_RECORDING = "⏺"
ICON_PROCESSING = "⏳"


class DictationApp(rumps.App):
    def __init__(self):
        super().__init__("Talk2Txt", title=ICON_IDLE)
        self.menu = [
            rumps.MenuItem("Status: Ready"),
            None,
            rumps.MenuItem("Preload model", callback=self._on_preload),
            None,
        ]
        self.recorder = Recorder()
        self.transcriber = Transcriber()
        self._status_item = self.menu["Status: Ready"]

    def _set_status(self, icon: str, status: str):
        self.title = icon
        self._status_item.title = f"Status: {status}"

    def _on_preload(self, _):
        self._set_status(ICON_PROCESSING, "Loading model...")
        threading.Thread(target=self._preload_model, daemon=True).start()

    def _preload_model(self):
        self.transcriber._ensure_model()
        self._set_status(ICON_IDLE, "Ready")
        rumps.notification("Talk2Txt", "", "Model loaded. Ready to dictate!")

    def _toggle_recording(self):
        if self.recorder.is_recording:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self):
        log.info("Nagrywanie START")
        self.recorder.start()
        self._set_status(ICON_RECORDING, "Recording...")

    def _stop_and_transcribe(self):
        audio = self.recorder.stop()
        log.info(f"Nagrywanie STOP, samples={len(audio) if audio is not None else 0}")
        if audio is None or len(audio) < 1600:
            self._set_status(ICON_IDLE, "Ready")
            return

        self._set_status(ICON_PROCESSING, "Transcribing...")
        threading.Thread(target=self._transcribe_and_paste, args=(audio,), daemon=True).start()

    def _transcribe_and_paste(self, audio):
        try:
            t0 = time.time()
            log.info(f"Transkrypcja start, {len(audio)} samples, {len(audio)/16000:.1f}s audio")
            text = self.transcriber.transcribe(audio)
            elapsed = time.time() - t0
            log.info(f"Transkrypcja done w {elapsed:.1f}s: '{text}'")

            if text:
                log.info("Wklejanie tekstu...")
                paste_text(text)
                log.info("Wklejanie done")
                self._set_status(ICON_IDLE, f"Ready ({elapsed:.1f}s, {len(audio)/16000:.0f}s audio)")
            else:
                log.info("Pusty tekst — no speech")
                self._set_status(ICON_IDLE, "Ready (no speech)")
        except Exception as e:
            log.error(f"BŁĄD: {e}", exc_info=True)
            self._set_status(ICON_IDLE, f"Error: {e}")

    def start_hotkey_listener(self):
        def on_activate():
            threading.Thread(target=self._toggle_recording, daemon=True).start()

        listener = keyboard.GlobalHotKeys({HOTKEY: on_activate})
        listener.start()


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
    log.info("1. Tworzenie app...")
    app = DictationApp()
    log.info("2. Start hotkey listener...")
    try:
        app.start_hotkey_listener()
    except Exception as e:
        log.error(f"HOTKEY ERROR: {e}")
    log.info("3. Preload model...")
    threading.Thread(target=app._preload_model, daemon=True).start()
    # Check permissions after short delay (so notification system is ready)
    threading.Timer(2.0, check_and_prompt_accessibility).start()
    log.info(f"4. Starting menu bar. Hotkey: {HOTKEY}")
    app.run()


if __name__ == "__main__":
    main()
