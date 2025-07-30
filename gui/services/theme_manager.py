from __future__ import annotations

"""Global theme manager.

Stores current UI theme in config.json (placed at project root). Only supports
"dark", "light", or "system" for now.
"""

import json
from pathlib import Path
from typing import Literal

ThemeName = Literal["dark", "light", "system"]

CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"
DEFAULT_THEME: ThemeName = "dark"


class ThemeManager:
    _instance: "ThemeManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._theme: ThemeName = DEFAULT_THEME
            cls._instance._load()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text("utf-8"))
                self._theme = data.get("theme", DEFAULT_THEME)  # type: ignore[arg-type]
            except Exception:
                pass

    def _save(self) -> None:
        try:
            data = {"theme": self._theme}
            CONFIG_FILE.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def current(self) -> ThemeName:  # noqa: D401
        return self._theme

    def set_theme(self, name: ThemeName) -> None:
        if name not in {"dark", "light", "system"}:
            raise ValueError("invalid theme")
        self._theme = name
        self._save()

    # Utility: apply to ttkbootstrap
    def apply_to_root(self, root) -> None:
        if hasattr(root, "style"):
            theme_map = {"dark": "darkly", "light": "flatly", "system": root.style.theme.name}
            new_theme = theme_map.get(self._theme, "darkly")
            try:
                root.style.theme_use(new_theme)
            except Exception:
                pass