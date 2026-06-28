# Decisões de Design — Registro para o Demo Day

Este documento registra **as escolhas que foram minhas/do grupo** (não impostas pela
banca), com o racional de cada uma. Serve para estudo e para defender as decisões na
apresentação.

Legenda da coluna "Natureza":

- **Exigido**: a banca pede o item; a tabela mostra *como* implementei.
- **Escolha dentro do exigido**: a banca pede a categoria, mas a opção foi minha.
- **Escolha livre**: a banca não pede; incluí por boa prática ou para antecipar etapas.

> Última atualização: **Etapa 6**. Atualizado a cada etapa nova.

---

## Etapa 0 — Organização do projeto

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Versão de Python | 3.11 fixa (`.python-version`) | 3.10 | Reprodutibilidade (Nível 2 de maturidade); usar recursos modernos de tipagem | Escolha dentro do exigido |
| Gerência de pacote | pip + `pyproject.toml` + venv | Poetry | Mais simples para iniciante; `pyproject.toml` é exigido | Escolha dentro do exigido |
| Nome do pacote interno | `datathon_offerexp` (≠ nome do repo) | igualar ao repo | Renomear o repo não deve quebrar imports | Escolha livre |
| Licença | MIT | Apache-2.0 | Permissiva e simples; licença é exigida | Escolha dentro do exigido |
| Layout | `src/` + `src/tests/` | tudo na raiz | Padrão profissional; evita import acidental | Escolha livre |
| Lint/format | **Ruff** | flake8 + black | Rápido, faz lint e format juntos | Escolha dentro do exigido |
| CI | GitHub Actions (ruff + pytest) | outro CI | Integra com o GitHub do projeto | Escolha dentro do exigido |

---

## Etapa 1 — Base Kaggle e EDA

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Dataset | Bank Marketing (`bank-additional-full`) | outras bases Kaggle aceitas | É o exemplo do enunciado; alvo binário de conversão encaixa em decisão de oferta | Escolha dentro do exigido |
| Coluna de vazamento | descartar **só** `duration` | descartar mais colunas | O próprio dataset alerta que `duration` é pós-contato; o resto é pré-decisão | Exigido (decisão de vazamento) |
| Valores `unknown` | manter como categoria | imputar | Não inventar dado; `unknown` pode ser informativo | Escolha livre |
| 12 duplicatas | manter | remover | Sem ID de cliente, podem ser legítimas; impacto 0,03% | Escolha livre |
| Formato da base tratada | Parquet | CSV | Compacto e rápido; preserva tipos | Escolha livre |
| Alvo | `y` → `subscribed` (1/0) | manter texto | Modelo precisa de número | Escolha livre |
| Estilo das figuras | paleta + Courier (padrão meu) | padrão matplotlib | Consistência visual para os resumos/Demo | Escolha livre |

---

## Etapa 2 — Enriquecimento sintético

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Nº de braços | **4** (incluí `oferta_deposito`) | 3 do exemplo | Dar mais riqueza à decisão e um braço "óbvio porém arriscado" | Escolha dentro do exigido |
| Segmentos | novo/recorrente/reativado (de `previous`/`poutcome`) | outra segmentação | Deriva do histórico real; dá contexto à política | Escolha livre |
| Canal | sintético (app/web/email) | usar `contact` real | O enunciado pede canal; criei como dado sintético | Escolha dentro do exigido |
| Propensão base (p0) | regressão logística nos dados reais | valores à mão | Ancorar o cenário na realidade, não em números soltos | Escolha livre |
| Modelo de recompensa | multiplicadores braço×segmento×canal | efeito só por braço | Fazer o **melhor braço depender do contexto** (senão o bandit não tem o que aprender) | Escolha livre |
| Funil de recompensa | clique → jornada → conversão | só conversão | Sinais intermediários (mais rápidos) + recompensa final | Exigido (delayed rewards) |
| Recompensa principal | conversão (binária) | usar clique | Conversão é o evento de valor; casa com Beta-Bernoulli | Escolha dentro do exigido |
| Política de log | uniforme (sorteia braço) | já decidir "esperto" | Dados sorteados permitem avaliação offline justa | Escolha livre |
| Semente / volume | `SEED=42`, 8.000 eventos, 30 dias | outros | Reprodutibilidade e volume suficiente para aprender | Exigido (sementes) |

---

## Etapa 3 — Baseline e bandits

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Conjunto de políticas | 2 baselines + Thompson + UCB1 + Thompson contextual | só 1 baseline + 1 bandit | Comparação rica e honesta (ingênuo, forte, e a proposta) | Escolha dentro do exigido |
| Bandit principal | **Thompson contextual** (por segmento) | Thompson global | Personaliza; melhor desempenho entre os que aprendem | Escolha dentro do exigido |
| UCB | UCB1 como referência **Nilos-UCB** | implementar variação exótica | Referência da família UCB exigida; UCB1 é o canônico | Exigido (referência Nilos-UCB) |
| Contexto na decisão | agrupar por segmento | LinUCB (contexto completo) | Mais simples; LinUCB fica como trabalho futuro | Escolha livre |
| Avaliação | replay **simulado** (modelo verdadeiro dá a recompensa) | estimadores off-policy (IPS) | Mais simples e rigoroso o bastante para iniciante | Escolha dentro do exigido |
| Janela de atribuição | 7 dias para a recompensa "voltar" | imediato | Imitar a vida real (recompensa atrasada) | Exigido (delayed rewards) |
| Métrica de exploração | escolheu ≠ melhor estimado | outra definição | Definição simples e interpretável | Escolha livre |
| Tracking | MLflow com **SQLite** | backend de arquivos | O MLflow novo descontinuou arquivos; SQLite é o recomendado | Exigido (MLflow); backend = escolha |
| Mostrar imediato vs atraso | sim, os dois | só o realista | Demonstra o efeito do atraso e quando o bandit vence | Escolha livre |

