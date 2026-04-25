# ============================================================
# app/config.py
# Configurações centralizadas usando Pydantic Settings
# ============================================================

import logging
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Todas as variáveis de ambiente do projeto.
    Lidas automaticamente do arquivo .env ou do ambiente do sistema.
    """

    # --- Banco de dados ---
    database_url: str = "postgresql://postgres:postgres@db:5432/signal_db"

    # --- Telegram ---
    telegram_token: str = ""
    telegram_chat_id: str = ""

    # --- Aplicação ---
    app_env: str = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-key-troque-em-producao"

    # --- Scheduler ---
    collect_interval_seconds: int = 30
    signal_min_confidence: float = 60.0

    # --- CORS ---
    frontend_origin: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna instância singleton das configurações.
    O decorator lru_cache garante que o .env é lido apenas uma vez.
    """
    return Settings()


def setup_logging(settings: Settings) -> None:
    """Configura o sistema de logs da aplicação."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
