# Geração dos Dados Sintéticos (Etapa 2)

Camada de experimentação criada **por cima** da base Kaggle, sem alterá-la.
Código: `src/datathon_offerexp/synthetic.py`. Reprodutível com semente fixa.

## Parâmetros

| Parâmetro | Valor |
|---|---|
| Semente (`SEED`) | 42 |
| Nº de eventos | 8.000 |
| Horizonte temporal | 30 dias (01/jan/2026 a 30/jan/2026) |
| Braços | sem_oferta, educacao_financeira, simulador_credito, oferta_deposito |
| Canais | app, web, email |
| Política de log | uniforme (sorteia braço ao acaso) |

## Arquivos gerados

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `offer_catalog.sample.csv` | catálogo dos braços | 4 |
| `offer_events.sample.csv` | impressões com contexto + braço logado | 8.000 |
| `delayed_rewards.sample.csv` | recompensas com atraso (funil) | 5.121 |

## Como o contexto é definido

Cada evento sorteia um cliente da base processada — então o contexto é **real**.
Sobre ele derivamos:

- **`segment`** (sintético, a partir do histórico real):
  - `novo`: nunca participou de campanha anterior (`previous=0`);
  - `recorrente`: já teve contatos anteriores sem sucesso;
  - `reativado`: teve sucesso em campanha anterior (`poutcome=success`).
- **`channel`**: sorteado entre app/web/email.
- **`base_propensity` (p0)**: probabilidade base de conversão estimada por uma
  regressão logística treinada nos dados reais. Ancora o cenário na realidade.

Distribuição de segmentos: novo 6.939 · recorrente 806 · reativado 255.

## Como a recompensa é definida

A probabilidade "verdadeira" de conversão de um braço é:

```
p_conv = p0 × efeito_do_braço × efeito_(braço,segmento) × efeito_(braço,canal)
```

Os multiplicadores são **hipóteses de negócio sintéticas** (documentadas no código):
oferta direta é forte para quem já converteu antes, mas irrita o cliente novo;
educação financeira ajuda o cliente novo; o simulador ajuda o recorrente.

Resultado — conversão (%) por segmento × braço (o melhor braço **muda com o contexto**):

| segmento | educacao | oferta_deposito | sem_oferta | simulador |
|---|---:|---:|---:|---:|
| novo | **14,1** | 7,0 | 6,4 | 11,9 |
| recorrente | 20,8 | 22,0 | 7,5 | **23,8** |
| reativado | 77,9 | **94,7** | 50,0 | 79,7 |

Melhor braço por segmento: **novo → educacao_financeira**, **recorrente →
simulador_credito**, **reativado → oferta_deposito**. É exatamente esse sinal
que uma política contextual deve aprender e um baseline fixo não captura.

## Recompensas com atraso (delayed rewards)

Funil coerente: um cliente que converte necessariamente clicou e iniciou jornada.

| Tipo | Valor | Atraso (mediana) | Quantidade |
|---|---:|---:|---:|
| `click` | 0,1 | ~94 min | 2.509 |
| `journey_start` | 0,3 | ~12 h | 1.593 |
| `conversion` | 1,0 | ~7,5 dias | 1.019 |

A **conversão** é a recompensa principal do bandit (binária: aconteceu ou não).
Clique e jornada são sinais intermediários, úteis e mais rápidos. O atraso da
conversão (dias) é o motivo de tratar **delayed rewards**: na hora de decidir, a
recompensa final ainda não chegou.

Conversão global: 1.019 / 8.000 = **12,7%** dos eventos (próximo dos 11,3% reais).

## Schema dos arquivos

**offer_catalog.sample.csv**: `arm_id, arm_name, description, cost_unit, channels`

**offer_events.sample.csv**: `event_id, occurred_at, subject_key, segment,
channel, age, job, month, poutcome, previous, base_propensity, available_arms,
logging_policy, chosen_arm`

**delayed_rewards.sample.csv**: `event_id, arm, reward_type, reward_value,
delay_minutes, occurred_at`

## Limitações e riscos

- **Dados 100% sintéticos** nas decisões/recompensas: validam o método, não
  refletem um banco real.
- **Multiplicadores arbitrários**: as hipóteses de negócio são inventadas (com
  semente fixa). Mudá-las muda o "melhor braço".
- **Segmentos desbalanceados**: poucos `reativado` (255) — estimativas desse
  grupo têm mais variância.
- **Sem identificador real de cliente**: `subject_key` é sintético.
- **Política de log uniforme**: ideal para avaliação offline, mas não é como um
  sistema real (que já decide com alguma inteligência).
