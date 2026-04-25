# ============================================================
# app/models/resultado.py
# Modelo ORM para armazenar resultados coletados do jogo
# ============================================================

from datetime import datetime
from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.connection import Base


class Resultado(Base):
    """
    Representa um resultado coletado do jogo.

    Campos:
        id          — PK auto-incrementada
        resultado   — valor do resultado (ex: "verde", "vermelho", "branco")
        fonte       — origem do dado (ex: "simulado", "api_externa", "scraping")
        timestamp   — quando o resultado ocorreu no jogo
        criado_em   — quando foi inserido no banco
    """

    __tablename__ = "resultados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resultado: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fonte: Mapped[str] = mapped_column(String(100), nullable=False, default="simulado")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def to_dict(self) -> dict:
        """Serializa o modelo para dicionário (usado nas respostas da API)."""
        return {
            "id": self.id,
            "resultado": self.resultado,
            "fonte": self.fonte,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
        }

    def __repr__(self) -> str:
        return f"<Resultado id={self.id} resultado='{self.resultado}' ts={self.timestamp}>"
