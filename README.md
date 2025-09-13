# GoMech AI Service

Serviço de IA para o sistema GoMech, construído com FastAPI e LangChain.

## 🚀 Deploy na Koyeb

### Pré-requisitos

1. **Conta na Koyeb**: [koyeb.com](https://www.koyeb.com)
2. **Banco PostgreSQL**: Configure um banco PostgreSQL (pode usar Koyeb Database ou serviços externos)
3. **OpenAI API Key**: Obtenha em [platform.openai.com](https://platform.openai.com)

### Configuração das Variáveis de Ambiente

Configure as seguintes variáveis no painel da Koyeb:

```bash
# Obrigatórias
DATABASE_URL=postgresql://username:password@host:port/database
OPENAI_API_KEY=sk-your-openai-api-key

# Opcionais
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_TRACING=false
ENVIRONMENT=production
```

### Deploy Automático

1. **Fork/Clone** este repositório
2. **Conecte** o repositório à Koyeb
3. **Configure** as variáveis de ambiente
4. **Deploy** será automático via Dockerfile

### Deploy Manual

```bash
# 1. Build da imagem
docker build -t gomech-ai-service .

# 2. Run local (para testes)
docker run -p 8000:8000 \
  -e DATABASE_URL="your-db-url" \
  -e OPENAI_API_KEY="your-api-key" \
  gomech-ai-service

# 3. Push para registry da Koyeb
# (seguir instruções específicas da Koyeb)
```

## 🗄️ Migrações do Banco de Dados

Este projeto usa **Alembic** para gerenciar migrações:

### Comandos Úteis

```bash
# Criar nova migração
alembic revision --autogenerate -m "Descrição da mudança"

# Aplicar migrações
alembic upgrade head

# Reverter migração
alembic downgrade -1

# Ver histórico
alembic history

# Ver migração atual
alembic current
```

### Estrutura do Banco

O serviço cria as seguintes tabelas:

- `conversations`: Armazena conversas dos usuários
- `messages`: Armazena mensagens individuais
- `users`: Tabela compartilhada com o backend Spring Boot

## 🔧 Desenvolvimento Local

### Instalação

```bash
# 1. Clone o repositório
git clone <repo-url>
cd gomech-ai-service

# 2. Instale dependências
pip install -r requirements.txt

# 3. Configure variáveis de ambiente
cp env.example .env
# Edite .env com suas configurações

# 4. Execute migrações
alembic upgrade head

# 5. Inicie o servidor
python main.py
```

### Estrutura do Projeto

```
gomech-ai-service/
├── agents/                 # Agentes de IA especializados
│   ├── chat_agent.py      # Agente de conversação
│   ├── sql_agent.py       # Agente de consultas SQL
│   └── chart_agent.py     # Agente de gráficos
├── alembic/               # Migrações do banco
│   ├── versions/          # Arquivos de migração
│   └── env.py            # Configuração do Alembic
├── utils/                 # Utilitários
├── main.py               # Aplicação principal
├── models.py             # Modelos SQLAlchemy
├── schemas.py            # Schemas Pydantic
├── router_agent.py       # Roteador de mensagens
├── requirements.txt      # Dependências Python
├── Dockerfile           # Container Docker
└── README.md           # Este arquivo
```

## 📊 Endpoints

### POST /chat
Endpoint principal para conversação com a IA.

**Request:**
```json
{
  "message": "Quantos clientes temos?",
  "user_id": 1,
  "thread_id": "optional-thread-id"
}
```

**Response:**
```json
{
  "reply": "Vocês têm 150 clientes cadastrados.",
  "thread_id": "generated-or-provided-thread-id",
  "image_base64": null,
  "image_mime": null
}
```

### GET /status
Verifica o status do serviço e suas dependências.

### GET /
Health check básico.

## 🔍 Monitoramento

### Health Checks

O serviço inclui health checks automáticos:

- **Endpoint**: `GET /`
- **Status detalhado**: `GET /status`
- **Docker health check**: Configurado no Dockerfile

### Logs

Os logs são estruturados e incluem:

- Requisições recebidas
- Erros de banco de dados
- Chamadas para APIs externas
- Performance dos agentes

## 🚨 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com banco**
   - Verifique `DATABASE_URL`
   - Confirme que o banco está acessível
   - Execute `alembic upgrade head`

2. **Erro de API OpenAI**
   - Verifique `OPENAI_API_KEY`
   - Confirme que tem créditos disponíveis
   - Verifique rate limits

3. **Timeout nas requisições**
   - Aumente timeout do Gunicorn
   - Verifique performance do banco
   - Monitore uso de CPU/memória

### Logs de Debug

Para habilitar logs detalhados:

```bash
# Desenvolvimento
export LOG_LEVEL=DEBUG
python main.py

# Produção (via Gunicorn)
gunicorn main:app --log-level debug
```

## 📈 Performance

### Configurações Recomendadas

- **Koyeb Instance**: Nano (para início) → Small (produção)
- **Workers**: 2-4 (dependendo da instância)
- **Timeout**: 120s (para consultas complexas)
- **Max Requests**: 1000 (restart workers periodicamente)

### Otimizações

1. **Connection Pooling**: Configurado no SQLAlchemy
2. **Keep-Alive**: Configurado no Gunicorn
3. **Request Limits**: Evita memory leaks
4. **Health Checks**: Detecta problemas rapidamente

## 🔐 Segurança

- **Variáveis de ambiente**: Nunca commite secrets
- **HTTPS**: Sempre use em produção
- **Rate Limiting**: Considere implementar
- **Input Validation**: Schemas Pydantic
- **SQL Injection**: Protegido pelo SQLAlchemy

## 📞 Suporte

Para problemas ou dúvidas:

1. Verifique os logs do serviço
2. Consulte este README
3. Verifique o status das dependências
4. Entre em contato com a equipe de desenvolvimento
