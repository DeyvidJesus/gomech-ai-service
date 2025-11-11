import os
import re
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

_router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

# FASE 10: Suporte a entrada multimodal
MULTIMODAL_SUPPORTED = True

# Mapeamento de contextos (rotas) para informações adicionais
CONTEXT_MAPPING = {
    "/dashboard": "visão geral do negócio, métricas gerais, KPIs",
    "/service-orders": "ordens de serviço, controle de OS, manutenções",
    "/inventory": "estoque, movimentação de peças, inventário",
    "/clients": "gestão de clientes, cadastro de clientes",
    "/vehicles": "histórico de veículos, cadastro de veículos",
    "/parts": "catálogo de peças, gerenciamento de peças",
    "/users": "usuários do sistema, equipe",
    "/analytics": "análises, relatórios, estatísticas",
}

def _extract_context_hint(context: Optional[str]) -> str:
    """Extrai dica de contexto baseado na rota."""
    if not context:
        return ""
    
    # Normalizar rota (remover IDs e query params)
    normalized = re.sub(r'/\d+', '', context).split('?')[0]
    
    for route, hint in CONTEXT_MAPPING.items():
        if normalized.startswith(route):
            return f"\n**Contexto da página:** {route} - {hint}"
    
    return f"\n**Contexto da página:** {context}"

_router_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é um roteador inteligente de mensagens do sistema GoMech.
Analise a pergunta do usuário, o contexto da página (se fornecido) e decida qual agente deve responder.

🗄️ **SQL** → Consultas ao banco de dados
   Palavras-chave: quantos, mostre, liste, busque, encontre, qual, quais, total, contagem, dados, relatório
   Dados: clientes, usuários, veículos, ordens de serviço, peças, estoque, inventário
   Exemplos:
   - "Quantos clientes temos?"
   - "Mostre os veículos da marca Honda"
   - "Liste as ordens de serviço pendentes"
   - "Qual o estoque da peça X?"
   - "Busque o cliente com CPF 123"
   - "Total de custos das OSs este mês"
   - "Dados dos últimos 10 clientes"
   - "Relatório de vendas"

💬 **CHAT** → Conversação e explicações
   Palavras-chave: como, por que, o que é, onde, explique, ajude, oi, olá, obrigado, funciona
   Contexto: saudações, dúvidas conceituais, agradecimentos, tutoriais do sistema
   Exemplos:
   - "Olá!" / "Oi" / "Bom dia"
   - "Como funciona o sistema?"
   - "O que é uma ordem de serviço?"
   - "Onde encontro os relatórios?"
   - "Pode me ajudar?"
   - "Obrigado!" / "Valeu!"
   - "Como adiciono um cliente?"
   - "Explique o que é markup"

📊 **GRAFICO** → Visualizações e gráficos
   Palavras-chave: gráfico, visualize, mostre gráfico, chart, dashboard, plotar, comparar visualmente
   Contexto: pedidos explícitos de visualização gráfica
   Exemplos:
   - "Mostre um gráfico de vendas"
   - "Crie um gráfico de veículos por marca"
   - "Visualize o estoque em gráfico"
   - "Quero ver um dashboard"
   - "Compare as vendas em gráfico"
   - "Plotar evolução de OSs"

🌐 **WEB** → Busca de vídeos e tutoriais
   Palavras-chave: vídeo, tutorial externo, aprenda, como fazer, ensine, YouTube, assista
   Contexto: busca de conteúdo educativo externo sobre mecânica
   Exemplos:
   - "Mostre vídeos sobre troca de óleo"
   - "Tutorial de alinhamento"
   - "Como fazer balanceamento"
   - "Aprenda a trocar pastilha de freio"
   - "Vídeo sobre suspensão"
   - "Assista tutorial sobre injeção eletrônica"

