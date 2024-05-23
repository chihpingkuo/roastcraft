import json


def load_settings() -> dict:
    with open("settings.json", "rb") as f:
        settings = json.load(f)
        print(settings)
        return settings
