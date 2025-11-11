import os
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

logger = logging.getLogger(__name__)
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=OPENAI_API_KEY)


# ========================================
# Integração com Backend - Auditoria
# ========================================

def _fetch_audit_events(user_email: Optional[str] = None, 
                        action_type: Optional[str] = None,
                        days_back: int = 30) -> List[Dict[str, Any]]:
    """
    Busca eventos de auditoria do backend Java.
    
    Args:
        user_email: Email do usuário (filtro opcional)
        action_type: Tipo de ação (CREATE, UPDATE, DELETE)
        days_back: Quantos dias buscar no histórico
    """
    try:
        # Calcular data inicial
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Montar parâmetros da query
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "page": 0,
            "size": 50
        }
        
        if user_email:
            params["userEmail"] = user_email
        if action_type:
            params["actionType"] = action_type
        
        response = requests.get(
            f"{BACKEND_URL}/audit/events",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("content", [])
        else:
            logger.warning(f"⚠️ [Audit] Backend retornou status {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"❌ [Audit] Erro ao buscar eventos: {str(e)}")
        return []


def _fetch_lgpd_status(user_email: str) -> Dict[str, Any]:
    """
    Verifica status LGPD de um usuário (exclusões pendentes, solicitações).
    """
    try:
        response = requests.get(
            f"{BACKEND_URL}/lgpd/status",
            params={"userEmail": user_email},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "unknown", "message": "Não foi possível verificar status LGPD"}
            
    except Exception as e:
        logger.error(f"❌ [Audit] Erro ao verificar status LGPD: {str(e)}")
        return {"status": "error", "message": str(e)}


def _format_audit_events(events: List[Dict[str, Any]]) -> str:
    """
    Formata eventos de auditoria em texto legível.
    """
    if not events:
        return "📋 Nenhum evento de auditoria encontrado no período especificado."
    
    formatted = ["📋 **Eventos de Auditoria Recentes:**\n"]
    
    for event in events[:10]:  # Limitar a 10 eventos
        occurred_at = event.get("occurredAt", "Data desconhecida")
        event_type = event.get("eventType", "Evento desconhecido")
        user_email = event.get("userEmail", "Usuário desconhecido")
        operation = event.get("operation", "")
        module = event.get("moduleName", "")
        
        # Traduzir operações
        operation_map = {
            "CREATE": "Criação",
            "UPDATE": "Atualização",
            "DELETE": "Exclusão",
            "READ": "Leitura",
            "LOGIN": "Login",
            "LOGOUT": "Logout"
        }
        operation_text = operation_map.get(operation, operation)
        
        formatted.append(f"• **{occurred_at}** - {operation_text} em {module}")
        formatted.append(f"  👤 Usuário: {user_email}")
        
        if event.get("blockchainReference"):
            formatted.append(f"  🔗 Blockchain: {event['blockchainReference'][:16]}...")
        
        formatted.append("")
    
    if len(events) > 10:
        formatted.append(f"_... e mais {len(events) - 10} eventos_")
    
    return "\n".join(formatted)


# ========================================
# Respostas Explicativas
# ========================================

SECURITY_FAQ = {
    "protecao": """
🛡️ **Como o GoMech protege seus dados:**

1. **Criptografia em Trânsito e Repouso**
   • Todas as comunicações usam HTTPS/TLS
   • Dados sensíveis são criptografados com AES-256-GCM
   • Senhas nunca são armazenadas em texto puro (BCrypt)

2. **Controle de Acesso**
   • Autenticação JWT com tokens de curta duração
   • Controle baseado em funções (ADMIN, USER)
   • MFA (Autenticação Multi-Fator) disponível

3. **Auditoria Imutável**
   • Todos os eventos críticos são registrados
   • Hash SHA-256 para garantir integridade
   • Integração com Blockchain para rastreabilidade

4. **Isolamento Multi-Tenancy**
   • Dados de cada oficina completamente isolados
   • Queries automáticas com filtro de organização
   • Impossível acessar dados de outras empresas

5. **Backups Seguros**
   • Backups automáticos diários
   • Criptografados antes do armazenamento
   • Testados regularmente para restauração
""",
    "lgpd": """
🔒 **Conformidade LGPD no GoMech:**

**Direitos dos Titulares:**
• **Acesso** - Você pode consultar quais dados temos sobre você
• **Correção** - Dados incorretos podem ser atualizados a qualquer momento
• **Exclusão** - Direito ao esquecimento (com ressalvas legais)
• **Portabilidade** - Exportar seus dados em formato estruturado
• **Revogação** - Retirar consentimento de processamento

**Bases Legais:**
• **Execução de contrato** - Dados necessários para prestação do serviço
• **Legítimo interesse** - Segurança, prevenção de fraude, melhorias
• **Obrigação legal** - Retenção para fins fiscais e contábeis

**Retenção de Dados:**
• Dados operacionais: enquanto houver relação comercial
• Dados fiscais: 5 anos (legislação brasileira)
• Dados de auditoria: 3 anos
• Backups: 90 dias

**DPO (Encarregado):**
• Contato: dpo@gomech.com
• Horário: Seg-Sex, 9h-18h

**Segurança:**
• Criptografia de ponta a ponta
• Auditoria contínua de acessos
• Treinamento periódico da equipe
• Plano de resposta a incidentes
""",
    "blockchain": """
⛓️ **Blockchain no GoMech:**

**Por que usamos Blockchain?**
O GoMech integra tecnologia blockchain para garantir **imutabilidade** e **rastreabilidade** dos eventos críticos.

**O que é registrado:**
• Criação/alteração de ordens de serviço
• Exclusão de dados sensíveis
• Alterações em valores financeiros
• Acessos administrativos
• Execução de backups

**Como funciona:**
1. Evento ocorre no sistema
2. Hash criptográfico (SHA-256) é gerado
3. Hash é publicado na blockchain
4. Referência blockchain é armazenada no banco

**Benefícios:**
✅ **Prova de Integridade** - Impossível alterar histórico
✅ **Transparência** - Auditoria independente
✅ **Conformidade** - Evidências para auditorias
✅ **Confiança** - Rastreabilidade completa

**Nota:** Apenas os hashes são registrados na blockchain, nunca dados pessoais ou sensíveis.
""",
    "acessos": """
👁️ **Monitoramento de Acessos:**

O GoMech registra automaticamente:
• **Logins/Logouts** - Quando e de onde você acessou
• **Alterações** - Quem modificou cada registro
• **Exclusões** - Histórico de dados removidos
• **Acessos Administrativos** - Ações de admins são auditadas
• **Exportações** - Downloads de relatórios e dados

**Como consultar seus acessos:**
1. Use este chat: "Quais acessos ocorreram na minha conta?"
2. Acesse: Menu → Segurança → Histórico de Acessos
3. Entre em contato: suporte@gomech.com

**Alertas Automáticos:**
🚨 Login de novo dispositivo
🚨 Acesso fora do horário habitual
🚨 Múltiplas tentativas de login falhas
🚨 Alteração de dados críticos

Você receberá notificações via email quando eventos suspeitos ocorrerem.
"""
}


# ========================================
# Prompt do Agente
# ========================================

_audit_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é o Agente de Segurança e Conformidade do GoMech.

🔐 **SUA MISSÃO:**
Garantir transparência, segurança e conformidade com LGPD.

📋 **SUAS CAPACIDADES:**
1. Explicar medidas de segurança do sistema
2. Responder dúvidas sobre LGPD e privacidade
3. Consultar logs de auditoria e acessos
4. Verificar status de solicitações LGPD
5. Orientar sobre direitos dos titulares de dados
6. Explicar uso de blockchain na auditoria

🎯 **DIRETRIZES:**
- Seja transparente e técnico quando necessário
- Use linguagem acessível para explicar conceitos complexos
- Sempre mencione as bases legais (LGPD)
- Reforce a segurança e privacidade como prioridades
- Ofereça links e contatos quando pertinente
- Nunca exponha dados sensíveis ou hashes completos

📊 **CONTEXTO ADICIONAL:**
{context}

Responda de forma clara, profissional e empática.
"""),
    ("human", "{question}")
])


# ========================================
# Função Principal
# ========================================

def run_audit_agent(question: str, user_email: Optional[str] = None) -> str:
    """
    Agente especializado em segurança, auditoria e LGPD.
    
    Args:
        question: Pergunta do usuário
        user_email: Email do usuário para consultas personalizadas
    
    Returns:
        Resposta formatada com informações de auditoria/segurança
    """
    logger.info(f"🔒 [Audit Agent] Pergunta: {question}")
    question_lower = question.lower()
    
    context = ""
    
    # Detectar tipo de pergunta e enriquecer contexto
    
    # 1. Consulta de acessos específicos
    if any(word in question_lower for word in ["acessos", "quem acessou", "login", "histórico"]):
        if user_email:
            events = _fetch_audit_events(user_email=user_email, days_back=30)
            context += f"\n\n{_format_audit_events(events)}"
        else:
            context += "\n\n⚠️ Não foi possível identificar seu email para consultar acessos específicos."
    
    # 2. Verificação LGPD
    if "lgpd" in question_lower or "exclusão" in question_lower or "dados pessoais" in question_lower:
        if user_email:
            lgpd_status = _fetch_lgpd_status(user_email)
            if lgpd_status.get("pending_requests"):
                context += "\n\n📋 **Status LGPD:**\n"
                context += f"• Solicitações pendentes: {lgpd_status.get('pending_requests', 0)}\n"
                if lgpd_status.get("deletion_scheduled"):
                    context += f"• Exclusão agendada para: {lgpd_status.get('deletion_date')}\n"
        context += f"\n\n{SECURITY_FAQ['lgpd']}"
    
    # 3. Perguntas sobre proteção/segurança
    if any(word in question_lower for word in ["protege", "segurança", "seguro", "criptografia"]):
        context += f"\n\n{SECURITY_FAQ['protecao']}"
    
    # 4. Perguntas sobre blockchain
    if "blockchain" in question_lower or "rastreab" in question_lower:
        context += f"\n\n{SECURITY_FAQ['blockchain']}"
    
    # 5. Perguntas sobre monitoramento
    if any(word in question_lower for word in ["monitoramento", "auditoria", "rastreio", "log"]):
        context += f"\n\n{SECURITY_FAQ['acessos']}"
        # Buscar eventos recentes gerais
        recent_events = _fetch_audit_events(days_back=7)
        if recent_events:
            context += f"\n\n📊 **Estatísticas (últimos 7 dias):**\n"
            context += f"• Total de eventos auditados: {len(recent_events)}\n"
            
            # Contar por tipo de operação
            operations = {}
            for event in recent_events:
                op = event.get("operation", "Desconhecido")
                operations[op] = operations.get(op, 0) + 1
            
            for op, count in sorted(operations.items(), key=lambda x: x[1], reverse=True):
                context += f"• {op}: {count} eventos\n"
    
    # Invocar LLM com contexto enriquecido
    try:
        chain = _audit_prompt | _llm
        result = chain.invoke({
            "question": question,
            "context": context
        })
        response = result.content.strip()
        
        logger.info(f"✅ [Audit Agent] Resposta gerada com sucesso")
        return response
        
    except Exception as e:
        logger.error(f"❌ [Audit Agent] Erro: {str(e)}", exc_info=True)
        return """
🔒 **Agente de Segurança e Conformidade**

Desculpe, tive um problema ao processar sua pergunta sobre segurança/auditoria.

**Posso te ajudar com:**
• Como o sistema protege seus dados
• Direitos LGPD (acesso, correção, exclusão)
• Consultar logs de auditoria
• Verificar acessos à sua conta
• Explicar uso de blockchain
• Políticas de segurança e privacidade

**Contatos:**
📧 Segurança: security@gomech.com
📧 DPO/LGPD: dpo@gomech.com
📞 Suporte: (11) 1234-5678

Tente reformular sua pergunta! 🛡️
"""
