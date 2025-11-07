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

### Pré-requisitos

- Python 3.11 ou superior
- PostgreSQL 16 (local ou remoto)
- pip (gerenciador de pacotes Python)

### Instalação

```bash
# 1. Clone o repositório
git clone <repo-url>
cd gomech-ai-service

# 2. Crie um ambiente virtual (venv)
python3 -m venv venv

# 3. Ative o ambiente virtual
# No Linux/macOS:
source venv/bin/activate

# No Windows:
# venv\Scripts\activate

# 4. Atualize pip (recomendado)
pip install --upgrade pip

# 5. Instale as dependências
pip install -r requirements.txt

# 6. Configure variáveis de ambiente
cp env.example .env
# Edite .env com suas configurações

# 7. Execute migrações do banco
alembic upgrade head

# 8. Inicie o servidor
python main.py
```

### Gerenciamento do Ambiente Virtual

```bash
# Ativar ambiente virtual
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Desativar ambiente virtual
deactivate

# Verificar pacotes instalados
pip list

# Atualizar requirements.txt (se adicionar novos pacotes)
pip freeze > requirements.txt

# Reinstalar dependências (após git pull)
pip install -r requirements.txt --upgrade
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
# Desenvolvimento (com venv ativo)
source venv/bin/activate  # Ative o venv primeiro
export LOG_LEVEL=DEBUG
python main.py

# Produção (via Gunicorn)
gunicorn main:app --log-level debug
```

### Testes Locais

```bash
# Ative o ambiente virtual
source venv/bin/activate

# Teste o health check
curl http://localhost:5000/health

# Teste o endpoint de chat
curl -X POST http://localhost:5000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Quantos clientes temos?",
    "user_id": 1,
    "thread_id": "test-thread"
  }'
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
- **Ambiente Virtual**: Use venv para isolar dependências

## 📝 Boas Práticas de Desenvolvimento

### 1. Sempre Use Ambiente Virtual

```bash
# SEMPRE ative o venv antes de trabalhar
source venv/bin/activate

# Verifique se está no venv (deve aparecer (venv) no prompt)
which python  # Deve apontar para venv/bin/python
```

### 2. Mantenha Dependências Atualizadas

```bash
# Verificar pacotes desatualizados
pip list --outdated

# Atualizar pacote específico
pip install --upgrade nome-do-pacote

# Atualizar requirements.txt
pip freeze > requirements.txt
```

### 3. Estrutura de Diretórios

```
gomech-ai-service/
├── venv/                  # Ambiente virtual (NÃO commitar)
├── agents/                # Agentes de IA
├── alembic/              # Migrações
├── utils/                # Utilitários
├── .env                  # Variáveis (NÃO commitar)
├── .gitignore            # Ignora venv, .env, __pycache__
├── requirements.txt      # Dependências
└── main.py              # App principal
```

### 4. .gitignore Recomendado

```
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp

# Logs
*.log
```

## 🐛 Troubleshooting Detalhado

### Erro: "ModuleNotFoundError"

```bash
# Causa: Ambiente virtual não ativado ou dependências não instaladas
# Solução:
source venv/bin/activate
pip install -r requirements.txt
```

### Erro: "Command 'python' not found"

```bash
# Causa: Python não instalado ou não no PATH
# Solução:
# Instale Python 3.11+
sudo apt-get install python3.11 python3.11-venv  # Ubuntu/Debian
# ou
brew install python@3.11  # macOS

# Use python3 explicitamente
python3 -m venv venv
```

### Erro: "Permission denied" ao ativar venv

```bash
# Causa: Problemas de permissão
# Solução:
chmod +x venv/bin/activate
source venv/bin/activate
```

### Erro: "SQLAlchemy connection error"

```bash
# Causa: DATABASE_URL incorreta ou PostgreSQL não acessível
# Solução:
# 1. Verifique .env
cat .env | grep DATABASE_URL

# 2. Teste conexão PostgreSQL
psql $DATABASE_URL

# 3. Verifique se PostgreSQL está rodando
docker-compose ps postgres  # Se usando Docker
# ou
sudo systemctl status postgresql  # Linux
```

### Erro: "relation 'messages' does not exist"

```bash
# Causa: Tabelas não criadas no banco de dados
# Solução:

# 1. Aplique as migrations
source venv/bin/activate  # Ative o venv primeiro
alembic upgrade head

# 2. Se o erro persistir, crie as tabelas manualmente
# (veja TROUBLESHOOTING.md para script SQL completo)

# 3. Marque a migration como aplicada
alembic stamp head

# 4. Verifique o estado
alembic current
# Deve mostrar: 001 (head)

# 5. Reinicie o serviço
python main.py
```

**Nota**: Para instruções completas de troubleshooting, consulte o arquivo `TROUBLESHOOTING.md`.

## 📞 Suporte

Para problemas ou dúvidas:

1. **Verifique o ambiente virtual**: `which python` deve apontar para `venv/bin/python`
2. **Verifique os logs**: `docker-compose logs fastapi` (Docker) ou `tail -f logs/app.log` (local)
3. **Consulte este README**: Especialmente seções de Troubleshooting
4. **Verifique dependências**: `pip list` no venv ativado
5. **Status do serviço**: `curl http://localhost:5000/status`
6. **Entre em contato**: equipe de desenvolvimento

---

## 🚀 Quick Start (Resumo)

```bash
# Setup inicial
git clone <repo-url>
cd gomech-ai-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp env.example .env
# Edite .env com suas credenciais
alembic upgrade head
python main.py

# Uso diário
source venv/bin/activate  # Sempre primeiro!
python main.py            # Inicia servidor

# Deploy Docker
docker-compose up -d      # Não precisa de venv no container
```

**Última atualização:** 2025-11-07  
**Versão:** 2.0.0 (com suporte venv)
