"""Ciclo de vida MLOps: champion-challenger, aprovacao, promocao e rollback (Etapa 7).

Fluxo demonstrado:
1. champion = politica em producao (registro `models/registry.json`).
2. treina um CHALLENGER (politica candidata) e registra no MLflow.
3. compara champion x challenger numa avaliacao congelada (offline, deterministica).
4. aplica criterio de promocao (ganho minimo); se passar, RECOMENDA promover.
5. promocao exige APROVACAO HUMANA (approved_by) -> atualiza o registro.
6. rollback volta para a versao anterior do registro.

A API (policy_store.load_policy) serve sempre a champion do registro: promover ou
reverter muda, de fato, qual politica entra em producao.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from datathon_offerexp import policy_store as store
from datathon_offerexp import synthetic as syn

# criterio objetivo de promocao: ganho minimo de conversao (pontos percentuais)
MIN_LIFT_PP = 0.3


def policy_value(policy, events: pd.DataFrame) -> dict:
    """Avaliacao CONGELADA: usa a decisao greedy (sem aprender mais).

    Mede a conversao esperada e o regret da politica ja treinada sobre todos os
    eventos, de forma deterministica (comparacao justa entre champion e challenger).
    """
    conv, oracle = [], []
    for _, r in events.iterrows():
        ctx = {
            "segment": r["segment"],
            "channel": r["channel"],
            "base_propensity": float(r["base_propensity"]),
        }
        probs = {a: syn.true_conv_prob(ctx["base_propensity"], a, ctx["segment"], ctx["channel"])
                 for a in syn.ARMS}
        arm = policy.best_among(ctx, list(syn.ARMS))
        conv.append(probs[arm])
        oracle.append(max(probs.values()))
    return {
        "conversao_pct": round(float(np.mean(conv)) * 100, 3),
        "regret_pct": round(float(np.mean(oracle) - np.mean(conv)) * 100, 3),
    }


def _load_version(version: str):
    policy, _ = store.load_policy(store.MODELS_DIR / f"{version}.json")
    return policy


def train_challenger(
    version: str,
    context_keys: tuple[str, ...] = ("segment", "channel"),
    seed: int = 1,
) -> str:
    """Treina e salva um challenger; registra no MLflow. Devolve a versao."""
    store.train_and_export(version=version, context_keys=context_keys, seed=seed)
    _log_mlflow_challenger(version, context_keys)
    return version


def compare(champion_version: str, challenger_version: str) -> dict:
    """Compara champion x challenger e aplica o criterio de promocao."""
    events = pd.read_csv(store.ev.EVENTS_PATH)
    champ = policy_value(_load_version(champion_version), events)
    chall = policy_value(_load_version(challenger_version), events)
    lift = round(chall["conversao_pct"] - champ["conversao_pct"], 3)
    recommend = lift >= MIN_LIFT_PP
    return {
        "champion": {"version": champion_version, **champ},
        "challenger": {"version": challenger_version, **chall},
        "lift_pp": lift,
        "criterio": f"lift >= {MIN_LIFT_PP} pp",
        "recomendacao": "PROMOVER" if recommend else "MANTER champion",
    }


def _registry() -> dict:
    if store.REGISTRY_PATH.exists():
        return json.loads(store.REGISTRY_PATH.read_text(encoding="utf-8"))
    return {"champion": store.DEFAULT_VERSION, "history": []}


def _save_registry(reg: dict) -> None:
    store.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    store.REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def promote(version: str, approved_by: str | None, metrics: dict | None = None) -> dict:
    """Promove uma versao a champion. EXIGE aprovacao humana (approved_by)."""
    if not approved_by:
        raise PermissionError("Promocao requer aprovacao humana (approved_by).")
    reg = _registry()
    reg["history"].append(
        {
            "version": version,
            "stage": "champion",
            "approved_by": approved_by,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics or {},
            "previous": reg["champion"],
        }
    )
    reg["champion"] = version
    _save_registry(reg)
    return reg


def rollback() -> dict:
    """Reverte para a versao anterior registrada no historico."""
    reg = _registry()
    if not reg["history"]:
        raise ValueError("Sem historico para rollback.")
    previous = reg["history"][-1].get("previous")
    if not previous:
        raise ValueError("Sem versao anterior registrada.")
    reg["history"].append(
        {
            "version": previous,
            "stage": "champion (rollback)",
            "approved_by": "rollback",
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "previous": reg["champion"],
        }
    )
    reg["champion"] = previous
    _save_registry(reg)
    return reg


def _log_mlflow_challenger(version: str, context_keys: tuple[str, ...]) -> None:
    import os

    try:
        import mlflow

        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
        mlflow.set_experiment("etapa7-lifecycle")
        events = pd.read_csv(store.ev.EVENTS_PATH)
        val = policy_value(_load_version(version), events)
        with mlflow.start_run(run_name=version):
            mlflow.log_params({"version": version, "context_keys": "+".join(context_keys)})
            mlflow.log_metrics(
                {"conversao_pct": val["conversao_pct"], "regret_pct": val["regret_pct"]}
            )
    except Exception as exc:  # tracking nao pode derrubar o ciclo de vida
        print(f"(MLflow indisponivel - tracking ignorado: {type(exc).__name__})")


def main() -> None:
    """Demonstra o ciclo completo de ponta a ponta."""
    # 1. champion v1: treinado numa janela menor/antiga (1500 eventos)
    store.train_and_export("policy-v1", context_keys=("segment",), seed=0, max_events=1500)
    _save_registry({"champion": "policy-v1", "history": []})

    # 2. challenger v2: RETREINO com a base completa (mesma estrutura, mais dados)
    train_challenger("policy-v2", context_keys=("segment",), seed=0)
    d2 = compare("policy-v1", "policy-v2")
    print("== Champion v1  x  Challenger v2 (retreino com dados completos) ==")
    print(json.dumps(d2, ensure_ascii=False, indent=2))
    if d2["recomendacao"] == "PROMOVER":
        promote("policy-v2", approved_by="maria (revisora)", metrics=d2["challenger"])
        print("-> APROVADO por humano. Champion agora:", _registry()["champion"])

    # 3. challenger v3: hipotese mais fina (segmento + canal)
    train_challenger("policy-v3", context_keys=("segment", "channel"), seed=1)
    d3 = compare(_registry()["champion"], "policy-v3")
    print("\n== Champion v2  x  Challenger v3 (segmento + canal) ==")
    print(json.dumps(d3, ensure_ascii=False, indent=2))
    if d3["recomendacao"] != "PROMOVER":
        print("-> REJEITADO pelo gate: v3 superajusta segmentos pequenos. Champion mantido:",
              _registry()["champion"])

    # 4. demonstra ROLLBACK e re-promocao
    print("\n== Rollback ==")
    rollback()
    print("Rollback -> champion:", _registry()["champion"])
    promote("policy-v2", approved_by="maria (revisora)", metrics=d2["challenger"])
    print("Re-promovido -> champion final:", _registry()["champion"])


if __name__ == "__main__":
    main()
