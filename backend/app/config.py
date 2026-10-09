import json
import os
from pathlib import Path
from typing import Dict, Any, List
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    RATES_CONFIG_PATH: str = "config/rates.json"
    MOCK_CLASSIFICATION: bool = False

    model_config = {
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

def get_rates_config(config_path: str = None) -> Dict[str, Any]:
    """Load rates, bounds, and caps from JSON config file."""
    if config_path is None:
        config_path = os.getenv("RATES_CONFIG_PATH", "config/rates.json")
    
    path = Path(config_path)
    if not path.is_absolute():
        path = BASE_DIR / path

    if not path.exists():
        # Fallback default configuration if file is missing
        return {
            "rates_per_100g": {
                "pet_bottle": 100,
                "aluminium_can": 150,
                "rigid_plastic": 80,
                "snack_wrapper": 50,
                "non_recyclable": 0,
                "no_item": 0
            },
            "weight_bounds_g": {
                "pet_bottle": { "min": 8.0, "max": 60.0 },
                "aluminium_can": { "min": 8.0, "max": 25.0 },
                "rigid_plastic": { "min": 5.0, "max": 150.0 },
                "snack_wrapper": { "min": 1.0, "max": 12.0 }
            },
            "min_confidence": 0.70,
            "points_per_rupee": 100,
            "cooldown_seconds": 5,
            "daily_caps": {
                "max_drops": 30,
                "max_grams": 1000.0
            }
        }

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

settings = Settings()
