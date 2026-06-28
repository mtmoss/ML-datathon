"""Politicas de decisao: baseline, Thompson Sampling e UCB1.

DIA 3: implementar a logica de cada politica aqui.
Por enquanto sao esqueletos com a assinatura definida.
"""

from __future__ import annotations

from collections.abc import Mapping

from datathon_offerexp.contracts import Arm, SyntheticOfferEvent


def baseline_select(event: SyntheticOfferEvent) -> Arm:
    """Politica de controle: escolhe sempre o primeiro braco elegivel (regra fixa)."""
    if not event.available_arms:
        raise ValueError("Evento sem bracos elegiveis.")
    return event.available_arms[0]


class ThompsonSampling:
    """Bandit bayesiano Beta-Bernoulli. DIA 3: implementar select/update."""

    def select(self, event: SyntheticOfferEvent) -> Arm:  # noqa: D102
        raise NotImplementedError("Implementar no Dia 3.")

    def update(self, arm: Arm, reward: float) -> None:  # noqa: D102
        raise NotImplementedError("Implementar no Dia 3.")


class UCB1:
    """Referencia da familia UCB (Nilos-UCB). DIA 3: implementar select/update."""

    def select(self, event: SyntheticOfferEvent) -> Arm:  # noqa: D102
        raise NotImplementedError("Implementar no Dia 3.")

    def update(self, arm: Arm, reward: float) -> None:  # noqa: D102
        raise NotImplementedError("Implementar no Dia 3.")


def adaptive_select(
    event: SyntheticOfferEvent,
    scores: Mapping[Arm, float],
) -> Arm:
    """Escolhe o braco de maior score estimado entre os elegiveis."""
    if not event.available_arms:
        raise ValueError("Evento sem bracos elegiveis.")
    return max(event.available_arms, key=lambda arm: scores.get(arm, 0.0))
