"""Check for updates on GitHub Releases."""

import json
import logging
import subprocess
import urllib.request

log = logging.getLogger("talk2txt")

GITHUB_REPO = "przemokam/Talk2Txt"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def check_for_update(current_version: str) -> dict | None:
    """Check GitHub for a newer release. Returns release info dict or None."""
    try:
        req = urllib.request.Request(
            RELEASES_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "Talk2Txt"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        latest_tag = data.get("tag_name", "").lstrip("v")
        if not latest_tag:
            return None

        if _is_newer(latest_tag, current_version):
            dmg_url = None
            for asset in data.get("assets", []):
                if asset["name"].endswith(".dmg"):
                    dmg_url = asset["browser_download_url"]
                    break

            return {
                "version": latest_tag,
                "url": data.get("html_url", ""),
                "dmg_url": dmg_url,
                "body": data.get("body", ""),
            }
    except Exception as e:
        log.debug(f"Update check failed: {e}")

    return None


def open_release_page(url: str):
    """Open the release page in the default browser."""
    subprocess.Popen(["open", url])


def _is_newer(latest: str, current: str) -> bool:
    """Compare version strings (e.g. '1.2.0' > '1.1.0')."""
    try:
        latest_parts = [int(x) for x in latest.split(".")]
        current_parts = [int(x) for x in current.split(".")]
        return latest_parts > current_parts
    except (ValueError, AttributeError):
        return False
