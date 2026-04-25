# ============================================================
# app/services/telegram_service.py
# Serviço de envio de mensagens para o Telegram.
#
# Usa a Bot API do Telegram via HTTP puro (httpx),
# sem dependência de bibliotecas de terceiros específicas do Telegram.
# ============================================================

import logging
from typing import Optional

import httpx

from app.config import get_settings
from app.models.sinal import Sinal

logger = logging.getLogger(__name__)
settings = get_settings()

# URL base da Bot API do Telegram
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"

# Timeout para requisições ao Telegram (segundos)
TIMEOUT = 10


def _build_url(method: str) -> str:
    """Constrói a URL completa para um método da Bot API."""
    return TELEGRAM_API_BASE.format(token=settings.telegram_token, method=method)


def _formatar_mensagem_sinal(sinal: Sinal) -> str:
    """
    Formata o sinal como mensagem Markdown para o Telegram.
    Parse mode: Markdown (não MarkdownV2 para simplicidade).
    """
    emoji_tipo = {
        "entrada verde": "🟢",
        "entrada vermelho": "🔴",
        "entrada branco": "⚪",
    }
    emoji = emoji_tipo.get(sinal.tipo.lower(), "📊")
    algoritmo_display = {
        "regra_simples": "Regra Simples",
        "random_forest": "Random Forest (ML)",
    }.get(sinal.algoritmo, sinal.algoritmo)

    linhas = [
        "🚀 *NOVO SINAL*",
        "",
        f"Entrada: *{sinal.tipo.upper()}* {emoji}",
        f"Confiança: *{sinal.confianca:.1f}%*",
        f"Algoritmo: {algoritmo_display}",
        "",
        f"📋 _{sinal.descricao}_",
        "",
        f"🕒 `{sinal.timestamp.strftime('%d/%m/%Y %H:%M:%S UTC') if sinal.timestamp else 'agora'}`",
    ]
    return "\n".join(linhas)


def enviar_sinal(sinal: Sinal) -> bool:
    """
    Envia um sinal formatado para o chat do Telegram.

    Args:
        sinal: Objeto Sinal a ser enviado

    Returns:
        True se enviado com sucesso, False caso contrário
    """
    if not settings.telegram_token or settings.telegram_token == "seu_token_aqui":
        logger.warning(
            "TELEGRAM_TOKEN não configurado. "
            "Defina no .env para habilitar o envio de mensagens."
        )
        return False

    if not settings.telegram_chat_id or settings.telegram_chat_id == "seu_chat_id_aqui":
        logger.warning(
            "TELEGRAM_CHAT_ID não configurado. "
            "Defina no .env para habilitar o envio de mensagens."
        )
        return False

    mensagem = _formatar_mensagem_sinal(sinal)

    try:
        url = _build_url("sendMessage")
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": mensagem,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)

        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                logger.info(
                    f"Sinal id={sinal.id} enviado ao Telegram com sucesso. "
                    f"message_id={data['result']['message_id']}"
                )
                return True
            else:
                logger.error(
                    f"Telegram retornou erro: {data.get('description', 'desconhecido')}"
                )
                return False
        else:
            logger.error(
                f"HTTP {response.status_code} ao enviar para o Telegram: {response.text[:200]}"
            )
            return False

    except httpx.TimeoutException:
        logger.error("Timeout ao conectar com a API do Telegram.")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao enviar mensagem ao Telegram: {e}")
        return False


def enviar_mensagem_texto(texto: str) -> bool:
    """
    Envia uma mensagem de texto livre ao Telegram.
    Útil para notificações de sistema (ex: bot iniciado, erro grave).
    """
    if not settings.telegram_token or not settings.telegram_chat_id:
        return False

    try:
        url = _build_url("sendMessage")
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": texto,
            "parse_mode": "Markdown",
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)
        return response.status_code == 200 and response.json().get("ok", False)
    except Exception as e:
        logger.error(f"Erro ao enviar texto ao Telegram: {e}")
        return False


def testar_conexao() -> dict:
    """
    Testa a conexão com o bot do Telegram usando getMe.
    Retorna informações do bot se bem-sucedido.
    """
    if not settings.telegram_token or settings.telegram_token == "seu_token_aqui":
        return {"ok": False, "erro": "TELEGRAM_TOKEN não configurado"}

    try:
        url = _build_url("getMe")
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url)
        data = response.json()
        if data.get("ok"):
            bot = data["result"]
            return {
                "ok": True,
                "bot_username": bot.get("username"),
                "bot_name": bot.get("first_name"),
            }
        return {"ok": False, "erro": data.get("description", "Desconhecido")}
    except Exception as e:
        return {"ok": False, "erro": str(e)}
