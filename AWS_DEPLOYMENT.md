# Plano de Infraestrutura AWS

Como hospedar o backend do CapiDoc (API + Postgres + MongoDB + o resto) gastando o mínimo possível, considerando que no início o volume de usuários é baixo. As decisões aqui já refletem o que foi combinado: RDS para o Postgres, e a correção de performance do gerador de PDF já foi aplicada no código (ver seção "Geração de PDF").

## Visão geral

O que precisa rodar em algum lugar:

| Componente | Onde | Custo |
|---|---|---|
| API (FastAPI) | EC2 | Grátis (free tier, 12 meses) |
| Redis | Mesmo EC2 da API | Grátis (recurso do próprio EC2) |
| PostgreSQL | RDS | Grátis (free tier, 12 meses) |
| MongoDB | MongoDB Atlas (fora da AWS) | **Grátis para sempre** (tier M0) |
| Arquivos (fotos, PDFs, templates) | S3 | Grátis até 5GB (free tier, 12 meses; depois é centavos por GB) |
| WAHA (gateway WhatsApp) | Mesmo EC2 da API | Grátis (recurso do próprio EC2) |
| n8n | Mesmo EC2 da API, ou n8n Cloud | Grátis (self-hosted) |

Nada aqui exige cartão de crédito cobrado além do que já é padrão pra criar conta AWS (que pede cartão mas não cobra nada dentro do free tier).

## Por que essa combinação

### EC2 — computação
`t3.micro` ou `t4g.micro` (ARM, mais barato e geralmente mais eficiente por watt — vale checar disponibilidade na região escolhida). 750 horas/mês grátis nos primeiros 12 meses de uma conta AWS nova, o que cobre 1 instância rodando 24/7 sem custo. Depois dos 12 meses, gira em torno de US$7-8/mês (t4g.micro) se continuar nessa instância.

Roda nele, via Docker Compose (o mesmo `docker-compose.yml` do projeto, só tirando os serviços que migram pra fora): API, Redis, WAHA e opcionalmente n8n.

### PostgreSQL — RDS
`db.t3.micro`, free tier: 750h/mês + 20GB de armazenamento, grátis nos primeiros 12 meses. Trade-off que você já escolheu: menos trabalho operacional (backup automático, restore point-in-time, patch de segurança automático) em troca de, depois dos 12 meses, um custo de ~US$12-15/mês se continuar no RDS. Dá pra migrar pra Postgres self-hosted no mesmo EC2 depois, se quiser cortar esse custo quando o free tier acabar — é só um `pg_dump`/`pg_restore`, não exige mudança de código (a app já usa a `DATABASE_URL` via variável de ambiente).

### MongoDB — Atlas, não AWS
A AWS não tem um serviço de MongoDB gratuito de verdade — o DocumentDB (o "equivalente" da AWS) não entra no free tier e já começa caro. A peça que resolve isso é o **MongoDB Atlas**, o serviço gerenciado do próprio time do MongoDB: o tier **M0** é gratuito **permanentemente** (não é trial), com 512MB de armazenamento — suficiente pra um volume inicial baixo de formulários/atendimentos. Dá pra criar o cluster M0 já na região `sa-east-1` (São Paulo) ou `us-east-1`, o que mantém a latência baixa até com a API rodando na AWS.

Quando o volume crescer e passar de 512MB, o próximo degrau pago do Atlas (M2/M5) começa em ~US$9/mês — ainda mais barato que rodar DocumentDB.

### Arquivos — S3 no lugar do MinIO
O `StorageService` do backend já fala com o storage via boto3 usando a API S3 (é assim que o MinIO local funciona hoje). Trocar pra S3 de verdade é só mudar a URL do endpoint e as credenciais no `.env` — **zero mudança de código**. Isso também tira o MinIO da lista de containers que precisam rodar no EC2 pequeno, sobrando mais RAM pra API/Redis/WAHA.

