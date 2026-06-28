"""Monitoramento de drift via PSI - Population Stability Index (Etapa 7).

Drift = quando a distribuicao dos dados em producao muda em relacao ao treino.
O modelo nao "piora" sozinho, mas para de refletir a realidade.

PSI mede o quanto duas distribuicoes diferem. Interpretacao usual:
- PSI < 0.1  -> estavel (sem acao);
- 0.1 a 0.2  -> alerta (observar);
- PSI > 0.2  -> drift relevante (gatilho de retreino).
"""

from __future__ import annotations

import numpy as np


def population_stability_index(
    reference: np.ndarray,
    current: np.ndarray,
    bins: int = 10,
) -> float:
    """Calcula o PSI entre uma amostra de referencia e uma amostra atual."""
    ref = np.asarray(reference, dtype=float)
    cur = np.asarray(current, dtype=float)

    # bordas dos bins definidas pela referencia (quantis)
    quantis = np.linspace(0, 100, bins + 1)
    edges = np.unique(np.percentile(ref, quantis))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf

    ref_perc = np.histogram(ref, bins=edges)[0] / len(ref)
    cur_perc = np.histogram(cur, bins=edges)[0] / len(cur)

    eps = 1e-6  # evita log(0)
    ref_perc = np.clip(ref_perc, eps, None)
    cur_perc = np.clip(cur_perc, eps, None)
    return float(np.sum((cur_perc - ref_perc) * np.log(cur_perc / ref_perc)))


def classify(psi: float) -> str:
    """Traduz o PSI em acao."""
    if psi < 0.1:
        return "estavel"
    if psi < 0.2:
        return "alerta"
    return "drift (gatilho de retreino)"


def drift_report(reference: np.ndarray, current: np.ndarray, name: str = "feature") -> dict:
    """Resumo de drift de uma feature."""
    psi = round(population_stability_index(reference, current), 4)
    return {"feature": name, "psi": psi, "status": classify(psi)}