---

## Etapa 4 — Avaliação offline e golden set

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Resposta esperada no golden | braço **ótimo verdadeiro** (barra de qualidade) | a própria escolha da política (passa sempre) | Revelar limitações de verdade; failures são informativos | Escolha dentro do exigido |
| Tamanho/cobertura | 21 casos: típico/borda/segmento/adversarial | mínimo 20 sem variar | Cobertura exigida; passei de 20 | Exigido (≥20 e cobertura) |
| Casos adversariais | "não escolher braço que prejudica" (oferta→novo) | outro tipo | Testa guardrail de suitability | Exigido (adversarial) |
| Fairness | exposição de cada braço por segmento | só métrica global | Ver se algum grupo é excluído | Exigido (fairness de exposição) |
| Sensibilidade | 5 sementes + atrasos {0,7,14} | uma execução | Mostrar estabilidade e efeito do atraso | Escolha dentro do exigido |
| Tabelas markdown | lib `tabulate` | montar à mão | Relatórios legíveis automaticamente | Escolha livre |
| Seção "quando não usar" | incluída e honesta | omitir limitações | Exigido explicar limitações e condições de não-uso | Exigido |

---

## Etapa 5 — Serviço demonstrável

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Meio demonstrável | **API FastAPI** | CLI ou notebook | Mais demonstrável; doc automática; casa com Azure Container Apps | Escolha dentro do exigido |
| Política em produção | **artefato versionado** `models/policy-v1.json` (treino offline, API carrega) | treinar dentro da API | Serviço rápido; cria conceito de "versão de política" que a Etapa 7 usa | Escolha livre (antecipa exigência futura) |
| Validação/erros | pydantic; 422 (tipo) e 400 (regra) | validar à mão | Tratamento de erro exigido; pydantic é o padrão FastAPI | Exigido (tratamento de erro) |
| Conteúdo dos reason codes | elegível, segmento, canal, maior score, score | outro conjunto | Justificativa exigida; escolhi códigos legíveis | Exigido (reason codes); conteúdo = escolha |
| Decisão ao servir | explotar (greedy) | explorar também | Em produção, servir a melhor oferta estimada | Escolha livre |
| Comando único | **Makefile** (`make pipeline/serve/test`) | script `.sh` | Atalhos claros; "comando único" exigido | Exigido (pipeline 1 comando); ferramenta = escolha |
| Log de decisão | JSONL, ignorado no git (gerado na demo) | commitar amostra | Evita crescer no repo; regenera ao rodar | Exigido (log auditável); formato = escolha |

---

## Etapa 6 — Arquitetura-alvo Azure

| Decisão | O que escolhi | Alternativa | Racional | Natureza |
|---|---|---|---|---|
| Compute | **Azure Container Apps** | AKS / Functions | Roda nosso container, escala a zero, sem complexidade de Kubernetes | Escolha dentro do exigido |
| MLflow | self-hosted + PostgreSQL | Azure Machine Learning | Mais leve/barato para o escopo | Escolha livre |
| Banco | PostgreSQL (Burstable) | Cosmos DB / Azure SQL | Backend do MLflow; simples e barato | Escolha dentro do exigido |
| Eventos | Event Hubs | Service Bus | Ingestão de impressões/recompensas em fluxo | Escolha dentro do exigido |
| LLM em produção | Azure AI Foundry | manter Claude na nuvem | Exigência: arquitetura só Azure (Claude fica no dev) | Exigido (só Azure) |
| Entrada | API Management | expor o Container App direto | Auth, rate limit e versão num ponto só | Escolha livre |
| Segredos | Key Vault + Managed Identity | variáveis de ambiente | Exigido usar Key Vault + Managed Identity | Exigido |
| Region | brazilsouth (exemplo) | outra region | Latência/LGPD no Brasil | Escolha livre |

## Decisões transversais

| Decisão | O que escolhi | Racional | Natureza |
|---|---|---|---|
| Nome do repositório | `datathon-7mlet-grupo-06` | Formato exigido pela banca | Exigido |
| Idioma do código/docs | português nos comentários e relatórios | Facilitar estudo e a banca brasileira | Escolha livre |
| Testes a cada etapa | cobertura incremental (27 testes até aqui) | Rede de segurança; exigência de testes | Exigido (testes); abordagem = escolha |
| Documentar tudo em `docs/` e `reports/` | um arquivo por tema | Rastreabilidade e narrativa para o pitch | Escolha dentro do exigido |

---

## Como usar na apresentação

Para cada decisão que a banca questionar, a defesa é a mesma estrutura: **o que a
banca pediu → a opção que escolhi → a alternativa que descartei → por quê**. As
linhas marcadas "Escolha livre" são onde mais vale mostrar maturidade técnica
(antecipei necessidades, priorizei simplicidade, fui honesta sobre limitações).
