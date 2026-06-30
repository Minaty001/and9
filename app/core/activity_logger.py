"""
app/core/activity_logger.py — Daily Activity Logger.
"""
import os
import re
import logging
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

ACTIVITIES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "activities")
)


class ActivityLogger:

    def __init__(self):
        os.makedirs(ACTIVITIES_DIR, exist_ok=True)
        self._lock = Lock()

    def log(self, query: str, response: str):
        today = datetime.now().strftime("%Y-%m-%d")
        filepath = os.path.join(ACTIVITIES_DIR, f"{today}.txt")
        timestamp = datetime.now().strftime("%H:%M:%S")

        response = str(response).strip() if response else ""

        entry = (
            f"[{timestamp}] USER:\n{query}\n\n"
            f"[{timestamp}] JARVIS:\n{response}\n\n"
            f"{ '-' * 40 }\n"
        )

        with self._lock:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(entry)

    def list_files(self) -> list:
        files = []
        with self._lock:
            for name in os.listdir(ACTIVITIES_DIR):
                if name.endswith(".txt") and re.match(r"^\d{4}-\d{2}-\d{2}\.txt$", name):
                    path = os.path.join(ACTIVITIES_DIR, name)
                    date_str = name.replace(".txt", "")
                    files.append({
                        "date": date_str,
                        "name": name,
                        "size": os.path.getsize(path),
                        "entries": self._count_entries(path),
                        "modified": os.path.getmtime(path),
                    })
        files.sort(key=lambda x: x["date"], reverse=True)
        return files

    def read_file(self, date_str: str) -> str | None:
        filepath = os.path.join(ACTIVITIES_DIR, f"{date_str}.txt")
        with self._lock:
            if not os.path.exists(filepath):
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

    def write_file(self, date_str: str, content: str) -> bool:
        filepath = os.path.join(ACTIVITIES_DIR, f"{date_str}.txt")
        with self._lock:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        return True

    @staticmethod
    def _count_entries(path: str) -> int:
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().endswith("USER:"):
                    count += 1
        return count


_instance = None

def get_activity_logger() -> ActivityLogger:
    global _instance
    if _instance is None:
        _instance = ActivityLogger()
    return _instance
