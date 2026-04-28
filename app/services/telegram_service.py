# ============================================================
# app/services/telegram_service.py
# ============================================================

import logging
import httpx

from app.config import get_settings
from app.models.sinal import Sinal
from app.models.resultado import Resultado

logger = logging.getLogger(__name__)
settings = get_settings()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 10

MAX_GALES = 2


def _build_url(method: str) -> str:
    return TELEGRAM_API_BASE.format(
        token=settings.telegram_token,
        method=method
    )


# ============================================================
# ENVIO BASE
# ============================================================

def _enviar(mensagem: str) -> bool:
    try:
        url = _build_url("sendMessage")
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)
        return response.status_code == 200

    except Exception as e:
        logger.error(f"Erro Telegram: {e}")
        return False


# ============================================================
# HELPERS DE DISPLAY
# ============================================================

def _display_tipo(tipo: str) -> tuple[str, str]:
    """
    Retorna (label_display, emoji) para o tipo de sinal.

    entrada azul     → PLAYER (azul)  🔵
    entrada vermelho → BANKER (vermelho) 🔴
    """
    t = tipo.lower()
    if "azul" in t:
        return "PLAYER (azul)", "🔵"
    elif "vermelho" in t:
        return "BANKER (vermelho)", "🔴"
    return tipo.upper(), "📊"


# ============================================================
# MENSAGEM DE SINAL
# ============================================================

def _formatar_sinal(sinal: Sinal) -> str:
    label, emoji = _display_tipo(sinal.tipo)

    return f"""
🔥 <b>SINAL BAC BO</b>

🎯 Entre em <b>{label}</b> {emoji}
📊 Confiança: <b>{sinal.confianca:.1f}%</b>

⚪ <b>Proteção no TIE (branco)</b>

👉 <a href="https://blaze.bet.br/pt/">ENTRAR NA BLAZE</a>
""".strip()


def _formatar_gale(sinal: Sinal, numero_gale: int) -> str:
    label, emoji = _display_tipo(sinal.tipo)

    return f"""
⚠️ <b>GALE {numero_gale} — BAC BO</b>

🎯 Entre novamente em <b>{label}</b> {emoji}
🔁 Mantenha a mesma entrada!

⚪ <b>Proteção no TIE (branco)</b>

👉 <a href="https://blaze.bet.br/pt/">ENTRAR NA BLAZE</a>
""".strip()


# ============================================================
# ENVIA SINAL
# ============================================================

def enviar_sinal(sinal: Sinal) -> bool:
    if not settings.telegram_token or not settings.telegram_chat_id:
        logger.warning("Telegram não configurado")
        return False

    mensagem = _formatar_sinal(sinal)
    enviado = _enviar(mensagem)

    if enviado:
        logger.info(f"Sinal {sinal.id} enviado ao Telegram")

    return enviado


# ============================================================
# TESTAR CONEXÃO
# ============================================================

def testar_conexao() -> dict:
    if not settings.telegram_token:
        return {"ok": False, "bot": None}

    try:
        url = _build_url("getMe")
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url)

        if response.status_code == 200:
            bot_name = response.json().get("result", {}).get("username")
            return {"ok": True, "bot": bot_name}

        return {"ok": False, "bot": None}

    except Exception as e:
        logger.error(f"Erro ao testar conexão Telegram: {e}")
        return {"ok": False, "bot": None}


# ============================================================
# VERIFICAR RESULTADO — com suporte a GALE
# ============================================================

def verificar_resultado(db) -> None:
    """
    Fluxo de verificação com até 2 gales:

      Jogada 1 (gale=0):
        - TIE (branco)    → ✅ GREEN (proteção)
        - cor correta     → ✅ GREEN
        - cor errada      → envia GALE 1, sinal.gale = 1

      Jogada 2 (gale=1):
        - TIE (branco)    → ✅ GREEN (proteção)
        - cor correta     → ✅ GREEN
        - cor errada      → envia GALE 2, sinal.gale = 2

      Jogada 3 (gale=2):
        - TIE (branco)    → ✅ GREEN (proteção)
        - cor correta     → ✅ GREEN
        - cor errada      → ❌ RED

    sinal.acertou fica None enquanto ainda não foi decidido.
    """

    sinal = (
        db.query(Sinal)
        .filter(Sinal.enviado_telegram == True)
        .filter(Sinal.acertou == None)  # noqa: E711
        .order_by(Sinal.timestamp.desc())
        .first()
    )

    if not sinal:
        return

    # Pega todos os resultados após o sinal em ordem cronológica
    resultados = (
        db.query(Resultado)
        .filter(Resultado.timestamp > sinal.timestamp)
        .order_by(Resultado.timestamp.asc())
        .all()
    )

    if not resultados:
        return

    # gale=0 → avalia jogada no índice 0
    # gale=1 → avalia jogada no índice 1
    # gale=2 → avalia jogada no índice 2
    indice_atual = sinal.gale

    if len(resultados) <= indice_atual:
        # Jogada ainda não saiu — aguarda próximo ciclo
        return

    resultado_real = resultados[indice_atual].resultado.lower()

    # Determina a cor esperada baseada no tipo do sinal
    entrada = sinal.tipo.lower()
    if "vermelho" in entrada:
        cor_esperada = "vermelho"   # entrada BANKER
    elif "azul" in entrada:
        cor_esperada = "azul"       # entrada PLAYER
    else:
        logger.warning(f"Tipo de sinal desconhecido: {sinal.tipo}")
        sinal.acertou = False
        db.commit()
        return

    # ── Verifica resultado ────────────────────────────────────────
    acertou = False

    if resultado_real == "branco":
        # TIE sempre é proteção — GREEN
        acertou = True
        _enviar("✅ <b>GREEN!</b> (proteção no TIE)")
        logger.info(f"Sinal {sinal.id} gale={sinal.gale} → GREEN (TIE/branco)")

    elif resultado_real == cor_esperada:
        acertou = True
        _enviar("✅ <b>GREEN!</b>")
        logger.info(f"Sinal {sinal.id} gale={sinal.gale} → GREEN ({cor_esperada})")

    # ── Acertou → encerra ─────────────────────────────────────────
    if acertou:
        sinal.acertou = True
        db.commit()
        return

    # ── Errou → gale ou RED ───────────────────────────────────────
    if sinal.gale < MAX_GALES:
        sinal.gale += 1
        db.commit()
        _enviar(_formatar_gale(sinal, sinal.gale))
        logger.info(f"Sinal {sinal.id} → GALE {sinal.gale} enviado")
    else:
        sinal.acertou = False
        db.commit()
        _enviar("❌ <b>RED!</b>")
        logger.info(f"Sinal {sinal.id} → RED (após {MAX_GALES} gales)")
