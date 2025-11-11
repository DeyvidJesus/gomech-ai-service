import os
import re
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=OPENAI_API_KEY)


# ========================================
# Análise de Sentimento (NLP)
# ========================================

# Palavras-chave para análise de sentimento (português)
POSITIVE_KEYWORDS = [
    "ótimo", "excelente", "perfeito", "maravilhoso", "amo", "adorei", "amei",
    "top", "show", "legal", "bom", "boa", "obrigado", "obrigada", "parabéns",
    "satisfeito", "satisfeita", "feliz", "recomendo", "melhor", "qualidade",
    "rápido", "rápida", "eficiente", "profissional", "atencioso", "educado"
]

NEGATIVE_KEYWORDS = [
    "péssimo", "horrível", "ruim", "terrível", "decepcionado", "decepcionada",
    "insatisfeito", "insatisfeita", "problema", "reclamação", "demora", "demorado",
    "caro", "errado", "erro", "falha", "não funciona", "quebrado", "defeito",
    "nunca", "pior", "mau", "má", "desorganizado", "bagunça", "desrespeito",
    "mal", "mal atendido", "grosseiro", "grosseira", "incompetente"
]

URGENT_KEYWORDS = [
    "urgente", "emergência", "quebrado", "parado", "não funciona", "não liga",
    "vazamento", "acidente", "perigo", "risco", "imediato", "agora", "já"
]


def _analyze_sentiment_simple(text: str) -> Dict[str, Any]:
    """
    Análise de sentimento simples baseada em palavras-chave.
    
    Returns:
        Dict com sentiment ("POSITIVE", "NEUTRAL", "NEGATIVE") e score (0-1)
    """
    text_lower = text.lower()
    
    # Contar palavras positivas e negativas
    positive_count = sum(1 for word in POSITIVE_KEYWORDS if word in text_lower)
    negative_count = sum(1 for word in NEGATIVE_KEYWORDS if word in text_lower)
    
    # Calcular score
    total = positive_count + negative_count
    if total == 0:
        return {"sentiment": "NEUTRAL", "score": 0.5}
    
    positive_ratio = positive_count / total
    
    if positive_ratio >= 0.6:
        return {"sentiment": "POSITIVE", "score": positive_ratio}
    elif positive_ratio <= 0.4:
        return {"sentiment": "NEGATIVE", "score": 1 - positive_ratio}
    else:
        return {"sentiment": "NEUTRAL", "score": 0.5}


def _is_urgent(text: str) -> bool:
    """Detecta se a mensagem é urgente."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in URGENT_KEYWORDS)


# ========================================
# Classificação de Tipo de Mensagem
# ========================================

_classify_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é um classificador de mensagens de clientes para uma oficina mecânica.

Analise a mensagem e classifique em uma das categorias:
- **SATISFACTION** - Avaliação de satisfação, feedback positivo
- **COMPLAINT** - Reclamação, problema, insatisfação
- **SUGGESTION** - Sugestão de melhoria
- **COMPLIMENT** - Elogio, agradecimento
- **QUESTION** - Dúvida, pergunta sobre serviços
- **REVIEW_REMINDER** - Cliente perguntando sobre revisão
- **APPOINTMENT** - Agendamento de serviço
- **OTHER** - Outros

Responda APENAS com a categoria em maiúsculas.
"""),
    ("human", "Mensagem: {message}")
])


def _classify_message_type(message: str) -> str:
    """Classifica o tipo de mensagem usando LLM."""
    try:
        chain = _classify_prompt | _llm
        result = chain.invoke({"message": message})
        classification = result.content.strip().upper()
        
        valid_types = ["SATISFACTION", "COMPLAINT", "SUGGESTION", "COMPLIMENT", 
                      "QUESTION", "REVIEW_REMINDER", "APPOINTMENT", "OTHER"]
        
        if classification in valid_types:
            return classification
        
        return "OTHER"
        
    except Exception as e:
        logger.error(f"❌ [CRM] Erro na classificação: {str(e)}")
        return "OTHER"


# ========================================
# Geração de Respostas Automáticas
# ========================================

_response_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é um assistente de CRM para a oficina GoMech.

Gere uma resposta PROFISSIONAL, AMIGÁVEL e PERSONALIZADA para o cliente.

**DIRETRIZES:**
- Seja cordial e empático
- Use linguagem clara e acessível
- Seja breve (máx 3-4 linhas)
- Inclua call-to-action quando apropriado
- Não use emojis em excesso
- Se for reclamação, demonstre empatia e ofereça solução

**CONTEXTO DO CLIENTE:**
{client_context}

