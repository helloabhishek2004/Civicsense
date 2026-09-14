from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve project root deterministically (backend/ -> Civicsense/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent if (_BACKEND_DIR.parent / "models").is_dir() else _BACKEND_DIR


class Settings(BaseSettings):
    """Central application configuration loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/civicsense"

    # API Configuration
    API_ENV: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Security & Limits
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8081",
        "http://localhost:19006",
    ]
    MAX_PAYLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    UPLOADS_DIR: str = "uploads"

    # Image Validation & Protection Limits
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MIN_IMAGE_DIMENSION: int = 64
    MAX_IMAGE_DIMENSION: int = 8192
    MAX_IMAGE_PIXELS: int = 25_000_000  # Decompression-bomb defense limit
    ALLOWED_IMAGE_MIME_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # Text Validation Limits
    MAX_DESCRIPTION_LENGTH: int = 5000
    MAX_REPEATED_CHARACTER_RUN: int = 20

    # Provisional AI Confidence & Review Thresholds
    AI_CONFIDENCE_HIGH_THRESHOLD: float = 0.80
    AI_CONFIDENCE_MEDIUM_THRESHOLD: float = 0.65
    AI_REVIEW_CONFIDENCE_THRESHOLD: float = 0.70
    AI_MODALITY_AGREEMENT_THRESHOLD: float = 0.60
    AI_PROVISIONAL_POLICY: bool = True
    AI_ENABLE_FILENAME_HEURISTICS: bool = False  # Disabled by default to prevent data leakage

    # Similarity & Deduplication Thresholds
    SIMILARITY_TEXT_WEIGHT: float = 0.40
    SIMILARITY_DISTANCE_WEIGHT: float = 0.35
    SIMILARITY_CATEGORY_WEIGHT: float = 0.25
    SIMILARITY_RADIUS_METERS: float = 50.0
    SIMILARITY_HIGH_THRESHOLD: float = 0.70
    SIMILARITY_MEDIUM_THRESHOLD: float = 0.45
    SIMILARITY_EMBEDDING_MODEL_VERSION: str = "all-MiniLM-L6-v2-v1"
    SIMILARITY_MODEL_DIR: str = ""  # resolved at startup relative to PROJECT_ROOT

    # Priority Ranking Weights (provisional, not scientifically validated)
    PRIORITY_SEVERITY_WEIGHT: float = 0.30
    PRIORITY_VOLUME_WEIGHT: float = 0.25
    PRIORITY_UNIQUE_REPORTER_WEIGHT: float = 0.20
    PRIORITY_RECENCY_WEIGHT: float = 0.15
    PERSISTENCE_WEIGHT: float = 0.10

    # Priority component parameters
    PRIORITY_VOLUME_SATURATION: int = 50  # report count at which volume_score ~ 0.95
    PRIORITY_RECENCY_HALF_LIFE_DAYS: float = 7.0  # exponential decay half-life
    PERSISTENCE_MAX_DAYS: float = 90.0  # cap persistence contribution at 90 days

    # Priority threshold mapping (score 0-100 -> PriorityLevel)
    PRIORITY_HIGH_THRESHOLD: float = 65.0
    PRIORITY_MEDIUM_THRESHOLD: float = 40.0
    PRIORITY_LOW_THRESHOLD: float = 15.0

    # Batch recomputation
    PRIORITY_BATCH_SIZE: int = 100

    # Vision Model Configuration
    VISION_MODEL_CHECKPOINT: str = ""  # resolved at startup relative to PROJECT_ROOT
    VISION_EMBEDDING_DIM: int = 576  # MobileNetV3-Small penultimate layer dimension
    VISION_CONFIDENCE_THRESHOLD: float = 0.60
    VISION_ENABLED: bool = True  # Set False to disable vision processing entirely

    # Multimodal Similarity Weights (text + visual + distance + category)
    SIMILARITY_VISUAL_WEIGHT: float = 0.15

    # Visual Safety Policy
    # "strict": visual similarity cannot independently promote to AUTO_LINK
    # "relaxed": visual similarity contributes normally to scoring
    VISUAL_SAFETY_MODE: str = "strict"

    # When strict mode is active, visual similarity cannot cause AUTO_LINK unless
    # the text-only score (without visual) also exceeds this threshold.
    # Set to 0.0 to allow visual to promote only when text score is below medium_threshold.
    VISUAL_AUTO_LINK_MIN_TEXT_SCORE: float = 0.0

    @property
    def similarity_model_path(self) -> Path:
        """Resolve the MiniLM model directory to an absolute path.

        Priority:
          1. Explicit SIMILARITY_MODEL_DIR if non-empty and exists
          2. models/all_minilm_l6_v2 relative to PROJECT_ROOT
          3. models/all_minilm_l6_v2 relative to CWD (legacy fallback)
        """
        if self.SIMILARITY_MODEL_DIR:
            explicit = Path(self.SIMILARITY_MODEL_DIR)
            if explicit.is_absolute():
                return explicit
            return _PROJECT_ROOT / explicit

        project_default = _PROJECT_ROOT / "models" / "all_minilm_l6_v2"
        if project_default.is_dir():
            return project_default

        cwd_default = Path.cwd() / "models" / "all_minilm_l6_v2"
        return cwd_default

    @property
    def vision_model_path(self) -> Path:
        """Resolve the vision model checkpoint to an absolute path.

        Priority:
          1. Explicit VISION_MODEL_CHECKPOINT if non-empty and exists
          2. models/mobilenet_v3_small_v1/exp_b/exp_b_best.pt relative to PROJECT_ROOT
          3. Fallback to PROJECT_ROOT/models/mobilenet_v3_small_v1/exp_b/exp_b_best.pt
        """
        if self.VISION_MODEL_CHECKPOINT:
            explicit = Path(self.VISION_MODEL_CHECKPOINT)
            if explicit.is_absolute():
                return explicit
            return _PROJECT_ROOT / explicit

        project_default = (
            _PROJECT_ROOT / "models" / "mobilenet_v3_small_v1"
            / "exp_b" / "exp_b_best.pt"
        )
        return project_default

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