🔍 **AUDIT** → Segurança, LGPD e auditoria
   Palavras-chave: segurança, LGPD, auditoria, logs, histórico de alterações, quem modificou
   Contexto: questões de compliance, rastreabilidade, segurança de dados
   Exemplos:
   - "Quem alterou este cliente?"
   - "Histórico de modificações da OS 123"
   - "Logs de acesso ao sistema"
   - "Conformidade LGPD"
   - "Auditoria de alterações"

💡 **RECOMMENDATION** → Insights e recomendações
   Palavras-chave: melhorar, insight, prever, recomendar, sugerir, otimizar, o que fazer
   Contexto: sugestões inteligentes, análise preditiva, otimizações
   Exemplos:
   - "Como melhorar o estoque?"
   - "Insights sobre vendas"
   - "O que devo fazer para aumentar a receita?"
   - "Preveja a demanda de peças"
   - "Recomende ações para reduzir custos"
   - "Sugira otimizações no processo"

⚡ **ACTION** → Comandos e ações diretas
   Palavras-chave: criar, adicionar, cadastrar, atualizar, marcar, mudar status, incluir, registrar
   Contexto: comandos que exigem ação no sistema (criar OS, atualizar status, etc)
   Exemplos:
   - "Crie uma OS para o cliente João"
   - "Marque a OS 123 como concluída"
   - "Adicione 10 unidades da peça X ao estoque"
   - "Cadastre a peça Filtro de óleo"
   - "Inclua a peça na OS 45"
   - "Atualizar status da OS 78 para em andamento"
   - "Registre entrada de estoque"

⚠️ **REGRAS DE DECISÃO:**
1. **PRIORIDADE MÁXIMA**: Se for um COMANDO de ação (criar, adicionar, atualizar, marcar, cadastrar, registrar) → ACTION
2. Se mencionar dados específicos (nomes, números, contagens, listagens) → SQL
3. Se pedir gráfico, visualização ou comparação visual explicitamente → GRAFICO
4. Se pedir vídeo/tutorial externo explicitamente → WEB
5. Se for saudação, agradecimento ou dúvida conceitual/tutorial → CHAT
6. Se mencionar segurança, LGPD, auditoria, logs → AUDIT
7. Se pedir melhorias, insights, previsões, recomendações → RECOMMENDATION
8. Use o contexto da página para desambiguar (ex: se está em /clients e pergunta "quantos?", provavelmente quer contar clientes)
9. Em caso de dúvida entre SQL e CHAT → prefira SQL se houver qualquer menção a dados concretos
10. Em caso de dúvida entre SQL e GRAFICO → prefira GRAFICO apenas se explicitamente pedir visualização
11. **IMPORTANTE**: Comandos de ação têm PRIORIDADE sobre consultas (ex: "Crie uma OS" é ACTION, não SQL)

