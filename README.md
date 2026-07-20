# CapiDoc Backend

API REST em FastAPI para o ecossistema CapiDoc: cadastro de operadores, formulários dinâmicos, atendimentos em campo, geração de documentos/relatórios em PDF/Excel/CSV, e canais de entrada via app Android, WhatsApp (n8n + WAHA) e extração de dados de documentos por IA.

## Stack

- **FastAPI** + **Pydantic v2** — API e validação
- **PostgreSQL** (SQLAlchemy 2.0 async + Alembic) — dados relacionais/multi-tenant (orgs, projetos, usuários, permissões, dispositivos, relatórios, autorizações do WhatsApp, atividades, notificações)
- **MongoDB** (PyMongo async) — dados de formato dinâmico (formulários, atendimentos, jornadas/GPS)
- **Redis** — cache, pub/sub (canal STOMP em tempo real), rate limiting
- **S3 / MinIO** — armazenamento de arquivos (fotos, PDFs gerados, templates)
- **PyMuPDF** — renderização de PDF (documentos com template + relatórios)
- **openpyxl** — geração de relatórios em Excel

## Arquitetura

Cada módulo em `app/modules/<nome>/` segue a mesma estrutura em camadas:

```
<modulo>/
  domain/          # entidades e Protocols de repositório (sem dependência de framework)
  infrastructure/  # implementação dos repositórios (SQLAlchemy ou PyMongo)
  application/     # regras de negócio (services) + schemas de request/response
  api/v1/          # endpoints FastAPI + wiring de dependências
```

### Módulos

| Módulo | Responsabilidade |
|---|---|
| `auth` | Login, refresh token, troca de senha, recuperação de senha por código (OTP) |
| `organizations` / `projects` / `departments` | Estrutura multi-tenant |
| `users` / `operators` | Contas e operadores de campo |
| `permissions` | Grupos de permissão + concessões individuais por recurso |
| `forms` | Formulários dinâmicos (campos, template de PDF, publicação) |
| `attendances` | Respostas de formulário preenchidas em campo |
| `documents` | Geração de PDF a partir de um atendimento + template |
| `document_imports` | Extração de dados de PDF/imagem via IA (n8n) para pré-preencher um atendimento |
| `reports` | Relatórios agregados (PDF/Excel/CSV), gerados em background |
| `devices` | Dispositivos móveis autorizados, exigências de foto/GPS na jornada |
| `journeys` | Início/fim de jornada e trilha de GPS |
| `mobile` | Endpoints dedicados ao app Android (nunca reaproveita os endpoints "web") |
| `dashboards_custom` | Dashboards configuráveis pelo usuário |
| `notifications` | Notificações in-app (sino do header, tela de notificações do Android) |
| `activities` | Log de atividade recente (dashboard) |
| `validation` | Validação pública de documento por código (sem autenticação) |
| `whatsapp_auth` | Allowlist de números autorizados a usar o bot do WhatsApp (validade + renovação automática) |
| `whatsapp_bot` | Motor da conversa do bot (preenchimento de formulário via WhatsApp) |

## Integrações externas

- **n8n**: dois fluxos, ambos com o backend fazendo o trabalho pesado e o n8n como orquestrador/relay:
  - Extração de documento por IA → `app/modules/document_imports/` (webhook de saída com JSON Schema pronto para nós de IA estruturada, callback de entrada autenticado por segredo)
  - Bot do WhatsApp → `app/modules/whatsapp_bot/` (endpoint `POST /whatsapp/messages`, autenticado por segredo, retorna o texto da próxima resposta)
- **WAHA** (WhatsApp HTTP API): gateway do WhatsApp — o backend não fala com o WAHA diretamente, só o n8n

## Como rodar localmente

Pré-requisitos: Docker + Docker Compose.

```bash
cp .env.example .env
docker compose up -d
```

Isso sobe API, Postgres, MongoDB, Redis, MinIO e WAHA. O `entrypoint.sh` roda as migrações do Alembic e faz o seed do admin padrão automaticamente na subida.

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- MinIO console: http://localhost:9001
- WAHA dashboard: http://localhost:3000

### Variáveis de ambiente

Veja `.env.example` — todas as seções têm comentário explicando o propósito. Os únicos valores que **precisam** ser trocados antes de produção são os marcados `change-this-*-in-production` (segredos de webhook do n8n/WhatsApp e credenciais do WAHA).

### Migrações

```bash
docker exec capidoc-api alembic revision --autogenerate -m "descrição"
docker exec capidoc-api alembic upgrade head
```

### Testes

```bash
docker exec capidoc-api pip install -r requirements-dev.txt
docker exec capidoc-api sh -c "cd /app && python -m pytest tests/ -v"
```

Testes unitários (fakes em memória, sem depender de banco real) — ver `tests/README.md`.

## Retenção de dados

Uma tarefa em background (iniciada no `lifespan` da aplicação, sem scheduler externo) limpa periodicamente atividades e notificações lidas antigas — configurável via `ACTIVITY_RETENTION_DAYS`, `NOTIFICATION_RETENTION_DAYS` e `RETENTION_CLEANUP_INTERVAL_HOURS` no `.env`.
