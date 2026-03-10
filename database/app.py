from datetime import datetime
import json
import time
import threading
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

ROOT = Path(__file__).resolve().parent

INPUT_DIR = ROOT / "staging"
ARCHIVE_DIR = ROOT / "cached"
DATABASE_FILE = ROOT / "database.json"

WEBPAGE_DIR = ROOT / "webpage"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=str(WEBPAGE_DIR), static_url_path="")

db = {
    "metadata": {
        "last_updated": None,
        "record_count": 0,
    },
    "records": []
}

db_lock = threading.Lock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path):
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    return json.loads(raw)


def _normalize(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("records"), list):
            return [r for r in payload["records"] if isinstance(r, dict)]
        return [payload]
    return []


def _write_master():
    with db_lock:
        db["metadata"]["last_updated"] = _now()
        db["metadata"]["record_count"] = len(db["records"])
        DATABASE_FILE.write_text(
            json.dumps(db, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )


def _process_file(path: Path):
    # Wait until file finishes writing
    last_size = -1
    for _ in range(20):
        size = path.stat().st_size
        if size == last_size:
            break
        last_size = size
        time.sleep(0.25)

    records = _normalize(_read_json(path))

    with db_lock:
        db["records"].extend(records)

    dest = ARCHIVE_DIR / path.name
    if dest.exists():
        dest = ARCHIVE_DIR / f"{path.stem}_{int(time.time())}{path.suffix}"
    path.rename(dest)

    _write_master()


def rebuild_from_archive():
    all_records = []
    for p in sorted(ARCHIVE_DIR.glob("*.json")):
        all_records.extend(_normalize(_read_json(p)))

    with db_lock:
        db["records"] = all_records

    _write_master()

def process_existing():
    for p in sorted(INPUT_DIR.glob("*.json")):
        try:
            _process_file(p)
        except Exception as e:
            print(f"Error processing {p.name}: {e}")


class IncomingHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".json":
            return
        try:
            _process_file(path)
        except Exception as e:
            print(f"Error processing {path.name}: {e}")

    def on_moved(self, event):
        if event.is_directory:
            return
        dest_path = getattr(event, "dest_path", None)
        if not dest_path:
            return
        path = Path(dest_path)
        if path.parent != INPUT_DIR:
            return
        if path.suffix.lower() != ".json":
            return
        try:
            _process_file(path)
        except Exception as e:
            print(f"Error processing {path.name}: {e}")


def start_watcher():
    observer = Observer()
    observer.schedule(IncomingHandler(), str(INPUT_DIR), recursive=False)
    observer.start()
    return observer


@app.get("/")
def index():
    return send_from_directory(WEBPAGE_DIR, "index.html")

@app.get("/api/database")
def api_database():
    if not DATABASE_FILE.exists():
        return jsonify({"metadata": {}, "records": []})
    return jsonify(json.loads(DATABASE_FILE.read_text(encoding="utf-8")))


@app.post("/api/rebuild")
def api_rebuild():
    rebuild_from_archive()
    return jsonify({"ok": True})


if __name__ == "__main__":
    if any(ARCHIVE_DIR.glob("*.json")):
        rebuild_from_archive()
    else:
        _write_master()

    process_existing()

    observer = start_watcher()
    try:
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
    finally:
        observer.stop()
        observer.join()