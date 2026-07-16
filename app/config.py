"""app/config.py — Centralised configuration"""
import os


class Settings:
    APP_NAME:    str = "Trip Planner"
    APP_VERSION: str = "1.0.0"
    DEBUG:       bool = True
    HOST:        str = "0.0.0.0"
    PORT:        int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./outputs/tripplanner.db"
    DB_PATH:      str = "./outputs/tripplanner.db"

    OUTPUTS_DIR:      str = "outputs"
    ITINERARY_DIR:    str = "outputs/itineraries"

    # Recommendation engine weights
    WEIGHT_RATING:    float = 0.35
    WEIGHT_PRICE:     float = 0.30
    WEIGHT_AMENITIES: float = 0.20
    WEIGHT_REVIEWS:   float = 0.15

    # Itinerary
    DEFAULT_START_HOUR: int = 9   # 9 AM
    MEALS_PER_DAY:      int = 3


settings = Settings()