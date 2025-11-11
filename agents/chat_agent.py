import asyncio
import logging
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List
from uuid import uuid4
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from schemas import ChatRequest
from models import Conversation, Message, User

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Carregar Base de Conhecimento de UI ---
UI_KNOWLEDGE_PATH = Path(__file__).parent.parent / "data" / "docs" / "ui_descriptions.json"

def _load_ui_knowledge() -> Dict:
    """Carrega base de conhecimento de UI."""
    try:
        if UI_KNOWLEDGE_PATH.exists():
            with open(UI_KNOWLEDGE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Falha ao carregar UI knowledge: {e}")
    return {"routes": {}, "common_flows": {}, "glossary": {}}

UI_KNOWLEDGE = _load_ui_knowledge()

# --- Mapeamento de Rotas da Aplicação ---
ROUTE_MAPPING = {
    "/": "página inicial",
    "/dashboard": """
**Dashboard** - Visão geral do negócio
- Métricas principais (KPIs)
- Resumo de ordens de serviço
- Faturamento do período
- Gráficos de desempenho
- Alertas e notificações importantes
""",
    "/service-orders": """
**Ordens de Serviço** - Controle de OS
- Criar nova ordem de serviço
- Listar ordens (abertas, em andamento, concluídas)
- Filtrar por status, cliente, veículo, técnico
- Visualizar detalhes e histórico
- Imprimir ordens
- Adicionar peças e serviços
""",
    "/inventory": """
**Estoque/Inventário** - Gestão de Peças
- Visualizar itens em estoque
- Movimentações (entrada/saída)
- Alertas de estoque mínimo
- Histórico de movimentação
- Reserva de peças para OS
- Relatórios de giro de estoque
""",
    "/clients": """
**Clientes** - Gestão de Clientes
- Cadastrar novo cliente
- Listar e buscar clientes
- Editar informações
- Visualizar histórico de serviços
- Ver veículos do cliente
- Exportar dados
""",
    "/vehicles": """
**Veículos** - Cadastro e Histórico
- Cadastrar novo veículo
- Vincular a cliente
- Histórico de manutenções
- Quilometragem atual
- Detalhes técnicos (marca, modelo, ano)
- Revisões programadas
""",
    "/parts": """
**Peças** - Catálogo de Peças
- Cadastrar nova peça
- Gerenciar catálogo
- Definir preços e custos
- Markup e margem
- SKU e código de barras
- Fornecedores
""",
    "/users": """
**Usuários** - Gestão de Equipe
- Cadastrar usuários
- Definir permissões e cargos
- Gerenciar acesso
- Visualizar atividades
""",
    "/analytics": """
**Análises** - Relatórios e Estatísticas
- Relatórios financeiros
- Desempenho de técnicos
- Análise de vendas
- Gráficos personalizados
- Exportar relatórios
""",
}

# --- Mini-Glossário de Termos do Sistema ---
GLOSSARY = {
    "OS": "Ordem de Serviço - Documento que registra um serviço a ser executado em um veículo",
    "ordem de serviço": "Documento que registra um serviço a ser executado em um veículo, incluindo descrição do problema, diagnóstico, peças utilizadas e custos",
    "markup": "Percentual adicionado ao custo de uma peça para definir o preço de venda. Exemplo: custo R$100 + markup 50% = preço R$150",
    "revisão programada": "Manutenção preventiva agendada com base na quilometragem ou tempo desde a última revisão",
    "NPS": "Net Promoter Score - Métrica de satisfação do cliente (escala de 0 a 10)",
    "margem": "Diferença entre o preço de venda e o custo, geralmente expressa em percentual",
    "giro de estoque": "Frequência com que o estoque é renovado em um período (quantas vezes foi vendido e reposto)",
    "SKU": "Stock Keeping Unit - Código único para identificar cada produto/peça no sistema",
    "inventário": "Conjunto de todas as peças e produtos em estoque na oficina",
    "estoque mínimo": "Quantidade mínima que deve ser mantida em estoque antes de fazer nova compra",
    "movimentação": "Entrada ou saída de peças do estoque (compra, venda, transferência, ajuste)",
    "KPI": "Key Performance Indicator - Indicadores chave de desempenho do negócio",
    "LGPD": "Lei Geral de Proteção de Dados - Legislação brasileira sobre privacidade e proteção de dados pessoais",
    "auditoria": "Registro de todas as alterações feitas no sistema, incluindo quem fez, quando e o que foi modificado",
    "multi-tenancy": "Arquitetura que permite múltiplas oficinas (organizações) usarem o mesmo sistema de forma isolada",
}

# --- System Prompt com Personalidade ---
SYSTEM_PROMPT = """Você é o assistente virtual do GoMech, um sistema inteligente de gestão para oficinas mecânicas. 

🎯 **SUA PERSONALIDADE:**
- Seja amigável, prestativo e profissional
- Use linguagem clara e acessível
- Seja proativo em oferecer ajuda
- Mantenha o contexto da conversa
- Use emojis ocasionalmente para ser mais amigável 😊
- Trate o usuário de forma respeitosa (você)

🔧 **SUAS CAPACIDADES:**
1. **Consultar dados do sistema** - clientes, veículos, ordens de serviço, estoque, peças
2. **Gerar gráficos e visualizações** - estatísticas e relatórios visuais
3. **Buscar vídeos tutoriais** - conteúdo educativo sobre mecânica
4. **Explicar funcionalidades** - como usar o sistema e suas páginas
5. **Dar suporte** - tirar dúvidas e orientar sobre processos

📚 **GLOSSÁRIO DE TERMOS:**
Você conhece estes termos do sistema GoMech:
- **OS/Ordem de Serviço**: Documento de registro de serviço
- **Markup**: Percentual adicionado ao custo para formar o preço
- **Revisão Programada**: Manutenção preventiva agendada
- **Giro de Estoque**: Frequência de renovação do estoque
- **SKU**: Código único de produto
- **KPI**: Indicador chave de desempenho
- **LGPD**: Lei de proteção de dados
- **Multi-tenancy**: Múltiplas oficinas no mesmo sistema

Se o usuário perguntar sobre algum termo, explique de forma clara e didática.

💡 **DICAS PARA SUAS RESPOSTAS:**
- Se o usuário perguntar sobre dados, sugira que pode buscar informações específicas
- Se houver dúvidas sobre funcionalidades, explique baseado no contexto da página atual
- Ofereça exemplos práticos quando explicar conceitos
- Mantenha respostas concisas mas completas
- Se não souber algo, seja honesto e sugira alternativas
- Lembre-se do contexto anterior da conversa e da página em que o usuário está

🗺️ **CONHECIMENTO DAS PÁGINAS:**
Você conhece todas as páginas do sistema e pode orientar o usuário sobre:
- O que cada página faz
- Como usar suas funcionalidades
- Onde encontrar informações específicas
- Dicas e melhores práticas

🚀 **EXEMPLOS DE INTERAÇÃO:**
- "Olá! Sou o assistente do GoMech. Como posso ajudar você hoje?"
- "Claro! Deixa eu buscar essas informações para você..."
- "Vejo que você está na página de [X]. Posso te ajudar a [Y]."
- "Posso te mostrar um gráfico para facilitar a visualização. Quer que eu crie?"
- "Sobre [termo]: é [explicação clara e simples]"

Seja sempre útil, empático e focado em resolver o problema do usuário! 🎉
"""

# --- Modelo de Chat ---
model = init_chat_model("gpt-4o-mini", model_provider="openai", api_key=OPENAI_API_KEY, temperature=0.7)

# --- Executor para chamadas síncronas ---
executor = ThreadPoolExecutor(max_workers=4)

# --- Locks para evitar race conditions ---
conversation_locks: Dict[str, asyncio.Lock] = {}


def get_lock_for_thread(thread_id: str) -> asyncio.Lock:
    if thread_id not in conversation_locks:
        conversation_locks[thread_id] = asyncio.Lock()
    return conversation_locks[thread_id]


# --- Função síncrona para chamar o modelo ---
def call_model_sync(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}


# --- Grafo LangGraph ---
chat_graph = StateGraph(state_schema=MessagesState)
chat_graph.add_node("model", call_model_sync)
chat_graph.add_edge(START, "model")
checkpointer = MemorySaver()
app_graph = chat_graph.compile(checkpointer=checkpointer)


# --- Funções auxiliares de contexto ---
def _get_route_context(context: Optional[str]) -> str:
    """Extrai informações sobre a rota atual para enriquecer o contexto."""
    if not context:
        return ""
    
    # Normalizar rota (remover IDs e query params)
    normalized = re.sub(r'/\d+', '', context).split('?')[0]
    
    # Primeiro tentar buscar na base de conhecimento detalhada
    route_info = UI_KNOWLEDGE.get("routes", {}).get(normalized)
    if route_info:
        context_text = f"\n\n📍 **Página Atual: {route_info['name']}**"
        context_text += f"\n{route_info['description_full']}"
        context_text += f"\n\n**Principais campos:** {', '.join(route_info['main_fields'][:5])}"
        context_text += f"\n\n**Ações possíveis:** {', '.join(route_info['possible_actions'][:5])}"
        return context_text
    
    # Fallback para mapeamento simples
    for route, description in ROUTE_MAPPING.items():
        if normalized.startswith(route) and route != "/":
            return f"\n\n📍 **Página Atual:** {description}"
    
    return ""


def _check_glossary_terms(message: str) -> str:
    """Verifica se a mensagem contém termos do glossário e retorna definições relevantes."""
    message_lower = message.lower()
    found_terms = []
    
    # Buscar no glossário local
    for term, definition in GLOSSARY.items():
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        if re.search(pattern, message_lower):
            found_terms.append(f"- **{term.title()}**: {definition}")
    
    # Buscar no glossário da base de conhecimento
    ui_glossary = UI_KNOWLEDGE.get("glossary", {})
    for term, definition in ui_glossary.items():
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        if re.search(pattern, message_lower) and term.lower() not in [t.lower() for t in GLOSSARY.keys()]:
            found_terms.append(f"- **{term}**: {definition}")
    
    if found_terms:
        return "\n\n📚 **Termos Relevantes:**\n" + "\n".join(found_terms[:5])  # Limitar a 5 termos
    
    return ""


def _detect_step_by_step_request(message: str, context: Optional[str]) -> Optional[Dict]:
    """
    Detecta se o usuário está pedindo um guia passo a passo.
    
    Retorna dict com steps se detectado, senão None.
    """
    message_lower = message.lower()
    
    # Palavras-chave que indicam pedido de tutorial
    tutorial_keywords = [
        "passo a passo", "passo-a-passo", "tutorial", 
        "como fazer", "como faço", "como criar", "como cadastrar",
        "ensine", "me guie", "me ajude a", "guia",
        "não sei como", "primeiro passo"
    ]
    
    is_tutorial_request = any(keyword in message_lower for keyword in tutorial_keywords)
    
    if not is_tutorial_request:
        return None
    
    # Normalizar contexto
    if context:
        normalized_context = re.sub(r'/\d+', '', context).split('?')[0]
        route_info = UI_KNOWLEDGE.get("routes", {}).get(normalized_context)
        
        if route_info:
            # Identificar qual tipo de guia
            if "criar" in message_lower or "novo" in message_lower or "cadastr" in message_lower:
                if "step_by_step_create" in route_info:
                    return {
                        "type": "step_by_step",
                        "title": f"📖 Guia: Como criar em {route_info['name']}",
                        "steps": route_info["step_by_step_create"]
                    }
            elif "entrada" in message_lower and "estoque" in message_lower:
                if "step_by_step_entry" in route_info:
                    return {
                        "type": "step_by_step",
                        "title": f"📖 Guia: Entrada de Estoque",
                        "steps": route_info["step_by_step_entry"]
                    }
            elif "relatório" in message_lower or "relatorio" in message_lower:
                if "step_by_step_report" in route_info:
                    return {
                        "type": "step_by_step",
                        "title": f"📖 Guia: Gerar Relatório",
                        "steps": route_info["step_by_step_report"]
                    }
    
    # Verificar se é um fluxo comum
    common_flows = UI_KNOWLEDGE.get("common_flows", {})
    if "atendimento" in message_lower or "completo" in message_lower:
        flow = common_flows.get("complete_service")
        if flow:
            return {
                "type": "step_by_step",
                "title": f"📖 {flow['name']}",
                "steps": flow["steps"]
            }
    elif "estoque" in message_lower and ("gestão" in message_lower or "gerenciar" in message_lower):
        flow = common_flows.get("stock_management")
        if flow:
            return {
                "type": "step_by_step",
                "title": f"📖 {flow['name']}",
                "steps": flow["steps"]
            }
    
    return None


# --- Função principal de chat ---
async def call_chat(req: ChatRequest, db: Session):
    thread_id = req.thread_id
    user_message = req.message
    user_id = req.user_id

    # Criar conversa se não existir thread_id
    if not thread_id:
        thread_id = str(uuid4())
    conversation = db.query(Conversation).filter_by(thread_id=thread_id).first()
    if not conversation:
        if not user_id:
            raise ValueError("user_id não pode ser nulo")
        conversation = Conversation(thread_id=thread_id, user_id=user_id)
        db.add(conversation)
        try:
            db.commit()
            db.refresh(conversation)
        except Exception as e:
            db.rollback()
            logging.exception("Erro ao criar conversa: %s", e)
            raise

    lock = get_lock_for_thread(thread_id)
    async with lock:
        # --- Detectar se é pedido de guia passo a passo ---
        step_guide = _detect_step_by_step_request(user_message, req.context)
        if step_guide:
            # Retornar guia diretamente
            steps_text = "\n".join(step_guide["steps"])
            reply = f"{step_guide['title']}\n\n{steps_text}\n\n💡 **Dica:** Siga estes passos em ordem. Se tiver dúvidas em algum passo específico, é só me perguntar!"
            
            # Salvar no histórico
            try:
                db.add(Message(conversation_id=conversation.id, role="user", content=user_message))
                db.add(Message(conversation_id=conversation.id, role="ai", content=reply))
                db.commit()
            except Exception as e:
                db.rollback()
                logging.exception("Erro ao salvar mensagens de guia: %s", e)
            
            return {
                "reply": reply,
                "thread_id": thread_id,
                "guide_mode": True,
                "steps": step_guide["steps"]
            }
        
        # --- Buscar informações do usuário para personalização ---
        user = db.query(User).filter_by(id=user_id).first()
        user_context = ""
        if user:
            user_context = f"\n\n👤 **Contexto do Usuário:**\n- Nome: {user.name}\n- Email: {user.email}\n- Cargo: {user.role}\n"
            if user.organization:
                user_context += f"- Organização: {user.organization.name}\n"
        
        # --- Enriquecer com contexto da rota ---
        route_context = _get_route_context(req.context)
        
        # --- Verificar termos do glossário ---
        glossary_context = _check_glossary_terms(user_message)
        
        # --- Reconstruir histórico com System Prompt enriquecido ---
        db.refresh(conversation)
        enriched_prompt = SYSTEM_PROMPT + user_context + route_context + glossary_context
        messages = [SystemMessage(content=enriched_prompt)]
        
        for msg in sorted(conversation.messages, key=lambda m: m.id):
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        messages.append(HumanMessage(content=user_message))

        # --- Invocar modelo ---
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    lambda: app_graph.invoke(
                        {"messages": messages},
                        config={"configurable": {"thread_id": thread_id}}
                    )
                ),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            raise TimeoutError("Tempo esgotado ao consultar modelo")
        except Exception as e:
            logging.exception("Erro ao invocar modelo: %s", e)
            raise

        try:
            reply_message = result["messages"][-1].content
        except Exception:
            logging.exception("Formato inesperado da resposta: %s", result)
            raise RuntimeError("Resposta inesperada do modelo")

        # --- Persistir mensagens no banco ---
        try:
            db.add(Message(conversation_id=conversation.id, role="user", content=user_message))
            db.add(Message(conversation_id=conversation.id, role="ai", content=reply_message))
            db.commit()
        except Exception as e:
            db.rollback()
            logging.exception("Erro ao salvar mensagens: %s", e)
            raise

    return {"reply": reply_message, "thread_id": thread_id}
