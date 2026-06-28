"""Armazenamento e versionamento da politica treinada (artefato + registro).

A API nao treina a cada chamada. Em vez disso:
1. treinamos a politica uma vez (sobre os eventos sinteticos);
2. exportamos o estado aprendido para um JSON COM VERSAO (models/policy-vN.json);
3. um REGISTRO (models/registry.json) aponta qual versao e a "champion";
4. a API carrega a champion e serve decisoes.

Isso separa treino de serving e da um conceito claro de versao de politica, que
a Etapa 7 usa para promover, aprovar e reverter (rollback) modelos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from datathon_offerexp import evaluation as ev
from datathon_offerexp import synthetic as syn
from datathon_offerexp.policies import ContextualThompson

MODELS_DIR = Path("models")
REGISTRY_PATH = MODELS_DIR / "registry.json"
DEFAULT_VERSION = "policy-v1"
POLICY_PATH = MODELS_DIR / f"{DEFAULT_VERSION}.json"


def train_and_export(
    version: str = DEFAULT_VERSION,
    context_keys: tuple[str, ...] = ("segment",),
    seed: int = 0,
    max_events: int | None = None,
) -> Path:
    """Treina a politica e salva o artefato versionado.

    `max_events` limita a base de treino (simula uma janela de dados menor/antiga).
    """
    events = pd.read_csv(ev.EVENTS_PATH)
    if max_events is not None:
        events = events.head(max_events)
    policy = ContextualThompson(context_keys=context_keys, seed=seed)
    ev.run_simulation(policy, events, delayed=False)  # treina ate convergir

    artifact = {
        "policy_version": version,
        "policy_type": "thompson_contextual",
        "context_keys": list(context_keys),
        "arms": list(syn.ARMS),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_events": int(len(events)),
        "state": policy.export(),
    }
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = MODELS_DIR / f"{version}.json"
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def champion_version() -> str:
    """Versao champion atual (do registro); default se nao houver registro."""
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["champion"]
    return DEFAULT_VERSION


def load_policy(path: Path | None = None) -> tuple[ContextualThompson, str]:
    """Carrega a politica champion do artefato. Treina a default se faltar."""
    if path is None:
        version = champion_version()
        path = MODELS_DIR / f"{version}.json"
    if not path.exists():
        train_and_export()
        path = POLICY_PATH
    artifact = json.loads(path.read_text(encoding="utf-8"))
    keys = tuple(artifact.get("context_keys", ["segment"]))
    policy = ContextualThompson(context_keys=keys)
    policy.load(artifact["state"])
    return policy, artifact["policy_version"]


if __name__ == "__main__":
    out = train_and_export()
    print(f"Politica treinada e salva em {out}")
