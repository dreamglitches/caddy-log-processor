# core/config_manager.py
import json
from pathlib import Path
from core.processing import SiteConfig
from utils.logger import log_event, log_error

DEFAULT_CONFIG = SiteConfig(
    "default",
    ["GET", "POST", "PUT", "DELETE", "PATCH"],
    [
        "admin",
        "administrator",
        "manage",
        "dashboard",
        "user",
        "home",
        "homepage",
        "index",
        "account",
        "settings",
        "profile",
        "payment",
        "checkout",
        "cart",
        "order",
        "buy",
    ],
    [
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
    [
        "login",
        "log-in",
        "signin",
        "sign-in",
        "signup",
        "sign-up",
        "register",
        "reset",
        "forgot",
    ],
)


class ConfigManager:
    def __init__(self, config_path="rules.json"):
        self.config_path = Path(config_path)
        self.configs = {}
        self.load_configs()

    def load_configs(self):
        try:
            if not self.config_path.exists():
                log_error(f"Config file {self.config_path} not found.")
                return False

            with open(self.config_path, "r") as f:
                raw_rules = json.load(f)

            new_configs = {}
            for host, rules in raw_rules.items():
                new_configs[host] = SiteConfig(
                    host,
                    [method.upper() for method in rules.get("important_methods", [])],
                    [path.lower() for path in rules.get("important_paths", [])],
                    [
                        method.upper()
                        for method in rules.get("very_important_methods", [])
                    ],
                    [path.lower() for path in rules.get("very_important_paths", [])],
                )

            self.configs = new_configs
            log_event(f"Loaded configuration for {len(self.configs)} sites.")
            return True
        except Exception as e:
            log_error(f"Failed to load config: {e}")
            return False

    def get_config(self, host: str) -> SiteConfig:
        return self.configs.get(host, DEFAULT_CONFIG)


# Global Instance
config_manager = ConfigManager()
