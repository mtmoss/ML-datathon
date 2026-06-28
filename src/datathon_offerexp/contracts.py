"""Contratos de dados (estruturas que entram e saem do sistema).

Estes dataclasses definem o "formato" de um evento de oferta e de um
registro de decisao. Manter o contrato fixo facilita testes e auditoria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# Os "bracos" sao as acoes possiveis (cada oferta e um braco do bandit).
Arm = Literal["sem_oferta", "educacao_financeira", "simulador_credito"]
Channel = Literal["app", "web", "email"]
Segment = Literal["novo", "recorrente", "reativado"]
PolicyMode = Literal["baseline", "adaptive"]


@dataclass(frozen=True, slots=True)
class SyntheticOfferEvent:
    """Um cliente elegivel vendo uma decisao de oferta."""

    event_id: str
    occurred_at: str  # ISO-8601
    subject_key: str  # id sintetico, NUNCA um id real de cliente
    channel: Channel
    segment: Segment
    available_arms: tuple[Arm, ...]
    context: dict[str, str | float | bool] = field(default_factory=dict)
    chosen_arm: Arm | None = None
    reward: float | None = None


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Registro auditavel de uma decisao tomada pela politica."""

    decision_id: str
    event_id: str
    policy_version: str
    selected_arm: Arm
    mode: PolicyMode
    exploration: bool
    reason_codes: tuple[str, ...]
    created_at: str  # ISO-8601
