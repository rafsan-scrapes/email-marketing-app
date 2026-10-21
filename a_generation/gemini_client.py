"""Gemini API client wrapper for the email marketing app."""

from dataclasses import dataclass
from typing import Optional
import requests
import logging

from a_projects.settings_utils import get_gemini_api_key

logger = logging.getLogger(__name__)

# Primary and fallback free-tier model IDs (re-verify against ai.google.dev/pricing before each pass)
GEMINI_MODEL_PRIMARY = "gemini-3.1-flash-lite"
GEMINI_MODEL_FALLBACK = "gemini-2.5-flash-lite"
GEMINI_ENDPOINT_PRIMARY = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_PRIMARY}:generateContent"


@dataclass
class GeminiResult:
    """Result of a Gemini API call."""
    success: bool
    raw_text: Optional[str] = None
    error_message: Optional[str] = None


def call_gemini(prompt: str) -> GeminiResult:
    """
    Call the Gemini API with the given prompt.
    
    Args:
        prompt: The full prompt text to send to Gemini (including formatting instructions)
        
    Returns:
        GeminiResult with success status, raw response text, and/or error message
    """
    api_key = get_gemini_api_key()
    
    if not api_key:
        return GeminiResult(
            success=False,
            error_message="Gemini API key not configured. Please set it in Settings."
        )
    
    url_primary = f"{GEMINI_ENDPOINT_PRIMARY}?key={api_key}"
    url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_FALLBACK}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    def _post(url):
        try:
            return requests.post(url, json=payload, headers=headers, timeout=30)
        except requests.exceptions.Timeout:
            return None, "timeout"
        except requests.exceptions.ConnectionError:
            return None, "connection"
        except requests.exceptions.RequestException as e:
            logger.exception("Gemini request failed")
            return None, f"request_failed:{e}"
    
    # First attempt with primary model
    response, error_tag = _post(url_primary)
    if error_tag:
        if error_tag == "timeout":
            return GeminiResult(success=False, error_message="Request timed out. Please try again.")
        elif error_tag == "connection":
            return GeminiResult(success=False, error_message="Network error. Please check your connection and try again.")
        else:
            return GeminiResult(success=False, error_message=f"Request failed: {error_tag}")
    
    # On rate limit (429), retry once with fallback model
    if response.status_code == 429:
        response, error_tag = _post(url_fallback)
        if error_tag:
            if error_tag == "timeout":
                return GeminiResult(success=False, error_message="Request timed out. Please try again.")
            elif error_tag == "connection":
                return GeminiResult(success=False, error_message="Network error. Please check your connection and try again.")
            else:
                return GeminiResult(success=False, error_message=f"Request failed: {error_tag}")
    
    # Handle HTTP errors
    if response.status_code == 400:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "Invalid request")
            if "API key" in error_msg or "API_KEY" in error_msg:
                return GeminiResult(
                    success=False,
                    error_message="Invalid or missing Gemini API key. Please check your key in Settings."
                )
            return GeminiResult(
                success=False,
                error_message=f"Invalid request: {error_msg}"
            )
        except ValueError:
            return GeminiResult(
                success=False,
                error_message="Invalid request (400)"
            )
    
    if response.status_code == 401:
        return GeminiResult(
            success=False,
            error_message="Invalid or missing Gemini API key. Please check your key in Settings."
        )
    
    if response.status_code == 429:
        return GeminiResult(
            success=False,
            error_message="Rate limit exceeded. Please wait a moment and try again."
        )
    
    if response.status_code == 403:
        return GeminiResult(
            success=False,
            error_message="Access denied. Please verify your API key has the necessary permissions."
        )
    
    if response.status_code >= 500:
        return GeminiResult(
            success=False,
            error_message="Gemini service temporarily unavailable. Please try again later."
        )
    
    if response.status_code != 200:
        try:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            return GeminiResult(
                success=False,
                error_message=f"API error: {error_msg}"
            )
        except ValueError:
            return GeminiResult(
                success=False,
                error_message=f"HTTP {response.status_code}"
            )
    
    # Parse successful response
    try:
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return GeminiResult(
                success=False,
                error_message="No response generated by Gemini"
            )
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return GeminiResult(
                success=False,
                error_message="Empty response from Gemini"
            )
        
        # Combine all parts (usually just one for text generation)
        raw_text = "".join(part.get("text", "") for part in parts)
        
        return GeminiResult(
            success=True,
            raw_text=raw_text
        )
    except (KeyError, IndexError, ValueError) as e:
        logger.exception("Failed to parse Gemini response")
        return GeminiResult(
            success=False,
            error_message=f"Failed to parse response: {str(e)}"
        )