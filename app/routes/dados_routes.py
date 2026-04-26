# ============================================================
# app/routes/dados_routes.py
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
    limite: int = Query(default=50, ge=1, le=500),
    resultado_filtro: Optional[str] = Query(default=None, alias="resultado"),
    db: Session = Depends(get_db),
):
    query = db.query(Resultado).order_by(Resultado.timestamp.desc())

    if resultado_filtro:
        query = query.filter(Resultado.resultado.ilike(f"%{resultado_filtro}%"))

    registros = query.limit(limite).all()

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
    fonte: str = Query(default="scraping"),
    db: Session = Depends(get_db),
):
    try:
        resultado = coletar_novo_resultado(db, fonte=fonte)
        if resultado is None:
            raise HTTPException(status_code=400, detail="Coleta não retornou resultado novo")
        return {
            "mensagem": "Coleta realizada com sucesso",
            "resultado": resultado.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro na coleta manual: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@router.get("/estatisticas", summary="Estatísticas dos resultados")
def get_estatisticas(db: Session = Depends(get_db)):
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

    ultimos = buscar_ultimos_resultados(db, limite=10)
    sequencia_atual = None
    if ultimos:
        ultimo_val = ultimos[0].resultado
        streak = sum(1 for r in ultimos if r.resultado == ultimo_val)
        sequencia_atual = {"valor": ultimo_val, "contagem": streak}

    return {
        "total": total,
        "distribuicao": distribuicao,
        "sequencia_atual": sequencia_atual,
        "ultimos_10": [r.to_dict() for r in ultimos],
    }
