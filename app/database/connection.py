# ============================================================
# app/database/connection.py
# Configuração da conexão com PostgreSQL via SQLAlchemy
# ============================================================

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Cria o engine do SQLAlchemy.
# pool_pre_ping=True verifica se a conexão está viva antes de usá-la.
# Essencial para containers que podem reiniciar.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=(settings.app_env == "development"),  # Loga SQL apenas em dev
)

# Fábrica de sessões — cada requisição HTTP obtém sua própria sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM do projeto."""
    pass


def get_db():
    """
    Dependency injection do FastAPI.
    Fornece uma sessão de banco de dados e garante que ela seja fechada
    ao final da requisição, mesmo em caso de erro.

    Uso nos endpoints:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """
    Cria todas as tabelas definidas nos modelos ORM.
    Chamado na inicialização da aplicação.
    """
    from app.models import resultado, sinal  # noqa: F401 — importa para registrar metadados

    logger.info("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas criadas com sucesso.")


def check_db_connection() -> bool:
    """Testa a conexão com o banco de dados. Retorna True se OK."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Falha na conexão com o banco: {e}")
        return False