5GB grátis nos primeiros 12 meses; depois disso, S3 cobra por GB armazenado e por request, mas pra fotos de atendimento + PDFs gerados com baixo volume isso fica na casa de centavos por mês.

## Geração de PDF (já resolvido no código)

A preocupação original era: gerar PDF é CPU-intensivo (PyMuPDF pra documentos com template, PyMuPDF + openpyxl pra relatórios), e isso rodando numa instância pequena poderia travar outras requisições enquanto processa — porque antes essas chamadas rodavam de forma síncrona dentro do event loop do FastAPI, e Python com asyncio é single-threaded: uma chamada síncrona pesada bloqueia literalmente tudo mais que estivesse em andamento, mesmo dentro de uma `BackgroundTask`.

**Isso já foi corrigido**: `render_document_pdf` (documentos) e `render_report_file` (relatórios) agora rodam via `starlette.concurrency.run_in_threadpool`, então a geração acontece numa thread separada e não trava o loop principal — outras requisições continuam sendo atendidas normalmente enquanto um PDF grande está sendo montado. Isso ajuda independente do tamanho da instância escolhida, mas é especialmente importante numa `t3.micro`/`t4g.micro` com poucos vCPUs.

## Ordem recomendada de setup

1. Criar conta AWS (se ainda não tiver) e conta MongoDB Atlas.
2. Criar o cluster Atlas M0, configurar usuário de banco e liberar o IP do EC2 (ou `0.0.0.0/0` temporariamente até restringir depois) na whitelist de rede do Atlas.
3. Criar o bucket S3 e um usuário IAM com permissão restrita só a esse bucket (não usar a conta root nem credenciais amplas).
4. Criar a instância RDS Postgres (free tier), anotar o endpoint.
5. Subir a instância EC2, instalar Docker + Docker Compose.
6. Ajustar o `.env` de produção: `POSTGRES_HOST` apontando pro endpoint do RDS, `MONGO_DSN` apontando pro Atlas (string de conexão `mongodb+srv://...`), `S3_ENDPOINT_URL`/credenciais apontando pro S3 real, e trocar todos os `change-this-secret-in-production`.
7. `docker compose up -d` no EC2 (sem os serviços `postgres` e `mongodb` do compose local, já que esses agora são externos).
8. Rodar as migrações do Alembic apontando pro RDS (o `entrypoint.sh` já faz isso automaticamente na subida do container).
9. Configurar Security Group do EC2: liberar só as portas necessárias (443/80 pra API atrás de um proxy, ou 8000 direto se ainda não tiver domínio/TLS) — nunca deixar Postgres/Mongo/Redis expostos publicamente.

## Estimativa de custo

| Período | Custo mensal aproximado |
|---|---|
| Meses 1–12 (dentro do free tier AWS) | **US$0** (Atlas M0 é grátis mesmo depois) |
| Após 12 meses, mantendo RDS | ~US$20-25/mês (EC2 + RDS + S3 residual) |
| Após 12 meses, migrando Postgres pro EC2 | ~US$8-10/mês (só EC2 + S3 residual, Atlas continua grátis) |

## Cuidados

- Nunca commitar o `.env` de produção com as credenciais reais — usar o `.env.example` como referência e manter os segredos fora do controle de versão (ou usar AWS Secrets Manager/Parameter Store mais pra frente).
- Restringir a whitelist de rede do Atlas ao IP do EC2 assim que ele tiver IP fixo (Elastic IP), em vez de deixar aberto.
- Monitorar o uso do free tier pelo AWS Billing Dashboard — é possível configurar um alarme de orçamento (`Budgets`) em US$1 pra ser avisado antes de qualquer cobrança inesperada.
- O tier M0 do Atlas tem limite de conexões simultâneas mais baixo que os pagos — não é um problema com poucos usuários, mas é o primeiro lugar a olhar se aparecer erro de conexão sob carga.
