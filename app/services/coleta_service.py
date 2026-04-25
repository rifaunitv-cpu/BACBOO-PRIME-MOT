# ============================================================
# app/services/coleta_service.py
# Módulo de coleta de dados do jogo.
#
# ARQUITETURA EXTENSÍVEL:
#   Atualmente usa um simulador realista.
#   Para trocar por scraping real ou API externa, implemente
#   uma nova função _coletar_de_<fonte>() e registre-a em
#   COLETORES no final do arquivo.
# ============================================================

import logging
import random
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.resultado import Resultado
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ------------------------------------------------------------------
# Configurações do simulador
# ------------------------------------------------------------------

# Distribuição de probabilidade dos resultados (soma = 1.0)
# Fácil de ajustar para refletir o jogo real
PROBABILIDADES = {
    "verde": 0.46,
    "vermelho": 0.46,
    "branco": 0.08,
}

# Histórico em memória para simulação de padrões
_ultimo_resultado: Optional[str] = None
_sequencia_atual: int = 0


# ------------------------------------------------------------------
# Funções de coleta
# ------------------------------------------------------------------

def _simular_resultado() -> str:
    """
    Simula um resultado de jogo com distribuição realista.

    Inclui uma pequena lógica de "momentum" para criar padrões
    que o motor de análise possa detectar, tornando o simulador
    mais fiel a jogos reais.
    """
    global _ultimo_resultado, _sequencia_atual

    # Após 3+ resultados iguais, aumenta chance de alternância (mean reversion)
    if _sequencia_atual >= 3 and _ultimo_resultado in ("verde", "vermelho"):
        oposto = "vermelho" if _ultimo_resultado == "verde" else "verde"
        populacao = list(PROBABILIDADES.keys())
        pesos = [
            PROBABILIDADES["branco"],   # branco — probabilidade normal
            0.0,                         # placeholder
            0.0,                         # placeholder
        ]
        # Reconstrói os pesos favorecendo o oposto
        pesos_ajustados = []
        for k in populacao:
            if k == oposto:
                pesos_ajustados.append(PROBABILIDADES[k] + 0.15)
            elif k == _ultimo_resultado:
                pesos_ajustados.append(max(0.01, PROBABILIDADES[k] - 0.15))
            else:
                pesos_ajustados.append(PROBABILIDADES[k])
        resultado = random.choices(populacao, weights=pesos_ajustados, k=1)[0]
    else:
        populacao = list(PROBABILIDADES.keys())
        pesos = list(PROBABILIDADES.values())
        resultado = random.choices(populacao, weights=pesos, k=1)[0]

    # Atualiza estado do simulador
    if resultado == _ultimo_resultado:
        _sequencia_atual += 1
    else:
        _sequencia_atual = 1
    _ultimo_resultado = resultado

    return resultado


def coletar_novo_resultado(db: Session, fonte: str = "simulado") -> Resultado:
    """
    Coleta (ou simula) um novo resultado e persiste no banco.

    Args:
        db:    Sessão ativa do SQLAlchemy
        fonte: Identificador da origem dos dados

    Returns:
        Objeto Resultado persistido no banco
    """
    # Seleciona o coletor conforme a fonte configurada
    coletor = COLETORES.get(fonte, _simular_resultado)

    try:
        valor = coletor()
        logger.debug(f"Resultado coletado via '{fonte}': {valor}")
    except Exception as e:
        logger.error(f"Erro ao coletar resultado de '{fonte}': {e}. Usando simulador.")
        valor = _simular_resultado()

    novo = Resultado(
        resultado=valor,
        fonte=fonte,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"Resultado salvo → id={novo.id} valor='{novo.resultado}'")
    return novo


def buscar_ultimos_resultados(db: Session, limite: int = 100) -> list[Resultado]:
    """
    Retorna os últimos N resultados ordenados do mais recente para o mais antigo.
    """
    return (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(limite)
        .all()
    )


def contar_resultados(db: Session) -> int:
    """Retorna o total de resultados no banco."""
    return db.query(Resultado).count()


# ------------------------------------------------------------------
# Registro de coletores
# Para adicionar uma nova fonte:
#   1. Implemente uma função _coletar_de_minha_fonte() -> str
#   2. Adicione ao dicionário abaixo
#   3. Mude a variável `fonte` ao chamar coletar_novo_resultado()
# ------------------------------------------------------------------

def _coletar_de_api_externa() -> str:
    """
    PLACEHOLDER — integração com API real.
    Implemente aqui a chamada HTTP ao endpoint do jogo.

    Exemplo:
        import httpx
        resp = httpx.get("https://api.jogo.com/ultimo-resultado", timeout=5)
        resp.raise_for_status()
        return resp.json()["resultado"]
    """
    raise NotImplementedError("Integração com API externa ainda não implementada.")


def _coletar_via_scraping() -> str:
    """
    PLACEHOLDER — scraping de site do jogo.
    Implemente aqui usando requests + BeautifulSoup ou Playwright.
    """
    raise NotImplementedError("Scraping ainda não implementado.")


COLETORES = {
    "simulado": _simular_resultado,
    "api_externa": _coletar_de_api_externa,
    "scraping": _coletar_via_scraping,
}