**TIPO DE MENSAGEM:** {message_type}
**SENTIMENTO:** {sentiment}
**É URGENTE:** {is_urgent}
"""),
    ("human", "Mensagem do cliente: {message}")
])


def _generate_auto_response(message: str, message_type: str, sentiment: str, 
                           is_urgent: bool, client_name: Optional[str] = None) -> str:
    """
    Gera resposta automática personalizada.
    """
    try:
        client_context = f"Nome: {client_name}" if client_name else "Cliente não identificado"
        
        chain = _response_prompt | _llm
        result = chain.invoke({
            "message": message,
            "message_type": message_type,
            "sentiment": sentiment,
            "is_urgent": "Sim" if is_urgent else "Não",
            "client_context": client_context
        })
        
        return result.content.strip()
        
    except Exception as e:
        logger.error(f"❌ [CRM] Erro ao gerar resposta: {str(e)}")
        return "Olá! Recebemos sua mensagem e vamos retornar em breve. Obrigado pelo contato!"


# ========================================
# Lembretes de Revisão
# ========================================

def _generate_review_reminder(client_name: str, vehicle_model: str, 
                             last_service_km: int, current_km: int) -> str:
    """
    Gera mensagem de lembrete de revisão.
    """
    km_since_service = current_km - last_service_km
    
    return f"""
Olá, {client_name}! 😊

Notamos que seu {vehicle_model} já rodou {km_since_service} km desde a última revisão.

🔧 Que tal agendar uma revisão preventiva? Cuidar do seu veículo evita problemas maiores e garante sua segurança!

📅 Podemos agendar um horário para você?

Responda SIM para agendar ou ligue (11) 1234-5678.

Equipe GoMech
""".strip()


def _generate_satisfaction_survey(client_name: str, service_order_number: str) -> str:
    """
    Gera mensagem de pesquisa de satisfação.
    """
    return f"""
Olá, {client_name}! 

Agradecemos pela confiança em nossos serviços! 🙏

Gostaríamos de saber: como foi sua experiência com o serviço #{service_order_number}?

📊 De 0 a 10, quanto você nos recomendaria?

Sua opinião é muito importante para nós!

Equipe GoMech
""".strip()


# ========================================
# Função Principal
# ========================================

def run_crm_agent(message: str, client_name: Optional[str] = None, 
                 action: str = "analyze") -> Dict[str, Any]:
    """
    Agente CRM com análise de sentimento e geração de respostas.
    
    Args:
        message: Mensagem do cliente
        client_name: Nome do cliente (opcional)
        action: Ação a realizar:
            - "analyze" - Analisar mensagem
            - "respond" - Gerar resposta automática
            - "review_reminder" - Gerar lembrete de revisão
            - "satisfaction_survey" - Gerar pesquisa de satisfação
    
    Returns:
        Dict com análise, classificação, resposta sugerida, etc.
    """
    logger.info(f"💬 [CRM Agent] Ação: {action} - Mensagem: {message[:50]}...")
    
    try:
        # Análise de sentimento
        sentiment_analysis = _analyze_sentiment_simple(message)
        sentiment = sentiment_analysis["sentiment"]
        sentiment_score = sentiment_analysis["score"]
        
        # Detectar urgência
        is_urgent = _is_urgent(message)
        
        # Classificar tipo
        message_type = _classify_message_type(message)
        
        result = {
            "sentiment": sentiment,
            "sentiment_score": sentiment_score,
            "message_type": message_type,
            "is_urgent": is_urgent,
            "analysis": f"Sentimento: {sentiment} ({sentiment_score:.2f}), Tipo: {message_type}"
        }
        
        # Gerar resposta se solicitado
        if action in ["respond", "analyze"]:
            auto_response = _generate_auto_response(
                message, 
                message_type, 
                sentiment, 
                is_urgent, 
                client_name
            )
            result["suggested_response"] = auto_response
        
        # Adicionar recomendações
        recommendations = []
        if is_urgent:
            recommendations.append("⚠️ URGENTE - Responder imediatamente")
        if sentiment == "NEGATIVE":
            recommendations.append("😞 Cliente insatisfeito - Priorizar atendimento")
        if message_type == "COMPLAINT":
            recommendations.append("📢 Reclamação - Encaminhar para gerente")
        if sentiment == "POSITIVE":
            recommendations.append("✅ Cliente satisfeito - Agradecer e pedir avaliação")
        
        result["recommendations"] = recommendations
        
        logger.info(f"✅ [CRM Agent] Análise concluída: {sentiment} - {message_type}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [CRM Agent] Erro: {str(e)}", exc_info=True)
        return {
            "sentiment": "NEUTRAL",
            "sentiment_score": 0.5,
            "message_type": "OTHER",
            "is_urgent": False,
            "error": str(e)
        }


def generate_review_reminder(client_name: str, vehicle_model: str, 
                            last_service_km: int, current_km: int) -> str:
    """Wrapper para gerar lembrete de revisão."""
    return _generate_review_reminder(client_name, vehicle_model, last_service_km, current_km)


def generate_satisfaction_survey(client_name: str, service_order_number: str) -> str:
    """Wrapper para gerar pesquisa de satisfação."""
    return _generate_satisfaction_survey(client_name, service_order_number)

