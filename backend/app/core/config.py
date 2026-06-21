import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "chatbot_rag"

    JWT_SECRET_KEY: str = "supersecretkeychangeinproduction12345!"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"
    SIMILARITY_THRESHOLD: float = 0.5
    TOP_K: int = 4
    UPLOAD_DIR: str = "./uploads"

    @property
    def pdf_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR) / "pdf"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def docx_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR) / "docx"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def csv_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR) / "csv"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def xml_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR) / "xml"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def vector_stores_dir(self) -> Path:
        p = Path(self.UPLOAD_DIR) / "vector_stores"
        p.mkdir(parents=True, exist_ok=True)
        return p

settings = Settings()
