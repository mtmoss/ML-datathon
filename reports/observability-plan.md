# Plano de Observabilidade (Etapa 7)

O que monitorar para saber quando a política está degradando e quando retreinar.
Código de drift: `src/datathon_offerexp/drift.py`. No Azure, surfaceado em Azure
Monitor + Application Insights (ver `docs/architecture-azure.md`).

## 1. Drift de dados (PSI)

Drift = a distribuição em produção muda em relação ao treino. O modelo não "piora"
sozinho, mas para de refletir a realidade.

Usamos o **PSI (Population Stability Index)**:

| PSI | Status | Ação |
|---|---|---|
| < 0,1 | estável | nenhuma |
| 0,1 – 0,2 | alerta | observar |
| > 0,2 | drift | **gatilho de retreino** |

Demonstração (sobre `base_propensity`):

| Cenário | PSI | Status |
|---|---:|---|
| metade vs metade da base (estável) | 0,005 | estável |
| distribuição deslocada (+0,05) | alto (>0,2) | drift → retreino |

> Nota: `base_propensity` é muito concentrada em valores baixos, então o PSI é
> sensível. Em produção, ajusta-se o número de bins e quais features monitorar.

Monitorar drift em: contexto (segmento, canal, propensão) e na **recompensa**
(conversão observada).

## 2. Monitoramento de recompensa e da política

| Métrica | Por quê | Alerta |
|---|---|---|
| Conversão média | valor de negócio | queda sustentada |
| Regret | quanto se perde vs. ótimo | subida sustentada |
| Taxa de exploração | saúde do bandit | exploração ~0 (parou de aprender) ou alta demais |
| Fairness de exposição | um segmento sem oferta | desvio entre segmentos |

## 3. Observabilidade operacional (Azure)

- **Latência e disponibilidade** da API → Application Insights.
- **Custo** por serviço → Azure Monitor (alerta de custo).
- **Logs de decisão** → Log Analytics (consultas de auditoria).
- **Uso do assistente LLM** → tokens e latência.

## 4. O que dispara retreino

1. PSI > 0,2 em uma feature de contexto **ou** na recompensa.
2. Queda sustentada de conversão / subida de regret.
3. Agenda periódica (linha de base), mesmo sem drift.

O retreino entra no fluxo da Etapa 7: treina challenger → compara → aprovação
humana → promoção → (se preciso) rollback.
