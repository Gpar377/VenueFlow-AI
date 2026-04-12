"""
VenueFlow AI — Configuration & Settings
Loads environment variables and provides typed config for the entire application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


class Settings:
    """Application settings loaded from environment."""

    # ── Google AI ──────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.7"))
    AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "1024"))

    # ── Google Maps (optional) ────────────────────────────────
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # ── Firebase (optional) ───────────────────────────────────
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_API_KEY: str = os.getenv("FIREBASE_API_KEY", "")
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL", "")

    # ── Server ────────────────────────────────────────────────
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ── Simulation ────────────────────────────────────────────
    VENUE_CAPACITY: int = int(os.getenv("VENUE_CAPACITY", "50000"))
    SIMULATION_TICK_SECONDS: int = int(os.getenv("SIMULATION_TICK_SECONDS", "5"))
    MAX_QUEUE_WAIT_MINUTES: int = int(os.getenv("MAX_QUEUE_WAIT_MINUTES", "45"))

    # ── Feature Flags ─────────────────────────────────────────
    @property
    def has_gemini(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY != "your_gemini_api_key_here")

    @property
    def has_maps(self) -> bool:
        return bool(self.GOOGLE_MAPS_API_KEY)

    @property
    def has_firebase(self) -> bool:
        return bool(self.FIREBASE_PROJECT_ID and self.FIREBASE_API_KEY)

    def validate(self) -> None:
        """Validate critical settings on startup."""
        if not self.has_gemini:
            print("(!) WARNING: No GEMINI_API_KEY set. AI features will use fallback responses.")
            print("   Get a FREE key at: https://aistudio.google.com")


settings = Settings()
