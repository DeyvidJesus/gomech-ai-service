import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict

from dotenv import load_dotenv
from openai import BaseModel
from sqlalchemy.orm import Session
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from schemas import ChatRequest
from models import Conversation, Message


load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Modelo de Chat ---
model = init_chat_model("gpt-4o-mini", model_provider="openai", api_key=OPENAI_API_KEY)

# --- Thread Pool Executor para não bloquear o loop ---
executor = ThreadPoolExecutor(max_workers=4)

# --- Locks para evitar race conditions por thread_id ---
conversation_locks: Dict[str, asyncio.Lock] = {}


def get_lock_for_thread(thread_id: str) -> asyncio.Lock:
    lock = conversation_locks.get(thread_id)
    if not lock:
        lock = asyncio.Lock()
        conversation_locks[thread_id] = lock
    return lock


# --- Função de chamada síncrona do modelo ---
def call_model_sync(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}


# --- Grafo LangGraph ---
chat_graph = StateGraph(state_schema=MessagesState)
chat_graph.add_node("model", call_model_sync)
chat_graph.add_edge(START, "model")  # ← ESSENCIAL: START aponta para o nó inicial
checkpointer = MemorySaver()
app_graph = chat_graph.compile(checkpointer=checkpointer)


# --- Função principal de chat ---
async def call_chat(req: ChatRequest, db: Session):
    # --- Criar nova conversa caso não exista ---
    thread_id = req.thread_id
    user_message = req.message

    if not thread_id:
        from uuid import uuid4
        thread_id = str(uuid4())
        conversation = Conversation(thread_id=thread_id)
        db.add(conversation)
        try:
            db.commit()
            db.refresh(conversation)
        except Exception as e:
            db.rollback()
            logging.exception("Erro ao criar conversa: %s", e)
            raise
    else:
        conversation = db.query(Conversation).filter_by(thread_id=thread_id).first()
        if not conversation:
            raise ValueError("thread_id inválido")

    lock = get_lock_for_thread(thread_id)
    async with lock:
        # --- Reconstruir histórico ---
        db.refresh(conversation)
        messages = []
        for msg in sorted(conversation.messages, key=lambda m: m.id):
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        messages.append(HumanMessage(content=user_message))

        # --- Invocar modelo no executor para não bloquear ---
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

        # --- Persistir no banco ---
        try:
            db.add(Message(conversation_id=conversation.id, role="user", content=user_message))
            db.add(Message(conversation_id=conversation.id, role="ai", content=reply_message))
            db.commit()
        except Exception as e:
            db.rollback()
            logging.exception("Erro ao salvar mensagens: %s", e)
            raise

    return {"reply": reply_message, "thread_id": thread_id}
