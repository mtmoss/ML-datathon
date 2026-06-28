"""Testes do monitoramento de drift (Etapa 7)."""

import numpy as np

from datathon_offerexp import drift


def test_psi_zero_para_distribuicoes_iguais() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=2000)
    psi = drift.population_stability_index(x, x.copy())
    assert psi < 0.01


def test_psi_alto_para_distribuicao_deslocada() -> None:
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, size=2000)
    cur = rng.normal(2, 1, size=2000)  # deslocada
    psi = drift.population_stability_index(ref, cur)
    assert psi > 0.2


def test_classify_thresholds() -> None:
    assert drift.classify(0.05) == "estavel"
    assert drift.classify(0.15) == "alerta"
    assert "drift" in drift.classify(0.5)
