"""Application settings — extends shon-toolkit's BaseToolkitSettings."""

from __future__ import annotations

from shon_toolkit.client import configure_settings_class
from shon_toolkit.client import get_settings as _get_settings
from shon_toolkit.config import BaseToolkitSettings


class Settings(BaseToolkitSettings):
    pass


configure_settings_class(Settings)


def get_settings() -> Settings:
    return _get_settings()  # type: ignore[return-value]
