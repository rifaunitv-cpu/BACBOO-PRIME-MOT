# ============================================================
# app/models/sinal.py
# Modelo ORM para armazenar sinais gerados pela análise
# ============================================================

from datetime import datetime
from sqlalchemy import String, DateTime, Float, Boolean, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.connection import Base


class Sinal(Base):
    """
    Representa um sinal de entrada gerado pelo motor de análise.

    Campos:
        id              — PK auto-incrementada
        tipo            — descrição do sinal (ex: "entrada azul", "entrada vermelho")
        confianca       — porcentagem de confiança (0.0 a 100.0)
        algoritmo       — qual algoritmo gerou o sinal
        descricao       — explicação detalhada do padrão detectado
        enviado_telegram— se foi enviado ao Telegram com sucesso
        acertou         — resultado real posterior (None = ainda não verificado)
        gale            — quantos gales já foram usados (0 = nenhum, máx 2)
        timestamp       — quando o sinal foi gerado
    """

    __tablename__ = "sinais"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    confianca: Mapped[float] = mapped_column(Float, nullable=False)
    algoritmo: Mapped[str] = mapped_column(String(50), nullable=False, default="regra_simples")
    descricao: Mapped[str] = mapped_column(Text, nullable=True)
    enviado_telegram: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acertou: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None = pendente
    gale: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0, 1 ou 2
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.tipo,
            "confianca": round(self.confianca, 2),
            "algoritmo": self.algoritmo,
            "descricao": self.descricao,
            "enviado_telegram": self.enviado_telegram,
            "acertou": self.acertou,
            "gale": self.gale,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self) -> str:
        return f"<Sinal id={self.id} tipo='{self.tipo}' confianca={self.confianca:.1f}% gale={self.gale}>"
