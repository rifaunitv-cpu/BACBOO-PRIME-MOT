# ============================================================
# TELEGRAM SERVICE (ESTÁVEL + GREEN/RED CORRETO)
# ============================================================

import logging
import httpx
from typing import Optional

from app.config import get_settings
from app.models.sinal import Sinal
from app.models.resultado import Resultado

logger = logging.getLogger(__name__)
settings = get_settings()

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"
TIMEOUT = 10


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
# MENSAGEM DE SINAL
# ============================================================

def _formatar_sinal(sinal: Sinal) -> str:
    tipo = sinal.tipo.lower().replace("verde", "azul")

    emoji = {
        "entrada azul": "🔵",
        "entrada vermelho": "🔴",
        "entrada branco": "⚪",
    }.get(tipo, "📊")

    return f"""
🔥 <b>SINAL BAC BO</b>

🎯 <b>{tipo.upper()}</b> {emoji}
📊 Confiança: <b>{sinal.confianca:.1f}%</b>

⚪ <b>Cobrir no branco</b>

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
        logger.info(f"Sinal {sinal.id} enviado")

    return enviado


# ============================================================
# TESTAR CONEXÃO
# ============================================================

def testar_conexao() -> dict:
    """
    Testa se o bot Telegram está acessível e retorna dict de status.
    Retorna: {"ok": True/False, "bot": "<nome>" ou None}
    """
    if not settings.telegram_token:
        logger.warning("Telegram token não configurado")
        return {"ok": False, "bot": None}

    try:
        url = _build_url("getMe")
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url)

        if response.status_code == 200:
            data = response.json()
            bot_name = data.get("result", {}).get("username")
            logger.info(f"Telegram OK — bot: @{bot_name}")
            return {"ok": True, "bot": bot_name}
        else:
            logger.warning(f"Telegram retornou status {response.status_code}")
            return {"ok": False, "bot": None}

    except Exception as e:
        logger.error(f"Erro ao testar conexão Telegram: {e}")
        return {"ok": False, "bot": None}


# ============================================================
# VERIFICAR RESULTADO (VERSÃO CORRETA)
# ============================================================

def verificar_resultado(db) -> None:
    """
    Procura sinais enviados e ainda não verificados
    e compara com o próximo resultado após o sinal
    """

    # pega último sinal enviado e ainda não verificado
    sinal = (
        db.query(Sinal)
        .filter(Sinal.enviado_telegram == True)
        .filter(Sinal.acertou.is_(None))
        .order_by(Sinal.timestamp.desc())
        .first()
    )

    if not sinal:
        return

    # pega resultados APÓS o sinal
    resultados = (
        db.query(Resultado)
        .filter(Resultado.timestamp > sinal.timestamp)
        .order_by(Resultado.timestamp.asc())
        .limit(2)  # pega até 2 jogadas (segurança)
        .all()
    )

    if not resultados:
        return

    entrada = sinal.tipo.lower().replace("verde", "azul")

    entrada_cor = None
    if "azul" in entrada:
        entrada_cor = "azul"
    elif "vermelho" in entrada:
        entrada_cor = "vermelho"

    if not entrada_cor:
        return

    # 🔥 verifica primeira jogada após sinal
    resultado_real = resultados[0].resultado.lower()

    if resultado_real == entrada_cor or resultado_real == "branco":
        _enviar("✅ <b>GREEN!</b>")
        sinal.acertou = True
        logger.info("GREEN confirmado")

    else:
        _enviar("❌ <b>RED!</b>")
        sinal.acertou = False
        logger.info("RED confirmado")

    db.commit()
