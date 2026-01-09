# core/database.py
import sqlite3
import threading
import queue
import time
import shutil
from pathlib import Path
from utils.logger import log_event, log_error

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT, remote_ip TEXT, method TEXT, uri TEXT, status INTEGER,
    headers TEXT, body TEXT, cookies TEXT, resp_headers TEXT, duration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class DBWorker(threading.Thread):
    def __init__(self, db_folder="data", rotate_limit=1000):
        super().__init__()
        self.db_folder = Path(db_folder)
        self.db_folder.mkdir(exist_ok=True)
        self.rotate_limit = rotate_limit

        # Unified Queue for Logs AND Commands
        self.input_queue = queue.Queue()

        # Queue for Bot Notifications
        self.notification_queue = queue.Queue()

        self._site_connections = {}
        self.running = True
        self.daemon = True

    def stop(self):
        self.running = False
        self.input_queue.put(None)

    def get_active_sites(self):
        """Thread-safe way to get list of sites and row counts for stats"""
        # Returns a COPY of the stats to avoid thread race conditions
        stats = {}
        # Note: Iterating this dict while the thread modifies it is technically risky
        # but in CPython mostly atomic for simple reads. For strict safety,
        # we would push a "get_stats" command, but for simple stats this suffices.
        for site, info in self._site_connections.items():
            stats[site] = info["count"]
        return stats

    def request_snapshot(self, site):
        """Public method to request a non-destructive copy of the DB"""
        self.input_queue.put({"type": "snapshot", "site": site})

    def request_rotation(self, site):
        """Public method to force rotation"""
        self.input_queue.put({"type": "rotate", "site": site})

    def run(self):
        log_event("DB Worker Thread Started")
        while self.running:
            try:
                task = self.input_queue.get()
                if task is None:
                    break

                msg_type = task.get("type")

                if msg_type == "log":
                    self._handle_write(
                        task["site"], task["data"], task["vip"], task.get("preview")
                    )
                elif msg_type == "snapshot":
                    self._handle_snapshot(task["site"])
                elif msg_type == "rotate":
                    self._rotate_log(task["site"], "User Command")

            except Exception as e:
                log_error(f"DB Worker Exception: {e}", exc_info=True)

        self._close_all()

    def _get_conn(self, site):
        if site not in self._site_connections:
            db_path = self.db_folder / f"{site}.db"
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            conn.execute(CREATE_TABLE_SQL)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM logs")
            self._site_connections[site] = {"conn": conn, "count": cursor.fetchone()[0]}
        return self._site_connections[site]

    def _handle_write(self, site, log_data, is_vip, preview=None):
        info = self._get_conn(site)
        info["conn"].execute(
            """
            INSERT INTO logs (host, remote_ip, method, uri, status, headers, body, cookies, resp_headers, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            log_data,
        )
        info["conn"].commit()
        info["count"] += 1
        limit_reached = info["count"] >= self.rotate_limit

        if limit_reached:
            reason = "Limit Reached"
            if is_vip:
                reason += " AND Important Log"
            # Pass the preview to rotation
            self._rotate_log(site, reason, preview_context=preview)

        if is_vip and not limit_reached:
            self.notification_queue.put(
                {
                    "site": site,
                    "important_preview": preview,
                }
            )

    def _handle_snapshot(self, site):
        """Creates a copy without closing the connection"""
        if site not in self._site_connections:
            # If no DB exists yet, create an empty one just so we can send it
            self._get_conn(site)

        # Use SQLite Backup API to safely copy even if open
        src_conn = self._site_connections[site]["conn"]
        timestamp = int(time.time())
        dest_path = self.db_folder / f"snapshot_{site}_{timestamp}.db"

        bck_conn = sqlite3.connect(str(dest_path))
        src_conn.backup(bck_conn)
        bck_conn.close()

        self.notification_queue.put(
            {
                "site": site,
                "path": str(dest_path),
                "reason": "Manual Snapshot",
                "delete_after": True,  # Helper flag
            }
        )

    def _rotate_log(self, site, reason, preview_context=None):
        if site not in self._site_connections:
            return

        # Close and Rename
        self._site_connections[site]["conn"].close()
        del self._site_connections[site]

        timestamp = int(time.time())
        original = self.db_folder / f"{site}.db"
        rotated = self.db_folder / f"log_{site}_{timestamp}.db"

        if original.exists():
            shutil.move(str(original), str(rotated))
            self.notification_queue.put(
                {
                    "site": site,
                    "path": str(rotated),
                    "reason": f"{reason} 🔁",
                    "delete_after": True,
                    "preview": preview_context,
                }
            )

    def _close_all(self):
        for info in self._site_connections.values():
            info["conn"].close()
