"""Camada de enriquecimento sintetico (Etapa 2).

Cria, POR CIMA da base Kaggle (sem altera-la), o cenario de experimentacao:

- catalogo de bracos (ofertas);
- eventos de impressao com contexto e braco escolhido por uma politica de log;
- recompensas com atraso (clique -> inicio de jornada -> conversao).

Tudo e gerado com semente fixa (reprodutivel). O modelo gerador fica aqui, no
codigo, para que a avaliacao offline (Etapa 4) possa simular o que teria
acontecido com qualquer braco (recompensas contrafactuais).

Visao geral do gerador:
1. Cada evento sorteia um cliente da base processada -> isso da o contexto real.
2. Um modelo de propensao (regressao logistica) estima p0 = prob. base de
   conversao daquele cliente (ancorado nos dados reais).
3. A prob. de conversao de cada braco = p0 ajustada por multiplicadores de
   braco, segmento e canal. Assim o MELHOR braco depende do contexto (sinal que
   um bandit contextual consegue aprender).
4. A politica de log e uniforme (sorteia um braco ao acaso). Isso permite
   avaliacao offline justa depois.
5. As recompensas seguem um funil: clique -> jornada -> conversao, cada uma com
   um atraso diferente (delayed rewards).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from datathon_offerexp import data_loader as dl

# ----------------------------------------------------------------------------
# Parametros globais (documentados no relatorio de geracao)
# ----------------------------------------------------------------------------
SEED = 42
N_EVENTS = 8000
HORIZON_DAYS = 30
START = datetime(2026, 1, 1, tzinfo=timezone.utc)

ARMS: tuple[str, ...] = (
    "sem_oferta",
    "educacao_financeira",
    "simulador_credito",
    "oferta_deposito",
)
CHANNELS: tuple[str, ...] = ("app", "web", "email")

# Diretorio de saida
OUT_DIR = Path("data/synthetic_enrichment")
CATALOG_PATH = OUT_DIR / "offer_catalog.sample.csv"
EVENTS_PATH = OUT_DIR / "offer_events.sample.csv"
REWARDS_PATH = OUT_DIR / "delayed_rewards.sample.csv"

# Multiplicadores do modelo gerador (hipoteses de negocio, sinteticas) ---------
# Efeito medio de cada braco sobre a propensao base.
ARM_MULT: dict[str, float] = {
    "sem_oferta": 0.70,          # controle: nenhuma oferta -> converte menos
    "educacao_financeira": 1.10,
    "simulador_credito": 1.25,
    "oferta_deposito": 1.40,     # oferta direta: forte, mas pode irritar (ver abaixo)
}

# Interacao braco x segmento (contexto importa).
SEG_MULT: dict[tuple[str, str], float] = {
    ("educacao_financeira", "novo"): 1.35,      # educar funciona p/ cliente novo
    ("simulador_credito", "recorrente"): 1.25,  # simulador p/ quem ja interage
    ("oferta_deposito", "reativado"): 1.30,     # oferta direta p/ quem ja teve campanha
    ("oferta_deposito", "novo"): 0.60,          # oferta direta irrita o cliente novo
}

# Interacao braco x canal.
CHANNEL_MULT: dict[tuple[str, str], float] = {
    ("educacao_financeira", "email"): 1.15,
    ("oferta_deposito", "app"): 1.20,
    ("simulador_credito", "web"): 1.15,
}

# Pesos das recompensas intermediarias (ilustrativos).
REWARD_VALUE = {"click": 0.1, "journey_start": 0.3, "conversion": 1.0}

# Features usadas no modelo de propensao (todas pre-decisao, sem vazamento).
CAT_FEATURES = ["job", "marital", "education", "contact", "month", "poutcome"]
NUM_FEATURES = ["age", "campaign", "previous", "emp.var.rate", "euribor3m", "nr.employed"]


# ----------------------------------------------------------------------------
def build_catalog() -> pd.DataFrame:
    """Catalogo dos bracos (ofertas). Separado da base Kaggle."""
    rows = [
        ("sem_oferta", "Sem oferta", "Controle: nenhuma acao proposta.", 0.0),
        (
            "educacao_financeira",
            "Educacao financeira",
            "Conteudo educativo sobre poupanca e investimento.",
            0.5,
        ),
        (
            "simulador_credito",
            "Simulador de credito",
            "Ferramenta para simular credito/investimento.",
            0.8,
        ),
        (
            "oferta_deposito",
            "Oferta de deposito a prazo",
            "Oferta direta de deposito a prazo.",
            1.0,
        ),
    ]
    df = pd.DataFrame(rows, columns=["arm_id", "arm_name", "description", "cost_unit"])
    df["channels"] = "app|web|email"
    return df


def derive_segment(df: pd.DataFrame) -> pd.Series:
    """Define o segmento sintetico a partir do historico real.

    - novo: nunca participou de campanha anterior;
    - recorrente: ja teve contatos anteriores, mas sem sucesso;
    - reativado: teve sucesso em campanha anterior.
    """
    seg = np.where(
        df["previous"] == 0,
        "novo",
        np.where(df["poutcome"] == "success", "reativado", "recorrente"),
    )
    return pd.Series(seg, index=df.index)


def fit_propensity(df: pd.DataFrame) -> np.ndarray:
    """Estima p0 (prob. base de conversao) por cliente via regressao logistica."""
    pipe = Pipeline(
        [
            (
                "prep",
                ColumnTransformer(
                    [
                        ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_FEATURES),
                        ("num", StandardScaler(), NUM_FEATURES),
                    ]
                ),
            ),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipe.fit(df[CAT_FEATURES + NUM_FEATURES], df[dl.TARGET])
    return pipe.predict_proba(df[CAT_FEATURES + NUM_FEATURES])[:, 1]


def true_conv_prob(p0: float, arm: str, segment: str, channel: str) -> float:
    """Probabilidade 'verdadeira' de conversao de um braco num contexto.

    E o coracao do simulador: combina a propensao base com os efeitos de
    braco, segmento e canal. Usada na geracao e na avaliacao (contrafactual).
    """
    p = p0 * ARM_MULT[arm]
    p *= SEG_MULT.get((arm, segment), 1.0)
    p *= CHANNEL_MULT.get((arm, channel), 1.0)
    return float(np.clip(p, 0.0, 0.95))


def generate(
    n_events: int = N_EVENTS,
    seed: int = SEED,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Gera (catalogo, eventos, recompensas) de forma reprodutivel."""
    rng = np.random.default_rng(seed)

    base = dl.build_modeling_table(dl.load_raw())
    base = base.reset_index(drop=True)
    base["segment"] = derive_segment(base)
    base["p0"] = fit_propensity(base)

    # sorteia clientes (com reposicao) para os eventos
    idx = rng.integers(0, len(base), size=n_events)
    clients = base.iloc[idx].reset_index(drop=True)

    # canal sintetico e timestamps dentro do horizonte
    channels = rng.choice(CHANNELS, size=n_events)
    offsets = np.sort(rng.uniform(0, HORIZON_DAYS, size=n_events))
    timestamps = [START + timedelta(days=float(o)) for o in offsets]

    # politica de log: braco uniforme entre os disponiveis (todos os bracos)
    logged_arms = rng.choice(ARMS, size=n_events)

    catalog = build_catalog()
    event_rows = []
    reward_rows = []

    for i in range(n_events):
        seg = clients.at[i, "segment"]
        ch = channels[i]
        p0 = float(clients.at[i, "p0"])
        arm = str(logged_arms[i])
        ts = timestamps[i]
        event_id = f"evt_{i:06d}"

        event_rows.append(
            {
                "event_id": event_id,
                "occurred_at": ts.isoformat(),
                "subject_key": f"sub_{int(idx[i]):06d}",
                "segment": seg,
                "channel": ch,
                "age": int(clients.at[i, "age"]),
                "job": clients.at[i, "job"],
                "month": clients.at[i, "month"],
                "poutcome": clients.at[i, "poutcome"],
                "previous": int(clients.at[i, "previous"]),
                "base_propensity": round(p0, 4),
                "available_arms": "|".join(ARMS),
                "logging_policy": "uniform_random",
                "chosen_arm": arm,
            }
        )

        # recompensas do braco escolhido (funil clique -> jornada -> conversao)
        p_conv = true_conv_prob(p0, arm, seg, ch)
        converted = rng.random() < p_conv
        # converters sempre clicaram e iniciaram jornada (funil coerente)
        p_click = float(np.clip(0.05 + 2.0 * p_conv, 0.0, 0.7))
        clicked = True if converted else (rng.random() < p_click)
        journey = True if converted else (clicked and rng.random() < 0.4)

        if clicked:
            reward_rows.append(
                _reward(event_id, arm, "click", ts, rng.uniform(5, 180), rng)
            )
        if journey:
            reward_rows.append(
                _reward(event_id, arm, "journey_start", ts, rng.uniform(60, 1440), rng)
            )
        if converted:
            reward_rows.append(
                _reward(
                    event_id, arm, "conversion", ts, rng.uniform(1440, 20160), rng
                )
            )

    events = pd.DataFrame(event_rows)
    rewards = pd.DataFrame(reward_rows)
    return catalog, events, rewards


