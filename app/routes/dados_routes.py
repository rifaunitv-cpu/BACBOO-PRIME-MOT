# ============================================================
# app/routes/dados_routes.py
# Rotas relacionadas a coleta e consulta de dados
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.resultado import Resultado
from app.services.coleta_service import (
    coletar_novo_resultado,
    buscar_ultimos_resultados,
    contar_resultados,
)

router = APIRouter(prefix="/dados", tags=["Dados"])
logger = logging.getLogger(__name__)


@router.get("/", summary="Últimos resultados coletados")
def get_dados(
    limite: int = Query(default=50, ge=1, le=500, description="Número de resultados a retornar"),
    resultado_filtro: Optional[str] = Query(
        default=None,
        alias="resultado",
        description="Filtra por valor (ex: verde, vermelho, branco)",
    ),
    db: Session = Depends(get_db),
):
    """
    Retorna os últimos resultados coletados do jogo.
    Suporta filtro por tipo de resultado e paginação por limite.
    """
    query = db.query(Resultado).order_by(Resultado.timestamp.desc())

    if resultado_filtro:
        query = query.filter(
            Resultado.resultado.ilike(f"%{resultado_filtro}%")
        )

    registros = query.limit(limite).all()

    # Agrega contagens por tipo para estatísticas rápidas
    contagens = (
        db.query(Resultado.resultado, func.count(Resultado.id).label("total"))
        .group_by(Resultado.resultado)
        .all()
    )

    return {
        "total_geral": contar_resultados(db),
        "retornados": len(registros),
        "contagens_por_tipo": {r.resultado: r.total for r in contagens},
        "dados": [r.to_dict() for r in registros],
    }


@router.post("/coletar", summary="Força coleta manual de um resultado")
def post_coletar(
    fonte: str = Query(default="simulado", description="Fonte da coleta: simulado | api_externa | scraping"),
    db: Session = Depends(get_db),
):
    """
    Força a coleta manual de um novo resultado.
    Útil para testes ou para "puxar" um dado imediatamente sem esperar o scheduler.
    """
    try:
        resultado = coletar_novo_resultado(db, fonte=fonte)
        logger.info(f"Coleta manual bem-sucedida: {resultado}")
        return {
            "mensagem": "Coleta realizada com sucesso",
            "resultado": resultado.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro na coleta manual: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno na coleta: {e}")


@router.get("/estatisticas", summary="Estatísticas dos resultados")
def get_estatisticas(db: Session = Depends(get_db)):
    """
    Retorna estatísticas agregadas dos resultados:
    - Distribuição percentual por tipo
    - Sequência atual
    - Últimas 10 entradas
    """
    total = contar_resultados(db)
    if total == 0:
        return {"total": 0, "distribuicao": {}, "sequencia_atual": None, "ultimos_10": []}

    contagens = (
        db.query(Resultado.resultado, func.count(Resultado.id).label("total"))
        .group_by(Resultado.resultado)
        .all()
    )
    distribuicao = {
        r.resultado: {
            "contagem": r.total,
            "percentual": round((r.total / total) * 100, 2),
        }
        for r in contagens
    }

    # Calcula a sequência atual (streak do último resultado)
    ultimos = buscar_ultimos_resultados(db, limite=10)
    sequencia_atual = None
    if ultimos:
        ultimo_val = ultimos[0].resultado
        streak = 0
        for r in ultimos:
            if r.resultado == ultimo_val:
                streak += 1
            else:
                break
        sequencia_atual = {"valor": ultimo_val, "contagem": streak}

    return {
        "total": total,
        "distribuicao": distribuicao,
        "sequencia_atual": sequencia_atual,
        "ultimos_10": [r.to_dict() for r in ultimos],
    }
