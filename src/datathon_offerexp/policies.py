"""Politicas de decisao: baseline, Thompson Sampling, UCB1 e Thompson contextual.

Cada politica recebe um `context` (dict com segment, channel, base_propensity),
escolhe um braco com `select`, e aprende com `update` quando a recompensa chega.

Conceitos:
- baseline: regra fixa, NAO aprende (controle).
- Thompson Sampling: bandit bayesiano. Mantem uma crenca (distribuicao Beta) sobre
  a taxa de conversao de cada braco e sorteia dela -> explora o incerto.
- UCB1 (familia Nilos-UCB): escolhe por media + bonus de incerteza.
- Thompson contextual: um Thompson separado por segmento -> personaliza.

Cold-start (comeco sem dados):
- Thompson usa prior Beta(1,1) (sem conhecimento -> explora bastante).
- UCB1 joga cada braco uma vez antes de comparar.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

import numpy as np

from datathon_offerexp.synthetic import ARMS


class Policy(ABC):
    """Interface comum a todas as politicas."""

    name: str = "policy"

    @abstractmethod
    def select(self, context: dict) -> str:
        """Escolhe um braco dado o contexto."""

    def update(self, arm: str, reward: float, context: dict) -> None:
        """Aprende com a recompensa observada (0/1). Baseline ignora."""

    def greedy(self, context: dict) -> str:
        """Melhor braco segundo a estimativa atual (usado p/ medir exploracao)."""
        return self.select(context)


class FixedArm(Policy):
    """Baseline deterministico: sempre o mesmo braco. Nao aprende."""

    def __init__(self, arm: str, name: str = "baseline_fixo") -> None:
        self.arm = arm
        self.name = name

    def select(self, context: dict) -> str:
        return self.arm

    def greedy(self, context: dict) -> str:
        return self.arm


class ThompsonSampling(Policy):
    """Bandit Beta-Bernoulli (nao contextual)."""

    def __init__(self, arms: tuple[str, ...] = ARMS, seed: int = 0) -> None:
        self.name = "thompson"
        self.arms = arms
        self.rng = np.random.default_rng(seed)
        # prior Beta(1,1) para cada braco -> cold-start sem vies
        self.alpha = {a: 1.0 for a in arms}
        self.beta = {a: 1.0 for a in arms}

    def select(self, context: dict) -> str:
        samples = {a: self.rng.beta(self.alpha[a], self.beta[a]) for a in self.arms}
        return max(samples, key=samples.get)

    def update(self, arm: str, reward: float, context: dict) -> None:
        self.alpha[arm] += reward
        self.beta[arm] += 1.0 - reward

    def greedy(self, context: dict) -> str:
        means = {a: self.alpha[a] / (self.alpha[a] + self.beta[a]) for a in self.arms}
        return max(means, key=means.get)

    def estimated_mean(self, arm: str) -> float:
        """Estimativa atual de conversao do braco (media da Beta)."""
        return self.alpha[arm] / (self.alpha[arm] + self.beta[arm])

    def export(self) -> dict[str, list[float]]:
        """Serializa o estado aprendido (alpha, beta por braco)."""
        return {a: [self.alpha[a], self.beta[a]] for a in self.arms}

    def load(self, state: dict[str, list[float]]) -> None:
        """Carrega um estado salvo."""
        for a, (al, be) in state.items():
            self.alpha[a] = float(al)
            self.beta[a] = float(be)


class UCB1(Policy):
    """Upper Confidence Bound (referencia da familia Nilos-UCB)."""

    def __init__(self, arms: tuple[str, ...] = ARMS) -> None:
        self.name = "ucb1"
        self.arms = arms
        self.counts = {a: 0 for a in arms}
        self.values = {a: 0.0 for a in arms}  # media de recompensa
        self.total = 0

    def select(self, context: dict) -> str:
        # cold-start: joga cada braco uma vez
        for a in self.arms:
            if self.counts[a] == 0:
                return a
        ucb = {
            a: self.values[a] + math.sqrt(2 * math.log(self.total) / self.counts[a])
            for a in self.arms
        }
        return max(ucb, key=ucb.get)

    def update(self, arm: str, reward: float, context: dict) -> None:
        self.counts[arm] += 1
        self.total += 1
        n = self.counts[arm]
        self.values[arm] += (reward - self.values[arm]) / n

    def greedy(self, context: dict) -> str:
        return max(self.values, key=self.values.get)


class ContextualThompson(Policy):
    """Um Thompson Sampling por CHAVE de contexto (criada sob demanda).

    `context_keys` define quais campos formam a chave:
    - ("segment",)             -> um modelo por segmento (padrao, mais simples);
    - ("segment", "channel")   -> por segmento E canal (contexto mais fino).

    Os modelos sao criados na hora em que uma chave nova aparece (cold-start),
    cada um com prior Beta(1,1).
    """

    def __init__(
        self,
        arms: tuple[str, ...] = ARMS,
        context_keys: tuple[str, ...] = ("segment",),
        seed: int = 0,
    ) -> None:
        self.name = "thompson_contextual"
        self.arms = arms
        self.context_keys = context_keys
        self.seed = seed
        self.models: dict[str, ThompsonSampling] = {}

    def _key(self, context: dict) -> str:
        return "|".join(str(context[k]) for k in self.context_keys)

    def _model(self, context: dict) -> ThompsonSampling:
        key = self._key(context)
        if key not in self.models:
            self.models[key] = ThompsonSampling(self.arms, seed=self.seed + len(self.models))
        return self.models[key]

    def select(self, context: dict) -> str:
        return self._model(context).select(context)

    def update(self, arm: str, reward: float, context: dict) -> None:
        self._model(context).update(arm, reward, context)

    def greedy(self, context: dict) -> str:
        return self._model(context).greedy(context)

    def best_among(self, context: dict, available: list[str]) -> str:
        """Melhor braco estimado entre os disponiveis (respeita elegibilidade)."""
        model = self._model(context)
        return max(available, key=model.estimated_mean)

    def estimated_mean(self, context: dict, arm: str) -> float:
        return self._model(context).estimated_mean(arm)

    def export(self) -> dict[str, dict]:
        """Serializa o estado de todas as chaves de contexto."""
        return {key: m.export() for key, m in self.models.items()}

    def load(self, state: dict[str, dict]) -> None:
        for key, st in state.items():
            model = ThompsonSampling(self.arms)
            model.load(st)
            self.models[key] = model
