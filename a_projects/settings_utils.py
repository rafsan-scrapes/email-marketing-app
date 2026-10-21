"""Helper functions for accessing app settings (e.g., Gemini API key)."""

from a_projects.models import Settings


def get_gemini_api_key() -> str:
    """Return the current Gemini API key from settings, or empty string if not set."""
    settings_obj = Settings.get_settings()
    return settings_obj.gemini_api_key or ''