Responda APENAS com: "sql", "chat", "grafico", "web", "audit", "recommendation" ou "action"
"""),
    ("human", "{context_hint}{question}")
])

def route_question(question: str, context: Optional[str] = None) -> str:
    """
    Roteia a pergunta para o agente apropriado.
    
    Args:
        question: Pergunta do usuário
        context: Contexto da rota atual (pathname do frontend)
        
    Returns:
        Nome do agente: "sql", "chat", "grafico", "web", "audit" ou "recommendation"
    """
    # Adicionar hint de contexto se fornecido
    context_hint = _extract_context_hint(context)
    
    # Invocar LLM para roteamento
    chain = _router_prompt | _router_llm
    result = chain.invoke({
        "question": question,
        "context_hint": context_hint
    })
    
    route = result.content.strip().lower()
    
    # Validar resposta (fallback para chat se inválido)
    valid_routes = ["sql", "chat", "grafico", "web", "audit", "recommendation", "action", "voice", "vision", "predictive", "simulation"]
    if route not in valid_routes:
        return "chat"

    return route


# ========================================
# FASE 10: ROTEAMENTO MULTIMODAL
# ========================================

def route_multimodal_input(input_data: Dict[str, Any], context: Optional[str] = None) -> Dict[str, Any]:
    """
    Roteia entrada multimodal (texto + imagem + voz).
    
    Args:
        input_data: Dict com campos opcionais:
            - text: Mensagem de texto (str)
            - image_base64: Imagem em base64 (str)
            - audio_base64: Áudio em base64 (str)
            - metadata: Metadados adicionais (Dict)
        context: Contexto da rota atual
    
    Returns:
        Dict com roteamento e ações a executar:
            - route: Agente principal
            - actions: Lista de ações (ex: [transcribe_audio, analyze_image, process_text])
            - priority: Ordem de execução
    """
    text = input_data.get('text')
    has_image = input_data.get('image_base64') is not None
    has_audio = input_data.get('audio_base64') is not None
    
    actions = []
    route = "chat"  # Rota padrão
    
    # 1. Processar áudio (se presente)
    if has_audio:
        actions.append({
            "type": "voice",
            "action": "transcribe",
            "priority": 1,
            "agent": "voice"
        })
    
    # 2. Processar imagem (se presente)
    if has_image:
        # Detectar se é análise de peça ou outro uso
        if text and any(word in text.lower() for word in ['peça', 'peca', 'danificado', 'quebrado', 'analise', 'foto']):
            actions.append({
                "type": "vision",
                "action": "analyze_part",
                "priority": 2,
                "agent": "vision"
            })
            route = "vision"
        else:
            actions.append({
                "type": "vision",
                "action": "general_analysis",
                "priority": 2,
                "agent": "vision"
            })
    
    # 3. Processar texto
    if text or (has_audio and not text):  # Se tem áudio sem texto, aguardar transcrição
        # Detectar tipo de consulta
        if text:
            text_lower = text.lower()
            
            # Comandos especiais da Fase 10
            if "e se" in text_lower or "what if" in text_lower or "simul" in text_lower:
                actions.append({
                    "type": "simulation",
                    "action": "what_if_analysis",
                    "priority": 3,
                    "agent": "simulation"
                })
                route = "simulation"
            
            elif any(word in text_lower for word in ['prever', 'atraso', 'gargalo', 'risco', 'predi']):
                actions.append({
                    "type": "predictive",
                    "action": "predict",
                    "priority": 3,
                    "agent": "predictive"
                })
                route = "predictive"
            
            else:
                # Roteamento padrão
                route = route_question(text, context)
                actions.append({
                    "type": "text",
                    "action": "process_query",
                    "priority": 3,
                    "agent": route
                })
    
    # Ordenar ações por prioridade
    actions.sort(key=lambda x: x['priority'])
    
    return {
        "route": route,
        "actions": actions,
        "is_multimodal": len(actions) > 1,
        "has_audio": has_audio,
        "has_image": has_image,
        "has_text": text is not None
    }


def detect_input_modality(input_data: Dict[str, Any]) -> str:
    """
    Detecta a modalidade principal da entrada.
    
    Returns:
        "text", "voice", "image", "multimodal"
    """
    has_text = input_data.get('text') is not None
    has_image = input_data.get('image_base64') is not None
    has_audio = input_data.get('audio_base64') is not None
    
    modality_count = sum([has_text, has_image, has_audio])
    
    if modality_count > 1:
        return "multimodal"
    elif has_audio:
        return "voice"
    elif has_image:
        return "image"
    else:
        return "text"


def should_use_tts(context: Optional[str] = None, user_preferences: Optional[Dict] = None) -> bool:
    """
    Determina se a resposta deve ser convertida em áudio (Text-to-Speech).
    
    Args:
        context: Contexto da requisição
        user_preferences: Preferências do usuário
    
    Returns:
        True se deve usar TTS, False caso contrário
    """
    # Por padrão, não usar TTS
    if not user_preferences:
        return False
    
    # Verificar preferência do usuário
    tts_enabled = user_preferences.get('tts_enabled', False)
    
    # Verificar se está em modo mãos-livres
    hands_free_mode = user_preferences.get('hands_free_mode', False)
    
    return tts_enabled or hands_free_mode