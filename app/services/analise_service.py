# ============================================================
# app/services/analise_service.py
# Motor de análise de padrões e geração de sinais.
#
# ALGORITMOS DISPONÍVEIS:
#   1. regra_simples  — detecção de padrões por repetição/alternância
#   2. random_forest  — modelo ML (scikit-learn) treinado on-the-fly
# ============================================================

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.resultado import Resultado
from app.models.sinal import Sinal
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Mínimo de dados históricos para tentar análise
MIN_HISTORICO = 10
# Janela de contexto usada nos dois algoritmos
JANELA = 20


# ------------------------------------------------------------------
# Estrutura de retorno
# ------------------------------------------------------------------

@dataclass
class ResultadoAnalise:
    """Resultado retornado pelo motor de análise."""
    sinal_gerado: bool
    tipo: str
    confianca: float
    algoritmo: str
    descricao: str


# ------------------------------------------------------------------
# Helpers de feature engineering
# ------------------------------------------------------------------

def _codificar(resultado: str) -> int:
    """Codifica string do resultado em inteiro."""
    mapa = {"verde": 1, "vermelho": -1, "branco": 0}
    return mapa.get(resultado.lower(), 0)


def _extrair_features(serie: list[int]) -> dict:
    """
    Extrai features numéricas de uma série de resultados codificados.
    Usadas tanto pela regra simples quanto pelo Random Forest.
    """
    arr = np.array(serie)
    n = len(arr)
    return {
        "ultimo": arr[-1] if n >= 1 else 0,
        "penultimo": arr[-2] if n >= 2 else 0,
        "antepenultimo": arr[-3] if n >= 3 else 0,
        "soma_5": int(arr[-5:].sum()) if n >= 5 else 0,
        "soma_10": int(arr[-10:].sum()) if n >= 10 else 0,
        "media_5": float(arr[-5:].mean()) if n >= 5 else 0.0,
        "std_5": float(arr[-5:].std()) if n >= 5 else 0.0,
        "streak": _calcular_streak(arr),
        "alternancia_3": _calcular_alternancia(arr, 3),
    }


def _calcular_streak(arr: np.ndarray) -> int:
    """
    Conta quantos resultados iguais consecutivos existem no final.
    Retorno positivo = streak de +1 (verde), negativo = streak de -1 (vermelho).
    """
    if len(arr) == 0:
        return 0
    streak = 1
    for i in range(len(arr) - 2, -1, -1):
        if arr[i] == arr[-1]:
            streak += 1
        else:
            break
    return streak * int(arr[-1])


def _calcular_alternancia(arr: np.ndarray, n: int) -> int:
    """Conta mudanças de sinal nos últimos N elementos."""
    if len(arr) < n:
        return 0
    tail = arr[-n:]
    return int(sum(1 for i in range(1, len(tail)) if tail[i] != tail[i - 1]))


# ------------------------------------------------------------------
# Algoritmo 1 — Regra simples
# ------------------------------------------------------------------

