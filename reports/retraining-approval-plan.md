# Retreino, Aprovação e Promoção (Etapa 7)

Como uma nova hipótese de oferta/canal/mensagem sai de experimento para produção
controlada. Código: `src/datathon_offerexp/lifecycle.py`. Reproduzível:
`python -m datathon_offerexp.lifecycle`.

## Versionamento de política

- Cada política treinada vira um artefato versionado `models/policy-vN.json`
  (estado aprendido + metadados + `context_keys`).
- O registro `models/registry.json` aponta a **champion** (em produção) e guarda o
  histórico de promoções. A API (`policy_store.load_policy`) serve sempre a
  champion do registro — promover ou reverter muda, de fato, o que entra em produção.

## Champion-challenger

1. **Champion**: política atual em produção.
2. **Challenger**: política candidata (retreino com dados novos, ou nova hipótese
   de contexto).
3. Avaliação **congelada** (offline, determinística) compara as duas na mesma base.

## Critério de promoção (objetivo)

- Promover só se o **ganho de conversão ≥ 0,3 ponto percentual** sobre a champion
  (`MIN_LIFT_PP`). Caso contrário, manter a champion.
- O regret é reportado junto para checar que não piora.

## Approval gate (humano no loop)

- A promoção **exige aprovação humana**: a função `promote()` recusa sem
  `approved_by`. Registra quem aprovou e quando.
- Decisões sensíveis (domínio financeiro) não sobem de forma automática.

## Rollback

- O registro guarda a versão anterior. `rollback()` volta a champion para ela.
- No Azure, o Container Apps também mantém revisões (rollback de imagem).

## Demonstração real (executada)

| Passo | Champion → Challenger | Lift | Decisão |
|---|---|---|---|
| Retreino com dados completos | v1 (janela de 1.500) 15,01% → **v2** (base completa) **16,81%** | **+1,80 pp** | **PROMOVER** (aprovado por humano) |
| Nova hipótese (segmento+canal) | v2 16,81% → v3 16,07% | −0,74 pp | **REJEITAR** (gate protege) |
| Rollback | v2 → v1 → re-promove v2 | — | champion final: v2 |

Leituras importantes:

- O **retreino com dados frescos** (v2) melhorou a conversão e foi promovido após
  aprovação humana.
- A hipótese mais fina (v3, segmento+canal) **piorou**: com poucos dados por
  bucket (`reativado` ~255 eventos divididos em 3 canais), ela superajusta. O
  **gate rejeitou** — exatamente o papel dele: barrar política que aprendeu errado.
- O **rollback** foi exercitado e funciona.

## Rastreio de experimentos

Cada challenger é registrado no **MLflow** (experimento `etapa7-lifecycle`) com
`context_keys`, conversão e regret. Histórico de promoções no `registry.json`.

## Gatilhos de retreino

- **Agendado** (cron) como linha de base.
- **Event-driven**: disparado por **drift** (ver `observability-plan.md`) ou queda
  de recompensa.
