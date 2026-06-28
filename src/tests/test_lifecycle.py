"""Testes do ciclo de vida MLOps: promoção, aprovação e rollback (Etapa 7)."""

import pandas as pd
import pytest

from datathon_offerexp import lifecycle as lc
from datathon_offerexp import policy_store as store
from datathon_offerexp.policies import ContextualThompson


@pytest.fixture
def registro_tmp(tmp_path, monkeypatch):
    """Isola o registro/modelos num diretório temporário."""
    monkeypatch.setattr(store, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(store, "REGISTRY_PATH", tmp_path / "registry.json")
    return tmp_path


def test_promocao_exige_aprovacao_humana(registro_tmp) -> None:
    with pytest.raises(PermissionError):
        lc.promote("policy-v2", approved_by=None)


def test_promocao_com_aprovacao_atualiza_champion(registro_tmp) -> None:
    reg = lc.promote("policy-v2", approved_by="maria")
    assert reg["champion"] == "policy-v2"
    assert reg["history"][-1]["approved_by"] == "maria"


def test_rollback_volta_versao_anterior(registro_tmp) -> None:
    lc.promote("policy-v2", approved_by="maria")  # champion v2 (anterior = default)
    reg = lc.rollback()
    assert reg["champion"] == store.DEFAULT_VERSION


def test_policy_value_retorna_metricas() -> None:
    events = pd.DataFrame(
        {
            "segment": ["novo", "recorrente", "reativado"] * 4,
            "channel": ["app", "web", "email"] * 4,
            "base_propensity": [0.1, 0.2, 0.3] * 4,
        }
    )
    val = lc.policy_value(ContextualThompson(), events)
    assert 0.0 <= val["conversao_pct"] <= 100.0
    assert val["regret_pct"] >= 0.0
