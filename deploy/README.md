# Deploy na AWS (ECS Express Mode)

Guia para colocar o agente no ar usando **Amazon ECS Express Mode** — o jeito
mais simples de rodar um container Docker na AWS sem gerenciar cluster, load
balancer ou VPC manualmente. Ele te dá uma URL pública com HTTPS automático.

> **Nota**: originalmente esse guia usava o AWS App Runner, mas a partir de
> 30/04/2026 a AWS parou de aceitar novos clientes nesse serviço e passou a
> recomendar o ECS Express Mode no lugar (anunciado em nov/2025). É o sucessor
> direto: mesma simplicidade (imagem + porta), infraestrutura por trás baseada
> em Fargate + Application Load Balancer.

## URL em produção

```
https://bi-97edfdad1c8640a39a92b593a43283e8.ecs.us-east-1.on.aws
```

## Por que ECS Express Mode (e não ECS "clássico"/EKS/EC2)

- Você só aponta pra uma imagem no ECR e ele cuida do resto (task definition,
  service, load balancer com SSL/TLS, autoscaling, monitoramento).
- ECS "clássico" ou EKS dão mais controle, mas exigem configurar VPC, ALB,
  task definitions etc. manualmente — overkill pra um único serviço.
- **Sem custo adicional pelo Express Mode em si**: você paga só pelos recursos
  criados (Fargate, Application Load Balancer, CloudWatch Logs). Com a menor
  configuração, fica em torno de alguns dólares por mês rodando 24/7 (não
  escala a zero).

## Passo 1 — Pré-requisitos

1. Instale o [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
   e rode `aws configure` com uma credencial (Access Key + Secret) que tenha
   permissão de ECR, ECS e Secrets Manager.
2. Confirme que está autenticado:
   ```
   aws sts get-caller-identity
   ```
3. **Conta AWS precisa estar com o cadastro completo** (cartão de pagamento
   válido + verificação de identidade). Se aparecer uma tela pedindo pra
   "Concluir configuração da conta" ao tentar criar recursos de computação,
   resolva isso primeiro em https://portal.aws.amazon.com/billing/signup/incomplete
   — sem isso, a criação do serviço falha.

## Passo 2 — Publicar a imagem no ECR

Rode o script incluso neste projeto:

```
AWS_REGION=us-east-1 ./deploy/push_to_ecr.sh
```

Ele cria o repositório ECR (se não existir), builda a imagem e faz o push. No
final ele imprime a URI da imagem, algo como:

```
<conta>.dkr.ecr.us-east-1.amazonaws.com/bimbambuy-agente:latest
```

## Passo 3 — Guardar a chave da Groq no Secrets Manager

```
aws secretsmanager create-secret \
  --name bimbambuy/groq-api-key \
  --secret-string "SUA_CHAVE_AQUI" \
  --region us-east-1
```

Guarde a ARN retornada — vai ser usada no Passo 4.

## Passo 4 — Criar o serviço no ECS Express Mode (console)

1. Acesse o [console do ECS](https://console.aws.amazon.com/ecs/v2) → menu
   lateral **"Express Mode"** → **Create**.
2. **URI da imagem**: cole a URI publicada no Passo 2 (ou use "Procurar
   imagens do ECR").
3. **Registro privado**: deixe desmarcado (é só para registries fora da AWS).
4. **Função de execução de tarefas** e **Perfil da infraestrutura**: deixe em
   "Criar novo perfil" — a AWS cria automaticamente.
5. Expanda **"Configurações adicionais - opcional"**:
   - **Porta do contêiner**: `8000` (é a porta que o `uvicorn` usa)
   - **Caminho da verificação de integridade**: `/`
   - **Variáveis de ambiente** → Adicionar variável de ambiente:
     - Chave: `GROQ_API_KEY`
     - Tipo de valor: **Segredo**
     - Valor: a ARN completa do secret criado no Passo 3
       (`arn:aws:secretsmanager:us-east-1:<conta>:secret:bimbambuy/groq-api-key-XXXXXX`)
   - **Comando**: deixe vazio (o texto de exemplo é só um placeholder)
   - **Função da tarefa**: deixe sem selecionar (o app não chama outras APIs AWS)
   - **Computar**: 1 vCPU / 2 GB para começar (dá pra reduzir depois)
   - **Auto Scaling**: mínimo 1 / máximo 1 (evita escalar sem necessidade)
6. Clique em **Criar**.

⚠️ **Armadilha comum**: a role `ecsTaskExecutionRole` criada automaticamente
**não** tem permissão pra ler segredos do Secrets Manager por padrão. Se a
implantação falhar com `tasks failed to start` e o log da tarefa mostrar
`AccessDeniedException ... secretsmanager:GetSecretValue`, siga o Passo 5.

## Passo 5 — Corrigir permissão do secret (se necessário)

1. IAM Console → **Funções** → busque **`ecsTaskExecutionRole`**
2. **Adicionar permissões** → **Criar política em linha** → aba **JSON**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "secretsmanager:GetSecretValue",
         "Resource": "arn:aws:secretsmanager:us-east-1:<conta>:secret:bimbambuy/groq-api-key-*"
       }
     ]
   }
   ```
3. Nomeie (ex.: `AllowReadGroqSecret`) e crie.
4. Volte no serviço → **"Atualizar o serviço"** → confirme sem mudar nada,
   pra forçar uma nova tentativa de implantação.

## Passo 6 — Testar

Na página do serviço, a **URL da aplicação** já aparece pronta. Abra no
navegador — deve carregar a interface de chat. Para confirmar que o container
realmente está de pé (não só a infra), veja a aba **Logs** do serviço: deve
aparecer `GET / HTTP/1.1 200 OK` repetido (health checks do load balancer).

## Domínio próprio (opcional)

O Express Mode ainda não tem um botão dedicado de "custom domain" como o App
Runner tinha; a forma de fazer isso é apontar um registro CNAME do seu DNS
para a URL gerada, ou configurar isso diretamente no Application Load Balancer
criado pelo Express Mode (visível em EC2 → Load Balancers).

## Atualizando depois de mudar o código

```
AWS_REGION=us-east-1 ./deploy/push_to_ecr.sh
```

Depois, no serviço do ECS Express Mode, clique em **"Atualizar o serviço"**
para que ele puxe a imagem `:latest` mais nova e reimplante.

## Se mudar algum PDF em `fonte_de_dados/`

O índice vetorial é gerado durante o `docker build` (dentro do
`push_to_ecr.sh`), então basta rodar o script de novo — ele já reconstrói o
índice com os PDFs atualizados antes de publicar a nova imagem.