def _analisar_regra_simples(serie_codificada: list[int]) -> ResultadoAnalise:
    """
    Detecta padrões por heurísticas:
      - 3+ resultados iguais → prediz alternância
      - Alta alternância nos últimos 5 → prediz continuidade da alternância
      - Empate/inconclusivo → sem sinal
    """
    features = _extrair_features(serie_codificada)
    streak = features["streak"]
    alternancia = features["alternancia_3"]
    soma_5 = features["soma_5"]

    # --- Regra 1: streak forte (≥3 iguais) → provável alternância ---
    if abs(streak) >= 3:
        proximo = "vermelho" if streak > 0 else "verde"
        confianca = min(55.0 + (abs(streak) - 3) * 5.0, 80.0)
        return ResultadoAnalise(
            sinal_gerado=True,
            tipo=f"entrada {proximo}",
            confianca=confianca,
            algoritmo="regra_simples",
            descricao=(
                f"Streak de {abs(streak)}x '{('verde' if streak > 0 else 'vermelho')}' detectado. "
                f"Probabilidade de alternância elevada."
            ),
        )

    # --- Regra 2: alta alternância (padrão ziguezague) → prediz continuidade ---
    if alternancia >= 2 and features["ultimo"] != 0:
        proximo = "vermelho" if features["ultimo"] == 1 else "verde"
        confianca = 58.0 + alternancia * 2.0
        return ResultadoAnalise(
            sinal_gerado=True,
            tipo=f"entrada {proximo}",
            confianca=min(confianca, 72.0),
            algoritmo="regra_simples",
            descricao=f"Padrão de alternância detectado nos últimos {alternancia + 1} resultados.",
        )

    # --- Regra 3: desequilíbrio acumulado nos últimos 5 ---
    if abs(soma_5) >= 4:
        proximo = "vermelho" if soma_5 > 0 else "verde"
        confianca = 55.0 + abs(soma_5) * 2.0
        return ResultadoAnalise(
            sinal_gerado=True,
            tipo=f"entrada {proximo}",
            confianca=min(confianca, 70.0),
            algoritmo="regra_simples",
            descricao=f"Desequilíbrio de {soma_5} nos últimos 5 resultados.",
        )

    return ResultadoAnalise(
        sinal_gerado=False,
        tipo="",
        confianca=0.0,
        algoritmo="regra_simples",
        descricao="Nenhum padrão forte identificado.",
    )


# ------------------------------------------------------------------
# Algoritmo 2 — Random Forest (scikit-learn)
# ------------------------------------------------------------------

# Instância do modelo (treinado em memória, se houver dados suficientes)
_modelo_rf = None
_modelo_treinado_em: Optional[datetime] = None


def _treinar_random_forest(serie: list[int]) -> bool:
    """
    Treina um RandomForestClassifier usando a série histórica.
    Feature = janela deslizante de JANELA posições.
    Label = próximo resultado.

    Retorna True se o treino foi bem-sucedido.
    """
    global _modelo_rf, _modelo_treinado_em

    try:
        from sklearn.ensemble import RandomForestClassifier

        # Cria dataset com janela deslizante
        X, y = [], []
        for i in range(JANELA, len(serie)):
            janela = serie[i - JANELA:i]
            features = list(_extrair_features(janela).values())
            X.append(features)
            y.append(serie[i])

        if len(X) < 30:
            logger.debug("Dados insuficientes para treinar Random Forest.")
            return False

        X_arr = np.array(X)
        y_arr = np.array(y)

        _modelo_rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            class_weight="balanced",
        )
        _modelo_rf.fit(X_arr, y_arr)
        _modelo_treinado_em = datetime.now(timezone.utc)
        logger.info(f"Random Forest treinado com {len(X)} amostras.")
        return True

    except ImportError:
        logger.warning("scikit-learn não disponível. Usando apenas regra simples.")
        return False
    except Exception as e:
        logger.error(f"Erro ao treinar Random Forest: {e}")
        return False


def _analisar_random_forest(serie_codificada: list[int]) -> ResultadoAnalise:
    """
    Usa o Random Forest treinado para prever o próximo resultado.
    Se o modelo não estiver treinado, treina antes de prever.
    """
    global _modelo_rf

    # Treina o modelo se ainda não foi treinado ou se passou mais de 1 hora
    if _modelo_rf is None:
        if not _treinar_random_forest(serie_codificada):
            return ResultadoAnalise(
                sinal_gerado=False,
                tipo="",
                confianca=0.0,
                algoritmo="random_forest",
                descricao="Modelo RF não treinado (dados insuficientes).",
            )

    try:
        janela_atual = serie_codificada[-JANELA:]
        features = list(_extrair_features(janela_atual).values())
        X_pred = np.array(features).reshape(1, -1)

        proba = _modelo_rf.predict_proba(X_pred)[0]
        classes = _modelo_rf.classes_
        idx_max = np.argmax(proba)
        classe_predita = classes[idx_max]
        confianca = float(proba[idx_max]) * 100.0

        mapa_inverso = {1: "verde", -1: "vermelho", 0: "branco"}
        tipo = f"entrada {mapa_inverso.get(int(classe_predita), str(classe_predita))}"

        logger.debug(f"RF prediz {tipo} com {confianca:.1f}% de confiança")

        return ResultadoAnalise(
            sinal_gerado=confianca >= settings.signal_min_confidence,
            tipo=tipo,
            confianca=confianca,
            algoritmo="random_forest",
            descricao=f"Random Forest prediz '{tipo}' com {confianca:.1f}% de confiança.",
        )

    except Exception as e:
        logger.error(f"Erro na predição do Random Forest: {e}")
        return ResultadoAnalise(
            sinal_gerado=False,
            tipo="",
            confianca=0.0,
            algoritmo="random_forest",
            descricao=f"Erro na predição: {e}",
        )


