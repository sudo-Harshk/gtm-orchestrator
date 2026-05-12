from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    groq_api_key: str
    app_env: str
    log_level: str

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            app_env=os.getenv("APP_ENV", "local"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


config = Config.from_env()
