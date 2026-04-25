# ============================================================
# TELEGRAM SERVICE (FINAL AJUSTADO - 85% + GALE + RESULTADO)
# ============================================================

import logging
import httpx

from app.config import get_settings
from app.models.sinal import Sinal

logger = logging.getLogger(__name__)
settings = get_settings()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 10


def _build_url(method: str) -> str:
    return TELEGRAM_API_BASE.format(token=settings.telegram_token, method=method)


# 🔥 MENSAGEM DO SINAL (AGORA COM GALE + COBERTURA)
def _formatar_mensagem_sinal(sinal: Sinal) -> str:
    tipo = sinal.tipo.lower().replace("verde", "azul")

    emoji_tipo = {
        "entrada azul": "🔵",
        "entrada vermelho": "🔴",
        "entrada branco": "⚪",
    }

    emoji = emoji_tipo.get(tipo, "📊")

    mensagem = f"""
🔥 <b>SINAL BACBO</b>

🎯 Entrada: <b>{tipo.upper()}</b> {emoji}
📊 Confiança: <b>{sinal.confianca:.1f}%</b>

⚠️ Fazer até 2 Gales
⚪ Cobrir no BRANCO (TIE)

👉 <a href="https://blaze.bet.br/pt/">CLIQUE AQUI PARA JOGAR</a>

🕒 {sinal.timestamp.strftime('%d/%m/%Y %H:%M:%S') if sinal.timestamp else 'agora'}
"""

    return mensagem.strip()


# 🔥 NOVO: MENSAGEM DE RESULTADO (GREEN / RED)
def _formatar_resultado(acertou: bool) -> str:
    if acertou:
        return "✅ <b>RESULTADO: GREEN</b>"
    else:
        return "❌ <b>RESULTADO: RED</b>"


def enviar_sinal(sinal: Sinal) -> bool:
    # 🔥 BLOQUEIO DE CONFIANÇA (85%)
    if sinal.confianca < 85:
        logger.info(f"Sinal ignorado por baixa confiança: {sinal.confianca:.1f}%")
        return False

    if not settings.telegram_token:
        logger.warning("TELEGRAM_TOKEN não configurado.")
        return False

    if not settings.telegram_chat_id:
        logger.warning("TELEGRAM_CHAT_ID não configurado.")
        return False

    mensagem = _formatar_mensagem_sinal(sinal)

    try:
        url = _build_url("sendMessage")

        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)

        if response.status_code == 200 and response.json().get("ok"):
            logger.info(f"Sinal {sinal.id} enviado com sucesso")
            return True

        logger.error(f"Erro Telegram: {response.text}")
        return False

    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")
        return False


# 🔥 NOVO: ENVIAR RESULTADO FINAL (GREEN / RED)
def enviar_resultado(sinal: Sinal) -> bool:
    if sinal.acertou is None:
        return False

    mensagem = _formatar_resultado(sinal.acertou)

    try:
        url = _build_url("sendMessage")

        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": mensagem,
            "parse_mode": "HTML",
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)

        return response.status_code == 200

    except Exception as e:
        logger.error(f"Erro ao enviar resultado: {e}")
        return False


def enviar_mensagem_texto(texto: str) -> bool:
    if not settings.telegram_token or not settings.telegram_chat_id:
        return False

    try:
        url = _build_url("sendMessage")

        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": texto,
            "parse_mode": "HTML",
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)

        return response.status_code == 200

    except Exception as e:
        logger.error(f"Erro ao enviar texto: {e}")
        return False


def testar_conexao() -> dict:
    if not settings.telegram_token:
        return {"ok": False, "erro": "Token não configurado"}

    try:
        url = _build_url("getMe")

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url)

        data = response.json()

        if data.get("ok"):
            return {
                "ok": True,
                "bot_username": data["result"]["username"],
                "bot_name": data["result"]["first_name"],
            }

        return {"ok": False, "erro": "Falha na API"}

    except Exception as e:
        return {"ok": False, "erro": str(e)}
