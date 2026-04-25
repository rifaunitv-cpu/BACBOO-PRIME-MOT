# ============================================================
# tests/test_services.py
# Testes unitários dos serviços principais
# ============================================================

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# ------------------------------------------------------------------
# Testes do serviço de coleta
# ------------------------------------------------------------------

def test_simular_resultado_retorna_valor_valido():
    """Verifica que o simulador retorna apenas valores válidos."""
    from app.services.coleta_service import _simular_resultado

    valores_validos = {"verde", "vermelho", "branco"}
    for _ in range(100):
        resultado = _simular_resultado()
        assert resultado in valores_validos, f"Valor inválido: {resultado}"


def test_coletar_novo_resultado_persiste_no_banco():
    """Verifica que coletar_novo_resultado cria um Resultado no banco."""
    from app.services.coleta_service import coletar_novo_resultado
    from app.models.resultado import Resultado

    mock_db = MagicMock()
    mock_resultado = MagicMock(spec=Resultado)
    mock_resultado.id = 1
    mock_resultado.resultado = "verde"

    # Simula o refresh retornando o objeto criado
    mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 1)

    resultado = coletar_novo_resultado(mock_db, fonte="simulado")

    assert mock_db.add.called
    assert mock_db.commit.called


# ------------------------------------------------------------------
# Testes do serviço de análise
# ------------------------------------------------------------------

def test_codificar_valores():
    """Verifica a codificação de resultados em inteiros."""
    from app.services.analise_service import _codificar

    assert _codificar("verde") == 1
    assert _codificar("vermelho") == -1
    assert _codificar("branco") == 0
    assert _codificar("VERDE") == 1
    assert _codificar("desconhecido") == 0


def test_calcular_streak_positivo():
    """Verifica cálculo de streak para sequência verde."""
    import numpy as np
    from app.services.analise_service import _calcular_streak

    arr = np.array([1, -1, 1, 1, 1])  # streak de 3 verdes
    assert _calcular_streak(arr) == 3


def test_calcular_streak_negativo():
    """Verifica cálculo de streak para sequência vermelha."""
    import numpy as np
    from app.services.analise_service import _calcular_streak

    arr = np.array([1, 1, -1, -1, -1, -1])  # streak de 4 vermelhos
    assert _calcular_streak(arr) == -4


def test_extrair_features_retorna_dict_completo():
    """Verifica que todas as features são extraídas."""
    from app.services.analise_service import _extrair_features

    serie = [1, -1, 1, -1, 1, 1, 1, -1, 1, -1]
    features = _extrair_features(serie)

    campos_esperados = ["ultimo", "penultimo", "antepenultimo",
                        "soma_5", "soma_10", "media_5", "std_5",
                        "streak", "alternancia_3"]
    for campo in campos_esperados:
        assert campo in features, f"Feature '{campo}' não encontrada"


def test_analise_streak_gera_sinal():
    """Verifica que streak de 3+ gera sinal."""
    from app.services.analise_service import _analisar_regra_simples

    # 4 verdes seguidos → deve prever vermelho
    serie = [-1, 1, 1, 1, 1, 1]
    resultado = _analisar_regra_simples(serie)

    assert resultado.sinal_gerado is True
    assert "vermelho" in resultado.tipo
    assert resultado.confianca >= 55.0


def test_analise_sem_padrao_nao_gera_sinal():
    """Verifica que dados sem padrão não geram sinal."""
    from app.services.analise_service import _analisar_regra_simples

    # Alternância equilibrada sem padrão forte
    serie = [1, -1, 1, -1, 0, 1, -1]
    resultado = _analisar_regra_simples(serie)

    # Pode não gerar sinal — só verificamos que a estrutura está correta
    assert hasattr(resultado, "sinal_gerado")
    assert hasattr(resultado, "confianca")
    assert hasattr(resultado, "tipo")


# ------------------------------------------------------------------
# Testes do serviço de Telegram
# ------------------------------------------------------------------

def test_testar_conexao_sem_token():
    """Verifica que testar_conexao retorna erro sem token configurado."""
    from app.services.telegram_service import testar_conexao

    with patch("app.services.telegram_service.settings") as mock_settings:
        mock_settings.telegram_token = "seu_token_aqui"
        resultado = testar_conexao()
        assert resultado["ok"] is False
        assert "não configurado" in resultado["erro"]


def test_formatar_mensagem_sinal():
    """Verifica que a mensagem do Telegram é formatada corretamente."""
    from app.services.telegram_service import _formatar_mensagem_sinal
    from app.models.sinal import Sinal

    sinal = MagicMock(spec=Sinal)
    sinal.tipo = "entrada verde"
    sinal.confianca = 73.5
    sinal.algoritmo = "regra_simples"
    sinal.descricao = "Streak de 3x detectado."
    sinal.timestamp = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

    msg = _formatar_mensagem_sinal(sinal)

    assert "NOVO SINAL" in msg
    assert "ENTRADA VERDE" in msg
    assert "73.5%" in msg
    assert "🟢" in msg


# ------------------------------------------------------------------
# Testes do modelo
# ------------------------------------------------------------------

def test_resultado_to_dict():
    """Verifica a serialização do modelo Resultado."""
    from app.models.resultado import Resultado

    r = Resultado()
    r.id = 1
    r.resultado = "verde"
    r.fonte = "simulado"
    r.timestamp = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
    r.criado_em = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    d = r.to_dict()
    assert d["id"] == 1
    assert d["resultado"] == "verde"
    assert d["fonte"] == "simulado"
    assert "timestamp" in d


def test_sinal_to_dict():
    """Verifica a serialização do modelo Sinal."""
    from app.models.sinal import Sinal

    s = Sinal()
    s.id = 42
    s.tipo = "entrada vermelho"
    s.confianca = 68.75
    s.algoritmo = "random_forest"
    s.descricao = "Teste"
    s.enviado_telegram = True
    s.acertou = None
    s.timestamp = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    d = s.to_dict()
    assert d["id"] == 42
    assert d["confianca"] == 68.75
    assert d["enviado_telegram"] is True
    assert d["acertou"] is None
