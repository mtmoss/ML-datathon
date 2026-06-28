# Datathon 7-MLET — Experimentação Adaptativa em Ofertas Financeiras

Plataforma de **experimentação adaptativa** (multi-armed bandits) que decide, para cada
cliente elegível, qual oferta apresentar — aprendendo com as recompensas observadas.
Projeto do Datathon da Fase 5 (MLET7 / FIAP).

> Status: esqueleto inicial (Etapa 0). As demais etapas são preenchidas ao longo do projeto.

## Visão do problema

Uma instituição financeira digital precisa escolher a melhor oferta, mensagem ou próximo
passo em cada canal. Regras fixas e testes A/B longos desperdiçam tráfego e demoram a
reagir. A solução usa **bandits** para testar variações e convergir para a melhor ação,
mantendo exploração mínima, auditoria das decisões e governança.

## Escopo

- Baseline determinístico + política adaptativa (**Thompson Sampling**, com **UCB1** de referência).
- Base Kaggle **Bank Marketing** + camada sintética de experimentação.
- Avaliação offline com golden set, API de decisão, log auditável.
- Ciclo MLOps (MLflow, retreino, aprovação, promoção) e arquitetura-alvo Azure.
- Assistente LLM (Claude) com RAG para explicar decisões.

## Escolhas de design (simplicidade)

| Item | Escolha |
|---|---|
| Base | Bank Marketing (Kaggle) |
| Bandit | Thompson Sampling (Beta-Bernoulli) |
| Serviço | FastAPI |
| Tracking | MLflow local |
| Dados | arquivos locais (CSV/Parquet/JSONL) |
| LLM | Claude (Anthropic) |
| Azure | apenas diagrama + plano (sem deploy) |

## Mapa de pastas

```text
data/      base Kaggle, base processada, enriquecimento sintético, golden set
docs/      model card, system card, lgpd, arquitetura azure, estratégia, pitch
notebooks/ EDA e baseline
src/datathon_offerexp/  contratos, políticas, avaliação, log de decisão, API
src/tests/ testes automatizados
infra/azure/  arquitetura e plano de deploy
reports/   geração de dados, avaliação offline, fairness, retreino, observabilidade
```

## Execução local

```bash
# 1. ambiente
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. dependências (modo editável + ferramentas de dev)
pip install -e ".[dev]"

# 3. variáveis de ambiente
cp .env.example .env                 # preencha ANTHROPIC_API_KEY

# 4. testes
pytest

# 5. lint
ruff check src

# 6. API (depois do Dia 5)
uvicorn datathon_offerexp.app:app --reload
# abra http://localhost:8000/health
```

## Comandos principais

| Comando | O que faz |
|---|---|
| `pytest` | roda os testes |
| `ruff check src` | verifica estilo do código |
| `offerexp-eval` | avaliação offline (Dia 4) |
| `uvicorn datathon_offerexp.app:app --reload` | sobe a API |

## Limitações

- Dados de cliente são **sintéticos**; não há dados reais nem deploy em produção.
- A arquitetura Azure é uma proposta (target), não está implantada.
- O assistente apoia a análise humana; não toma decisões financeiras autônomas.
