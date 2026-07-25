# Deploy na AWS (App Runner)

Guia para colocar o agente no ar usando **AWS App Runner** — o jeito mais simples
de rodar um container Docker na AWS sem gerenciar servidor, cluster ou load
balancer. Ele te dá uma URL pública com HTTPS automático.

## Por que App Runner (e não ECS/EKS/EC2)

- Você só aponta pra uma imagem no ECR e ele cuida do resto (deploy, HTTPS,
  restart em caso de falha, autoscaling).
- Alternativas como ECS Fargate ou EKS dão mais controle, mas exigem configurar
  VPC, load balancer, task definitions etc. — overkill pra um único serviço.
- **Atenção ao custo**: App Runner mantém no mínimo 1 instância ativa o tempo
  todo (não escala a zero como o Lambda ou o Cloud Run do GCP). Com a menor
  configuração (0.25 vCPU / 0.5 GB), fica em torno de alguns dólares por mês
  rodando 24/7. Se o volume de uso for muito baixo e o custo importar, me avise
  que te oriento a versão com AWS Lambda (container image) em vez disso, que
  escala a zero.

## Passo 1 — Pré-requisitos

1. Instale o [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
   e rode `aws configure` com uma credencial (Access Key + Secret) que tenha
   permissão de ECR e App Runner.
2. Confirme que está autenticado:
   ```
   aws sts get-caller-identity
   ```

## Passo 2 — Publicar a imagem no ECR

Rode o script incluso neste projeto:

```
AWS_REGION=us-east-1 ./deploy/push_to_ecr.sh
```

Ele cria o repositório ECR (se não existir), builda a imagem e faz o push. No
final ele imprime a URI da imagem, algo como:

```
123456789012.dkr.ecr.us-east-1.amazonaws.com/bimbambuy-agente:latest
```

Guarde essa URI — você vai usar no próximo passo.

## Passo 3 — Guardar a chave da Groq no Secrets Manager (recomendado)

Em vez de colar a `GROQ_API_KEY` em texto puro na configuração do App Runner,
guarde num secret:

```
aws secretsmanager create-secret \
  --name bimbambuy/groq-api-key \
  --secret-string "SUA_CHAVE_AQUI" \
  --region us-east-1
```

## Passo 4 — Criar o serviço no App Runner (console)

A criação inicial é mais tranquila pelo console (ele oferece um botão para
criar automaticamente a IAM role de acesso ao ECR):

1. Acesse o [console do App Runner](https://console.aws.amazon.com/apprunner/)
   → **Create service**.
2. **Source**: Container registry → Amazon ECR → selecione a imagem que você
   publicou no Passo 2.
3. **Deployment trigger**: "Automatic" se quiser que todo push de nova imagem
   no ECR dispare um redeploy sozinho; ou "Manual" se preferir controlar.
4. **ECR access role**: clique em "Create new service role" (o console cria a
   role com a permissão certa pra puxar a imagem).
5. **Service settings**:
   - Port: `8000` (é a porta que o `uvicorn` expõe dentro do container)
   - CPU/Memory: comece com 0.25 vCPU / 0.5 GB (dá pra aumentar depois se
     precisar)
6. **Environment variables**: adicione `GROQ_API_KEY`, tipo "Secrets Manager",
   apontando pro secret criado no Passo 3 (`bimbambuy/groq-api-key`).
7. **Health check**: path `/`, os outros valores padrão servem.
8. Revise e clique em **Create & deploy**.

Em alguns minutos o App Runner te dá uma URL pública tipo
`https://xxxxx.us-east-1.awsapprunner.com`. Abra ela e teste o chat.

## Passo 5 — Domínio próprio (opcional)

Se quiser algo como `suporte.bimbambuy.com`:

1. No serviço do App Runner → **Custom domains** → **Link domain**.
2. Siga as instruções para criar os registros CNAME/validação no seu provedor
   de DNS (ou direto no Route 53, se o domínio já estiver lá).

## Atualizando depois de mudar o código

```
AWS_REGION=us-east-1 ./deploy/push_to_ecr.sh
```

- Se o "Deployment trigger" estiver como **Automatic**, o App Runner detecta a
  nova imagem sozinho e faz o redeploy.
- Se estiver como **Manual**, dispare com:
  ```
  aws apprunner start-deployment --service-arn <ARN_DO_SERVICO> --region us-east-1
  ```
  (o ARN aparece na página do serviço no console).

## Se mudar algum PDF em `fonte_de_dados/`

O índice vetorial é gerado durante o `docker build` (dentro do
`push_to_ecr.sh`), então basta rodar o script de novo — ele já reconstrói o
índice com os PDFs atualizados antes de publicar a nova imagem.
