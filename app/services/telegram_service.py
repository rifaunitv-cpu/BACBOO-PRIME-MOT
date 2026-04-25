# ============================================================
# TELEGRAM SERVICE (COM GREEN/RED + COBERTURA)
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

# 🔥 CONTROLE DE SINAL ATIVO
_sinal_ativo: Optional[Sinal] = None


def _build_url(method: str) -> str:
    return TELEGRAM_API_BASE.format(
        token=settings.telegram_token,
        method=method
    )


# ============================================================
# 📤 ENVIO BASE
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
# 🔥 MENSAGEM DE ENTRADA (SINAL)
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
"""


# ============================================================
# 🚀 ENVIA SINAL
# ============================================================

def enviar_sinal(sinal: Sinal) -> bool:
    global _sinal_ativo

    if not settings.telegram_token or not settings.telegram_chat_id:
        logger.warning("Telegram não configurado")
        return False

    mensagem = _formatar_sinal(sinal)

    enviado = _enviar(mensagem)

    if enviado:
        logger.info(f"Sinal {sinal.id} enviado")
        _sinal_ativo = sinal  # 🔥 GUARDA PARA VALIDAR DEPOIS

    return enviado


# ============================================================
# 🧠 VERIFICA RESULTADO (GREEN / RED)
# ============================================================

def verificar_resultado(db) -> None:
    """
    Deve ser chamado a cada ciclo do scheduler
    """
    global _sinal_ativo

    if _sinal_ativo is None:
        return

    # pega último resultado
    ultimo = (
        db.query(Resultado)
        .order_by(Resultado.timestamp.desc())
        .first()
    )

    if not ultimo:
        return

    entrada = _sinal_ativo.tipo.lower()

    # 🔥 converte verde -> azul
    entrada = entrada.replace("verde", "azul")

    resultado = ultimo.resultado.lower()

    # mapeamento
    mapa = {
        "azul": "azul",
        "vermelho": "vermelho",
        "branco": "branco",
    }

    entrada_cor = None
    for k in mapa:
        if k in entrada:
            entrada_cor = k

    if not entrada_cor:
        return

    # 🔥 GREEN
    if resultado == entrada_cor or resultado == "branco":
        _enviar("✅ <b>GREEN!</b>")
        logger.info("GREEN enviado")
        _sinal_ativo = None
        return

    # 🔴 RED
    else:
        _enviar("❌ <b>RED!</b>")
        logger.info("RED enviado")
        _sinal_ativo = None
        return
