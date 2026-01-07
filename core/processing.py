# core/processing.py
import json
from typing import Dict, Any


class SiteConfig:
    """Holds configuration for a specific site."""

    def __init__(
        self,
        name: str,
        important_methods: list = [],
        important_paths: list = [],
        very_important_methods: list = [],
        very_important_paths: list = [],
    ):
        self.name = name
        self.important_methods = important_methods
        self.important_paths = important_paths

        self.very_important_methods = very_important_methods
        self.very_important_paths = very_important_paths


class CaddyLog:
    def __init__(self, raw_data: Dict[str, Any], site_config: SiteConfig):
        self.raw = raw_data
        self.config = site_config

        # Extract Request Data
        req = raw_data.get("request", {})
        self.host = req.get("host", "unknown")
        self.remote_ip = req.get("remote_ip", "")
        self.method = req.get("method", "")
        self.uri = req.get("uri", "")
        self.headers = json.dumps(req.get("headers", {}))

        # Caddy doesn't always log body by default unless configured,
        # but if it's there, we grab it.
        self.body = json.dumps(raw_data.get("request_body", {}))

        # Cookies are usually inside headers, but we can extract strictly if needed
        self.cookies = req.get("headers", {}).get("Cookie", [])
        if isinstance(self.cookies, list):
            self.cookies = "; ".join(self.cookies)

        # Extract Response Data
        self.status = raw_data.get("status", 0)
        self.resp_headers = json.dumps(raw_data.get("resp_headers", {}))

        # Metrics
        self.duration = raw_data.get("duration", 0)

    @property
    def is_important(self) -> bool:
        if self.method in self.config.important_methods:
            for path in self.config.important_paths:
                if path in self.uri.lower():
                    return True

        return False

    @property
    def is_very_important(self) -> bool:
        if self.method in self.config.very_important_methods:
            for path in self.config.very_important_paths:
                if path in self.uri.lower():
                    return True

        return False

    def get_preview_string(self):
        """Generates a short summary for Telegram captions."""
        # Example: 🚨 500 POST /admin/login (1.2.3.4)
        icon = "🆕" if self.is_very_important else "📝"
        return f"{icon} <b>{self.status}</b> {self.method} {self.uri}\nIP: <code>{self.remote_ip}</code>"

    def to_tuple(self):
        """Helper for SQLite insertion"""
        return (
            self.host,
            self.remote_ip,
            self.method,
            self.uri,
            self.status,
            self.headers,
            self.body,
            self.cookies,
            self.resp_headers,
            self.duration,
        )
