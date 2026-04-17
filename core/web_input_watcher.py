"""
web_input_watcher.py — Monitors input_web.json / input_web.txt for main.py to consume.
"""

import json
import os

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import core.config as config
import core.skills as skills

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE = os.path.join(BASE_DIR, "data", "input_web.json")


class WebUIWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if "input_web.json" in event.src_path:
            try:
                with open(INPUT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                open(INPUT_FILE, "w").close()

                cmd = data.get("comando", "")

                if cmd == "toggle_batepapo":
                    if data.get("ativo"):
                        skills.activate()
                    else:
                        skills.deactivate()
                    return

                if data.get("conteudo_completo", "").strip() or data.get("arquivos"):
                    config.pending_web_input = data

            except Exception:
                pass

        elif INPUT_FILE in event.src_path:
            try:
                with open(INPUT_FILE, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    config.pending_web_input = text
                    open(INPUT_FILE, "w").close()
            except Exception:
                pass


_observer: Observer | None = None


def start_web_input_watcher() -> None:
    """Start observer in data/ folder."""
    global _observer
    if _observer is not None:
        return
    
    data_dir = os.path.join(BASE_DIR, "data")
    
    # Ensure folder exists
    os.makedirs(data_dir, exist_ok=True)
    
    _observer = Observer()
    _observer.schedule(WebUIWatcher(), path=data_dir, recursive=False)
    
    # Daemon: doesn't hold the process on exit
    try:
        _observer.daemon = True
    except AttributeError:
        pass
    
    _observer.start()