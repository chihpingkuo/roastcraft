import json
from .loggers import LOG_FASTAPI_CLI


def load_settings() -> dict:
    with open("settings.json", "rb") as f:
        settings = json.load(f)
        LOG_FASTAPI_CLI.info(settings)
        return settings