def _reward(
    event_id: str,
    arm: str,
    kind: str,
    ts: datetime,
    delay_minutes: float,
    rng: np.random.Generator,  # noqa: ARG001 (mantem assinatura uniforme)
) -> dict[str, object]:
    """Monta uma linha de recompensa com atraso."""
    delay = round(float(delay_minutes), 1)
    return {
        "event_id": event_id,
        "arm": arm,
        "reward_type": kind,
        "reward_value": REWARD_VALUE[kind],
        "delay_minutes": delay,
        "occurred_at": (ts + timedelta(minutes=delay)).isoformat(),
    }


def main() -> None:
    """Gera e salva os tres arquivos sinteticos."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    catalog, events, rewards = generate()
    catalog.to_csv(CATALOG_PATH, index=False)
    events.to_csv(EVENTS_PATH, index=False)
    rewards.to_csv(REWARDS_PATH, index=False)

    conv = rewards[rewards["reward_type"] == "conversion"]
    print(f"Catalogo : {len(catalog)} bracos -> {CATALOG_PATH}")
    print(f"Eventos  : {len(events)} -> {EVENTS_PATH}")
    print(f"Recompensas: {len(rewards)} linhas -> {REWARDS_PATH}")
    print(f"Conversoes: {len(conv)} ({len(conv)/len(events)*100:.2f}% dos eventos)")
    print("Conversao por braco (politica de log uniforme):")
    by_arm = events.assign(
        conv=events["event_id"].isin(set(conv["event_id"]))
    ).groupby("chosen_arm")["conv"].mean().mul(100).round(2)
    print(by_arm.to_string())


if __name__ == "__main__":
    main()
