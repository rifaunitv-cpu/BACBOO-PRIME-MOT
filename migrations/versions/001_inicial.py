"""Criacao das tabelas iniciais: resultados e sinais

Revision ID: 001_inicial
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_inicial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabela de resultados coletados
    op.create_table(
        "resultados",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resultado", sa.String(50), nullable=False),
        sa.Column("fonte", sa.String(100), nullable=False, server_default="simulado"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resultados_timestamp", "resultados", ["timestamp"])
    op.create_index("ix_resultados_resultado", "resultados", ["resultado"])

    # Tabela de sinais gerados
    op.create_table(
        "sinais",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("confianca", sa.Float(), nullable=False),
        sa.Column("algoritmo", sa.String(50), nullable=False, server_default="regra_simples"),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("enviado_telegram", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("acertou", sa.Boolean(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sinais_timestamp", "sinais", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_sinais_timestamp", table_name="sinais")
    op.drop_table("sinais")
    op.drop_index("ix_resultados_timestamp", table_name="resultados")
    op.drop_index("ix_resultados_resultado", table_name="resultados")
    op.drop_table("resultados")
