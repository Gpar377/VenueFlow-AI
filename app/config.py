"""
VenueFlow AI — Configuration & Settings
Refactored using pydantic-settings for enterprise-grade validation.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables (.env).
    Pydantic handles type conversion and validation automatically.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # ── Google AI ──────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 1024

    # ── Google Maps (optional) ────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = ""

    # ── Firebase (optional) ───────────────────────────────────
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_API_KEY: str = ""
    FIREBASE_DATABASE_URL: str = ""

    # ── Server ────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Simulation ────────────────────────────────────────────
    VENUE_CAPACITY: int = 50000
    SIMULATION_TICK_SECONDS: int = 5
    MAX_QUEUE_WAIT_MINUTES: int = 45

    # ── Computed Properties ───────────────────────────────────
    @property
    def has_gemini(self) -> bool:
        """Check if a valid Gemini API key is present."""
        k = self.GEMINI_API_KEY
        return bool(k and k != "your_gemini_api_key_here" and len(k) > 10)

    @property
    def has_maps(self) -> bool:
        return bool(self.GOOGLE_MAPS_API_KEY)

    @property
    def has_firebase(self) -> bool:
        return bool(self.FIREBASE_PROJECT_ID and self.FIREBASE_API_KEY)


# ── Global Instance ───────────────────────────────────────────
settings = Settings()
