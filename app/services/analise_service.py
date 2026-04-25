# ============================================================
# app/services/analise_service.py (CORRIGIDO FINAL)
# ============================================================

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models.resultado import Resultado
from app.models.sinal import Sinal

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 85.0
MIN_HISTORICO = 10
JANELA = 20


@dataclass
class ResultadoAnalise:
    sinal_gerado: bool
    tipo: str
    confianca: float
    algoritmo: str
    descricao: str


def _codificar(resultado: str) -> int:
    mapa = {"verde": 1, "vermelho": -1, "branco": 0}
    return mapa.get(resultado.lower(), 0)


def _extrair_features(serie: list[int]) -> dict:
    arr = np.array(serie)
    n = len(arr)
    return {
        "ultimo": arr[-1] if n >= 1 else 0,
        "penultimo": arr[-2] if n >= 2 else 0,
        "antepenultimo": arr[-3] if n >= 3 else 0,
        "soma_5": int(arr[-5:].sum()) if n >= 5 else 0,
        "media_5": float(arr[-5:].mean()) if n >= 5 else 0.0,
        "streak": _calcular_streak(arr),
    }


def _calcular_streak(arr: np.ndarray) -> int:
    if len(arr) == 0:
        return 0
    streak = 1
    for i in range(len(arr) - 2, -1, -1):
        if arr[i] == arr[-1]:
            streak += 1
        else:
            break
    return streak * int(arr[-1])


# -----------------------------------------
# REGRA SIMPLES (não passa de 80%)
# -----------------------------------------
def _analisar_regra_simples(serie_codificada: list[int]) -> ResultadoAnalise:
    features = _extrair_features(serie_codificada)
    streak = features["streak"]

    if abs(streak) >= 3:
        proximo = "vermelho" if streak > 0 else "verde"
        confianca = min(60 + abs(streak) * 5, 80)

        return ResultadoAnalise(
            True,
            f"entrada {proximo}",
            confianca,
            "regra_simples",
            f"Streak detectado ({abs(streak)})",
        )

    return ResultadoAnalise(False, "", 0.0, "regra_simples", "Sem padrão")


# -----------------------------------------
# RANDOM FOREST
# -----------------------------------------
_modelo_rf = None


def _treinar_random_forest(serie: list[int]) -> bool:
    global _modelo_rf
    try:
        from sklearn.ensemble import RandomForestClassifier

        X, y = [], []
        for i in range(JANELA, len(serie)):
            janela = serie[i - JANELA:i]
            features = list(_extrair_features(janela).values())
            X.append(features)
            y.append(serie[i])

        if len(X) < 30:
            return False

        _modelo_rf = RandomForestClassifier(n_estimators=100)
        _modelo_rf.fit(X, y)
        return True

    except Exception:
        return False


def _analisar_random_forest(serie_codificada: list[int]) -> ResultadoAnalise:
    global _modelo_rf

    if _modelo_rf is None:
        if not _treinar_random_forest(serie_codificada):
            return ResultadoAnalise(False, "", 0.0, "rf", "Sem modelo")

    try:
        janela = serie_codificada[-JANELA:]
        features = list(_extrair_features(janela).values())
        X = np.array(features).reshape(1, -1)

        proba = _modelo_rf.predict_proba(X)[0]
        classes = _modelo_rf.classes_

        idx = np.argmax(proba)
        classe = classes[idx]
        confianca = float(proba[idx]) * 100

        mapa = {1: "verde", -1: "vermelho", 0: "branco"}
        tipo = f"entrada {mapa.get(int(classe))}"

        return ResultadoAnalise(
            confianca >= MIN_CONFIDENCE,
            tipo,
            confianca,
            "rf",
            "Alta probabilidade detectada",
        )

    except Exception as e:
        logger.error(e)
        return ResultadoAnalise(False, "", 0.0, "rf", "erro")


# ============================================================
# FUNÇÃO PRINCIPAL
# ============================================================

def analisar_e_gerar_sinal(db: Session) -> Optional[Sinal]:

    registros = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .limit(200)
        .all()
    )

    if len(registros) < MIN_HISTORICO:
        return None

    serie_str = [r.resultado for r in reversed(registros)]
    serie_cod = [_codificar(r) for r in serie_str]

    r1 = _analisar_regra_simples(serie_cod)
    r2 = _analisar_random_forest(serie_cod)

    melhor = max([r1, r2], key=lambda r: r.confianca)

    if melhor.confianca < MIN_CONFIDENCE:
        logger.info("Ignorado: abaixo de 85%")
        return None

    # 🔥 SALVA APENAS O TIPO LIMPO
    novo = Sinal(
        tipo=melhor.tipo,  # 🔥 IMPORTANTE
        confianca=melhor.confianca,
        algoritmo=melhor.algoritmo,
        descricao=melhor.descricao,
        enviado_telegram=False,
        timestamp=datetime.now(timezone.utc),
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    logger.info(f"Sinal criado: {melhor.tipo} ({melhor.confianca:.1f}%)")

    return novo


# ============================================================
# 🔥 FUNÇÃO QUE FALTAVA (OBRIGATÓRIA)
# ============================================================

def calcular_taxa_acerto(db: Session) -> dict:
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
