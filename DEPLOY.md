# 🚀 Deploy do GoMech AI Service

## ✅ Problema Resolvido: Alembic

O erro de **InterpolationSyntaxError** foi corrigido:

### 🔧 Correções Aplicadas:

1. **`alembic.ini` simplificado**: Removidas configurações problemáticas de formatação
2. **`env.py` otimizado**: Configuração direta sem dependência de fileConfig
3. **Comando correto**: Usar `python -m alembic` ao invés de `alembic` diretamente

### 📋 Status Atual:

```bash
✅ Alembic configurado e funcionando
✅ Migrações testadas localmente
✅ Banco de dados compatível (PostgreSQL)
✅ Dockerfile atualizado
✅ Scripts de produção prontos
```

## 🐳 Deploy na Koyeb/Render

### 1. Variáveis de Ambiente Obrigatórias:

```bash
DATABASE_URL=postgresql://user:pass@host:port/database
OPENAI_API_KEY=sk-your-openai-api-key
ENVIRONMENT=production
PORT=8000
HOST=0.0.0.0
```

### 2. Processo de Deploy:

#### **Automático via Dockerfile:**
```bash
# Build
docker build -t gomech-ai-service .

# Run (local test)
docker run -p 8000:8000 \
  -e DATABASE_URL="your-db-url" \
  -e OPENAI_API_KEY="your-api-key" \
  gomech-ai-service
```

#### **Deploy na Koyeb:**
1. Conectar repositório GitHub
2. Configurar variáveis de ambiente
3. Selecionar Dockerfile como build method
4. Deploy automático

#### **Deploy no Render:**
1. Conectar repositório GitHub
2. Configurar variáveis de ambiente
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `python -m alembic upgrade head && gunicorn main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT`

### 3. Comandos de Migração:

```bash
# Verificar status atual
python -m alembic current

# Aplicar migrações
python -m alembic upgrade head

# Marcar migração como aplicada (se tabelas já existem)
python -m alembic stamp head

# Criar nova migração
python -m alembic revision --autogenerate -m "Descrição"
```

### 4. Health Checks:

```bash
# Verificar se o serviço está rodando
curl http://localhost:8000/

# Status detalhado
curl http://localhost:8000/status

# Teste de chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá", "user_id": 1}'
```

## 🔍 Troubleshooting

### Problema: Alembic InterpolationSyntaxError
**Solução**: ✅ **RESOLVIDO** - Usar configuração simplificada

### Problema: Tabelas já existem
**Solução**: 
```bash
python -m alembic stamp head
```

### Problema: Conexão com banco
**Verificar**:
- DATABASE_URL está correto
- Banco PostgreSQL está acessível
- Credenciais estão válidas

### Problema: OpenAI API
**Verificar**:
- OPENAI_API_KEY está configurada
- Conta tem créditos disponíveis
- Rate limits não foram excedidos

## 📊 Monitoramento

### Logs Importantes:
```bash
# Startup
🚀 Iniciando Gomech AI Service...
✅ Variáveis de ambiente verificadas
🔄 Executando migrações do banco de dados...
✅ Migrações executadas com sucesso
🌐 Iniciando servidor...

# Erro comum (resolvido)
❌ InterpolationSyntaxError: bad interpolation variable reference
```

### Endpoints de Monitoramento:
- `GET /` - Health check básico
- `GET /status` - Status detalhado com dependências
- `POST /chat` - Endpoint principal

## 🎯 Próximos Passos

1. **Deploy em produção** ✅ Pronto
2. **Configurar monitoramento** (logs, métricas)
3. **Configurar backup** do banco de dados
4. **Configurar CI/CD** para deploys automáticos
5. **Configurar rate limiting** se necessário

---

**Status**: ✅ **PRONTO PARA PRODUÇÃO**

O serviço está completamente configurado e testado para deploy na Koyeb ou qualquer plataforma de cloud que suporte Docker ou Python.
