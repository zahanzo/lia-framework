"""
web_input_watcher.py — Observa input_web.json / input_web.txt para o main.py consumir.
Mantém o main.py mais enxuto (sem PyQt / sem lógica de ficheiro no loop principal).
"""

import json

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import config
import skills as skills_mod


class WebUIWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if "input_web.json" in event.src_path:
            try:
                with open("input_web.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                open("input_web.json", "w").close()

                cmd = data.get("comando", "")

                if cmd == "toggle_batepapo":
                    if data.get("ativo"):
                        skills_mod.activate()
                    else:
                        skills_mod.deactivate()
                    return

                if data.get("conteudo_completo", "").strip() or data.get("arquivos"):
                    config.pending_web_input = data

            except Exception:
                pass

        elif "input_web.txt" in event.src_path:
            try:
                with open("input_web.txt", "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    config.pending_web_input = text
                    open("input_web.txt", "w").close()
            except Exception:
                pass


_observer: Observer | None = None


def start_web_input_watcher() -> None:
    """Inicia o observer na pasta de trabalho atual (onde corre o main)."""
    global _observer
    if _observer is not None:
        return
    _observer = Observer()
    _observer.schedule(WebUIWatcher(), path=".", recursive=False)
    # Daemon: não segura o processo no exit (evita join longo do interpretador).
    try:
        _observer.daemon = True
    except AttributeError:
        pass
    _observer.start()