# ------------------------------------------------------------------
# Função principal de análise
# ------------------------------------------------------------------

def analisar_e_gerar_sinal(db: Session) -> Optional[Sinal]:
    """
    Ponto de entrada principal do motor de análise.

    Fluxo:
      1. Busca histórico recente do banco
      2. Codifica os resultados em série numérica
      3. Aplica regra simples
      4. Se dados suficientes, aplica Random Forest
      5. Escolhe o sinal com maior confiança
      6. Persiste o sinal no banco se confiança ≥ mínimo configurado

    Returns:
        Objeto Sinal persistido, ou None se nenhum sinal foi gerado.
    """
    # Busca histórico
    registros = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(200)
        .all()
    )

    if len(registros) < MIN_HISTORICO:
        logger.info(
            f"Histórico insuficiente para análise ({len(registros)}/{MIN_HISTORICO})."
        )
        return None

    # Converte para série cronológica (mais antigo → mais recente)
    serie_str = [r.resultado for r in reversed(registros)]
    serie_cod = [_codificar(r) for r in serie_str]

    logger.debug(f"Analisando série de {len(serie_cod)} resultados.")

    # Aplica algoritmos
    resultado_simples = _analisar_regra_simples(serie_cod)
    resultado_rf = _analisar_random_forest(serie_cod) if len(serie_cod) >= JANELA + 30 else None

    # Seleciona o melhor sinal
    candidatos = [resultado_simples]
    if resultado_rf and resultado_rf.sinal_gerado:
        candidatos.append(resultado_rf)

    melhor = max(candidatos, key=lambda r: r.confianca)

    logger.info(
        f"Melhor análise: algoritmo={melhor.algoritmo} "
        f"tipo='{melhor.tipo}' confianca={melhor.confianca:.1f}% "
        f"sinal_gerado={melhor.sinal_gerado}"
    )

    if not melhor.sinal_gerado or melhor.confianca < settings.signal_min_confidence:
        logger.info("Confiança insuficiente — nenhum sinal gerado.")
        return None

    # Persiste o sinal
    novo_sinal = Sinal(
        tipo=melhor.tipo,
        confianca=melhor.confianca,
        algoritmo=melhor.algoritmo,
        descricao=melhor.descricao,
        enviado_telegram=False,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(novo_sinal)
    db.commit()
    db.refresh(novo_sinal)

    logger.info(f"Sinal gerado e salvo → {novo_sinal}")
    return novo_sinal


def calcular_taxa_acerto(db: Session) -> dict:
    """
    Calcula estatísticas de acerto dos sinais.
    Considera apenas sinais com resultado verificado (acertou != None).
    """
    sinais = db.query(Sinal).filter(Sinal.acertou.isnot(None)).all()

    if not sinais:
        return {"total_verificados": 0, "acertos": 0, "taxa_acerto": 0.0}

    acertos = sum(1 for s in sinais if s.acertou is True)
    taxa = (acertos / len(sinais)) * 100.0

    return {
        "total_verificados": len(sinais),
        "acertos": acertos,
        "erros": len(sinais) - acertos,
        "taxa_acerto": round(taxa, 2),
    }
