# Plano de Deploy — Azure

Passos para provisionar a arquitetura-alvo. **Ilustrativo**: o datathon não exige
recursos pagos ativos; serve para mostrar que o caminho é viável e só em Azure.

## Pré-requisitos

- Azure CLI (`az`) e conta com uma subscription.
- Imagem do serviço publicada (Dockerfile do projeto) no **Azure Container Registry**.

## Provisionamento (esboço `az` CLI)

```bash
# 1. grupo de recursos
az group create -n rg-offerexp -l brazilsouth

# 2. registry de container + build/push da imagem
az acr create -g rg-offerexp -n acrofferexp --sku Basic
az acr build -r acrofferexp -t offerexp-api:v1 .

# 3. armazenamento (datasets, artefatos, logs)
az storage account create -g rg-offerexp -n stofferexp --sku Standard_LRS

# 4. banco do MLflow
az postgres flexible-server create -g rg-offerexp -n pg-offerexp --tier Burstable --sku-name Standard_B1ms

# 5. segredos
az keyvault create -g rg-offerexp -n kv-offerexp

# 6. ambiente e app (Container Apps) com identidade gerenciada
az containerapp env create -g rg-offerexp -n cae-offerexp
az containerapp create -g rg-offerexp -n offerexp-api \
  --environment cae-offerexp --image acrofferexp.azurecr.io/offerexp-api:v1 \
  --system-assigned --ingress external --target-port 8000

# 7. dá à identidade do app acesso ao Key Vault e ao Storage (RBAC)
#    (az role assignment / az keyvault set-policy)

# 8. observabilidade
az monitor app-insights component create -g rg-offerexp --app offerexp-ai -l brazilsouth
```

(Event Hubs, AI Search e AI Foundry seguem o mesmo padrão; omitidos por brevidade.)

## CI/CD (já temos a base)

O `.github/workflows/ci.yaml` roda ruff + pytest. Para o deploy, o passo de CD
seria: ao dar merge na `main` → `az acr build` da imagem → atualizar a revisão do
Container Apps. Promoção de política controlada pela Etapa 7.

## Gestão de segredos

- Todos os segredos no **Key Vault**; a aplicação lê via **Managed Identity**.
- Nada de chave em código, imagem ou variável de ambiente em texto.
- `.env.example` ↔ secrets do Key Vault (mapeamento 1:1).

## Rollback

- Container Apps mantém **revisões**: voltar é apontar para a revisão anterior.
- Política: apontar o artefato para a versão anterior (`policy-v(N-1).json`).

## Custo qualitativo (resumo)

| Bloco | Custo ocioso | Sob carga |
|---|---|---|
| Compute (Container Apps) | ~zero (escala a zero) | baixo-médio |
| Dados (Blob + PostgreSQL) | baixo fixo | baixo |
| Eventos (Event Hubs) | baixo | médio |
| IA/RAG (AI Search + Foundry) | médio (Search cobra ocioso) | médio (Foundry por token) |
| Observabilidade | baixo | por GB de log |

Detalhe de ROI e TCO no pitch (Etapa 8).
