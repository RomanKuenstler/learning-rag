from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    postgres_db: str = os.getenv("POSTGRES_DB", "rag")
    postgres_user: str = os.getenv("POSTGRES_USER", "rag")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "rag")
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = _get_int("POSTGRES_PORT", 5432)
    qdrant_url: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "rag_chunks")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "http://host.docker.internal:11434/v1")
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "dummy")
    embedding_max_input_tokens: int = _get_int("EMBEDDING_MAX_INPUT_TOKENS", 400)
    llm_model: str = os.getenv("LLM_MODEL", "huggingface.co/qwen/qwen2.5-coder-3b-instruct-gguf:Q4_K_M")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "dummy")
    llm_timeout_seconds: float = _get_float("LLM_TIMEOUT_SECONDS", 180.0)
    chunk_size: int = _get_int("CHUNK_SIZE", 600)
    chunk_overlap: int = _get_int("CHUNK_OVERLAP", 100)
    watch_interval: int = _get_int("WATCH_INTERVAL", 10)
    retrieval_score_threshold: float = _get_float("RETRIEVAL_SCORE_THRESHOLD", 0.70)
    retrieval_min_results: int = _get_int("RETRIEVAL_MIN_RESULTS", 2)
    retrieval_max_results: int = _get_int("RETRIEVAL_MAX_RESULTS", 8)
    history_limit: int = _get_int("CHAT_HISTORY_LIMIT", _get_int("HISTORY_LIMIT", 5))
    default_assistant_mode: str = os.getenv("DEFAULT_ASSISTANT_MODE", "simple").lower()
    enable_refine_mode: bool = _get_bool("ENABLE_REFINE_MODE", True)
    enable_thinking_mode: bool = _get_bool("ENABLE_THINKING_MODE", True)
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = _get_int("API_PORT", 8000)
    embedder_api_host: str = os.getenv("EMBEDDER_API_HOST", "0.0.0.0")
    embedder_api_port: int = _get_int("EMBEDDER_API_PORT", 8001)
    embedder_service_url: str = os.getenv("EMBEDDER_SERVICE_URL", "http://embedder:8001")
    cors_allowed_origins: str = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000",
    )
    enable_ocr: bool = _get_bool("ENABLE_OCR", True)
    pdf_ocr_mode: str = os.getenv("PDF_OCR_MODE", "fallback").lower()
    pdf_min_extracted_chars: int = _get_int("PDF_MIN_EXTRACTED_CHARS", 500)
    pdf_min_avg_chars_per_page: int = _get_int("PDF_MIN_AVG_CHARS_PER_PAGE", 150)
    pdf_enable_column_detection: bool = _get_bool("PDF_ENABLE_COLUMN_DETECTION", True)
    pdf_render_scale: float = _get_float("PDF_RENDER_SCALE", 2.0)
    ocr_language: str = os.getenv("OCR_LANGUAGE", "eng")
    ocr_enable_preprocessing: bool = _get_bool("OCR_ENABLE_PREPROCESSING", True)
    ocr_preprocess_grayscale: bool = _get_bool("OCR_PREPROCESS_GRAYSCALE", True)
    ocr_preprocess_threshold: bool = _get_bool("OCR_PREPROCESS_THRESHOLD", True)
    ocr_preprocess_denoise: bool = _get_bool("OCR_PREPROCESS_DENOISE", False)
    ocr_preprocess_contrast: bool = _get_bool("OCR_PREPROCESS_CONTRAST", True)
    html_cleaning_strict: bool = _get_bool("HTML_CLEANING_STRICT", True)
    epub_skip_front_matter: bool = _get_bool("EPUB_SKIP_FRONT_MATTER", True)
    epub_remove_repeated_chrome: bool = _get_bool("EPUB_REMOVE_REPEATED_CHROME", True)
    epub_fallback_scan_enabled: bool = _get_bool("EPUB_FALLBACK_SCAN_ENABLED", True)
    index_schema_version: int = _get_int("INDEX_SCHEMA_VERSION", 2)
    processor_version: int = _get_int("PROCESSOR_VERSION", 2)
    normalization_version: int = _get_int("NORMALIZATION_VERSION", 2)
    extraction_strategy_version: int = _get_int("EXTRACTION_STRATEGY_VERSION", _get_int("PROCESSOR_VERSION", 2))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    data_dir: str = os.getenv("DATA_DIR", "/app/data")
    max_upload_files: int = _get_int("MAX_UPLOAD_FILES", 5)
    allowed_upload_extensions: str = os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".txt,.md,.html,.htm,.pdf,.epub")
    upload_max_file_size_mb: int = _get_int("UPLOAD_MAX_FILE_SIZE_MB", 50)
    attachment_max_files: int = _get_int("ATTACHMENT_MAX_FILES", 3)
    attachment_max_total_chars: int = _get_int("ATTACHMENT_MAX_TOTAL_CHARS", 15000)
    enable_attachment_ocr: bool = _get_bool("ENABLE_ATTACHMENT_OCR", True)
    attachment_allowed_extensions: str = os.getenv(
        "ATTACHMENT_ALLOWED_EXTENSIONS",
        ".txt,.md,.html,.htm,.pdf,.epub,.csv,.png,.jpg,.jpeg,.webp",
    )
    default_tag: str = os.getenv("DEFAULT_TAG", "default")
    jwt_secret: str = os.getenv("JWT_SECRET", "supersecretkey")
    jwt_expiration_minutes: int = _get_int("JWT_EXPIRATION_MINUTES", 120)
    jwt_refresh_threshold_minutes: int = _get_int("JWT_REFRESH_THRESHOLD_MINUTES", 60)
    jwt_max_lifetime_minutes: int = _get_int("JWT_MAX_LIFETIME_MINUTES", 720)
    password_salt: str = os.getenv("PASSWORD_SALT", "%vSp3$")
    users_file: str = os.getenv("USERS_FILE", "/app/users.json")
    courses_dir: str = os.getenv("COURSES_DIR", "courses")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def processing_signature(self) -> str:
        parts = [
            f"chunk_size={self.chunk_size}",
            f"chunk_overlap={self.chunk_overlap}",
            f"index_schema_version={self.index_schema_version}",
            f"processor_version={self.processor_version}",
            f"normalization_version={self.normalization_version}",
            f"extraction_strategy_version={self.extraction_strategy_version}",
            f"pdf_ocr_mode={self.pdf_ocr_mode}",
            f"enable_ocr={self.enable_ocr}",
            f"html_cleaning_strict={self.html_cleaning_strict}",
            f"epub_skip_front_matter={self.epub_skip_front_matter}",
            f"epub_remove_repeated_chrome={self.epub_remove_repeated_chrome}",
            f"epub_fallback_scan_enabled={self.epub_fallback_scan_enabled}",
        ]
        return "|".join(parts)

    @property
    def allowed_upload_extension_set(self) -> set[str]:
        return {
            extension.strip().lower()
            for extension in self.allowed_upload_extensions.split(",")
            if extension.strip()
        }

    @property
    def attachment_allowed_extension_set(self) -> set[str]:
        return {
            extension.strip().lower()
            for extension in self.attachment_allowed_extensions.split(",")
            if extension.strip()
        }

    @property
    def available_assistant_modes(self) -> list[str]:
        modes = ["simple"]
        if self.enable_refine_mode:
            modes.append("refine")
        if self.enable_thinking_mode:
            modes.append("thinking")
        return modes


def get_settings() -> Settings:
    return Settings()
