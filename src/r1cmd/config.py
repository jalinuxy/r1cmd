"""Local user configuration (access key, secret key, default storage space)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from r1cmd.constants import CONFIG_DIR_NAME, CONFIG_FILE_NAME


@dataclass
class UserConfig:
    """Saved credentials and preferences for the interactive CLI."""

    access_key: str
    secret_key: str
    default_space: Optional[str] = None

    @property
    def config_dir(self) -> Path:
        xdg_config = os.getenv("XDG_CONFIG_HOME")
        base = Path(xdg_config) if xdg_config else Path.home() / ".config"
        return base / CONFIG_DIR_NAME

    @property
    def config_path(self) -> Path:
        return self.config_dir / CONFIG_FILE_NAME

    @classmethod
    def config_file(cls) -> Path:
        return cls("", "").config_path

    @classmethod
    def exists(cls) -> bool:
        return cls.config_file().is_file()

    @classmethod
    def load(cls) -> "UserConfig":
        path = cls.config_file()
        if not path.is_file():
            raise FileNotFoundError(str(path))

        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            access_key=data["access_key"],
            secret_key=data["secret_key"],
            default_space=data.get("default_space"),
        )

    def save(self) -> Path:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        path = self.config_path
        path.write_text(
            json.dumps(asdict(self), indent=2) + "\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
        return path

    def clear(self) -> None:
        path = self.config_path
        if path.is_file():
            path.unlink()
