"""app/plugins/weather/plugin.py — Weather plugin for AND9"""
import logging
import requests

from app.plugins.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class Plugin(BasePlugin):
    name = "WeatherPlugin"
    version = "1.0"
    intents = ["get_weather", "weather_forecast", "weather"]
    ram_estimate_mb = 3

    def handle(self, intent: str, entities: dict) -> dict:
        """Handle weather queries."""
        location = entities.get("location", "your area")
        try:
            # Simple weather lookup using wttr.in
            resp = requests.get(
                f"https://wttr.in/{location}?format=%C+%t",
                timeout=5
            )
            if resp.status_code == 200:
                weather = resp.text.strip()
                return {
                    "success": True,
                    "response": f"Weather in {location}: {weather}",
                }
        except Exception as e:
            logger.warning(f"WeatherPlugin: request failed: {e}")

        return {
            "success": False,
            "response": f"Could not fetch weather for {location}.",
        }

    def health_check(self) -> bool:
        try:
            resp = requests.get("https://wttr.in?format=%C", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False