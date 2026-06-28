# Infra Azure — Componentes e Fronteiras

Detalhe de responsabilidade de cada componente e as fronteiras entre eles.
Visão completa e diagrama em [`docs/architecture-azure.md`](../../docs/architecture-azure.md).

## Fluxo de uma decisão

1. O cliente/avaliador chama a API via **API Management** (autentica e limita taxa).
2. **Container Apps** (FastAPI) recebe o contexto, valida o contrato e decide.
3. A decisão usa o **artefato de política** (`policy-v1.json`) carregado do **Blob**.
4. A decisão é gravada no **decision log** (Blob/Data Lake) e emitida para
   **Application Insights**.
5. Impressões e recompensas (atrasadas) entram por **Event Hubs**.

## Fluxo de retreino e promoção (Etapa 7)

1. Um **Container Apps Job** (agendado ou disparado por drift) lê eventos+recompensas.
2. Treina uma política candidata e registra métricas no **MLflow** (backend
   **PostgreSQL**, artefatos no **Blob**).
3. Se passar nos critérios, um humano aprova a promoção no **model registry**.
4. A nova versão do artefato substitui a anterior; rollback = apontar para a versão antiga.

## Fluxo do assistente (RAG, Etapa 8)

1. Pergunta do usuário → **assistente** em Container Apps.
2. Recupera documentos de política em **Azure AI Search** (busca vetorial sobre o Blob).
3. Gera a resposta com **Azure AI Foundry** (modelo de chat + embeddings).

## Fronteiras de segurança

| Fronteira | Controle |
|---|---|
| Internet → API | API Management + Entra ID (autenticação) |
| Serviço → segredos | Managed Identity → Key Vault (sem senha) |
| Serviço → dados | RBAC (least privilege) |
| Serviço → banco | Entra auth no PostgreSQL |
| Rede | Private Endpoints/VNet quando justificado |

## Responsabilidade por componente

| Componente | Responsabilidade única |
|---|---|
| API Management | entrada, auth, rate limit, versão da API |
| Container Apps (API) | decidir e registrar |
| Container Apps (Job) | retreinar e avaliar |
| Blob/Data Lake | persistir dados, artefatos e logs |
| PostgreSQL | metadados do MLflow |
| Event Hubs | ingestão de eventos/recompensas |
| AI Search | recuperação para o RAG |
| AI Foundry | inferência do LLM |
| Key Vault | segredos |
| Monitor/App Insights | observar |
