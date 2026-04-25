# ============================================================
# app/routes/sinais_routes.py
# Rotas relacionadas a geração, consulta e atualização de sinais
# ============================================================

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.sinal import Sinal
from app.services.analise_service import analisar_e_gerar_sinal, calcular_taxa_acerto
from app.services.telegram_service import enviar_sinal

router = APIRouter(prefix="/sinais", tags=["Sinais"])
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Schemas Pydantic (validação de entrada/saída)
# ------------------------------------------------------------------

class AtualizarAcertoRequest(BaseModel):
    acertou: bool


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/", summary="Lista sinais gerados")
def get_sinais(
    limite: int = Query(default=20, ge=1, le=200),
    apenas_enviados: bool = Query(default=False, description="Filtra apenas sinais enviados ao Telegram"),
    algoritmo: Optional[str] = Query(default=None, description="Filtra por algoritmo (regra_simples | random_forest)"),
    db: Session = Depends(get_db),
):
    """
    Retorna os sinais gerados pelo motor de análise.
    Inclui estatísticas de taxa de acerto ao final.
    """
    query = db.query(Sinal).order_by(Sinal.timestamp.desc())

    if apenas_enviados:
        query = query.filter(Sinal.enviado_telegram == True)  # noqa: E712

    if algoritmo:
        query = query.filter(Sinal.algoritmo == algoritmo)

    sinais = query.limit(limite).all()
    taxa = calcular_taxa_acerto(db)

    return {
        "total_retornado": len(sinais),
        "taxa_acerto": taxa,
        "sinais": [s.to_dict() for s in sinais],
    }


@router.post("/gerar", summary="Força geração manual de sinal")
def post_gerar_sinal(
    enviar_telegram: bool = Query(
        default=False,
        description="Se True, envia o sinal ao Telegram imediatamente",
    ),
    db: Session = Depends(get_db),
):
    """
    Força uma análise imediata do histórico e gera um sinal se houver padrão.
    Opcional: envia o sinal ao Telegram.
    """
    sinal = analisar_e_gerar_sinal(db)

    if sinal is None:
        return {
            "mensagem": "Análise realizada mas nenhum sinal com confiança suficiente foi gerado.",
            "sinal": None,
        }

    resultado = {"mensagem": "Sinal gerado com sucesso", "sinal": sinal.to_dict()}

    if enviar_telegram:
        enviado = enviar_sinal(sinal)
        if enviado:
            sinal.enviado_telegram = True
            db.commit()
        resultado["telegram_enviado"] = enviado

    return resultado


@router.patch("/{sinal_id}/acerto", summary="Registra se o sinal acertou")
def patch_acerto(
    sinal_id: int = Path(..., description="ID do sinal"),
    body: AtualizarAcertoRequest = ...,
    db: Session = Depends(get_db),
):
    """
    Atualiza o campo `acertou` de um sinal após verificar o resultado real.
    Útil para calcular a taxa de acerto histórica.
    """
    sinal = db.query(Sinal).filter(Sinal.id == sinal_id).first()
    if sinal is None:
        raise HTTPException(status_code=404, detail=f"Sinal {sinal_id} não encontrado.")

    sinal.acertou = body.acertou
    db.commit()
    db.refresh(sinal)

    logger.info(f"Sinal {sinal_id} atualizado: acertou={body.acertou}")
    return {"mensagem": "Atualizado com sucesso", "sinal": sinal.to_dict()}


@router.get("/taxa-acerto", summary="Taxa de acerto histórica")
def get_taxa_acerto(db: Session = Depends(get_db)):
    """Retorna as estatísticas de acerto de todos os sinais verificados."""
    return calcular_taxa_acerto(db)
