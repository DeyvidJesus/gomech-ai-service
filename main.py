import os
import uuid
import asyncio
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from models import Base, Conversation, Message

# --- LangChain / LangGraph ---
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.checkpoint.memory import MemorySaver

# --- Configuração ---
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurado")
if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY não encontrado")

# --- Banco de dados ---
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Cria tabelas (somente para DEV — em produção usar Alembic)
Base.metadata.create_all(bind=engine)

# --- FastAPI ---
app = FastAPI(title="Chatbot Service Async (revisado)")

# --- Modelo de chat ---
model = init_chat_model("gpt-4o-mini", model_provider="openai")

def call_model_sync(state: MessagesState):
    response = model.invoke(state["messages"])
    return {"messages": response}

workflow = StateGraph(state_schema=MessagesState)
workflow.add_edge(START, "model")
workflow.add_node("model", call_model_sync)
app_graph = workflow.compile(checkpointer=MemorySaver())

executor = ThreadPoolExecutor(max_workers=4)

# --- Schemas ---
class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    reply: str
    thread_id: str

# --- Dependency DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Locks para evitar race conditions ---
conversation_locks: dict[str, asyncio.Lock] = {}

def get_lock_for_thread(thread_id: str) -> asyncio.Lock:
    lock = conversation_locks.get(thread_id)
    if not lock:
        lock = asyncio.Lock()
        conversation_locks[thread_id] = lock
    return lock

# --- Endpoint principal ---
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    # Criar nova conversa
    if not req.thread_id:
        req.thread_id = str(uuid.uuid4())
        conversation = Conversation(thread_id=req.thread_id)
        db.add(conversation)
        try:
            db.commit()
            db.refresh(conversation)
        except SQLAlchemyError as e:
            db.rollback()
            logging.exception("Erro ao criar conversa: %s", e)
            raise HTTPException(status_code=500, detail="Erro ao criar conversa")
    else:
        conversation = db.query(Conversation).filter_by(thread_id=req.thread_id).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="thread_id inválido")

    lock = get_lock_for_thread(req.thread_id)
    async with lock:
        # Reconstituir histórico
        db.refresh(conversation)
        messages = []
        for msg in sorted(conversation.messages, key=lambda m: m.id):
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            else:
                messages.append(AIMessage(content=msg.content))
        messages.append(HumanMessage(content=req.message))

        # Invocar modelo no executor (não bloquear loop)
        loop = asyncio.get_running_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    lambda: app_graph.invoke(
                        {"messages": messages},
                        config={"configurable": {"thread_id": req.thread_id}}
                    )
                ),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Tempo esgotado ao consultar modelo")
        except Exception as e:
            logging.exception("Erro ao invocar modelo: %s", e)
            raise HTTPException(status_code=500, detail="Erro interno no modelo")

        try:
            reply_message = result["messages"][-1].content
        except Exception:
            logging.exception("Formato inesperado da resposta: %s", result)
            raise HTTPException(status_code=500, detail="Resposta inesperada do modelo")

        # Persistir no banco
        try:
            db.add(Message(conversation_id=conversation.id, role="user", content=req.message))
            db.add(Message(conversation_id=conversation.id, role="ai", content=reply_message))
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logging.exception("Erro ao salvar mensagens: %s", e)
            raise HTTPException(status_code=500, detail="Erro ao salvar mensagens")

    return ChatResponse(reply=reply_message, thread_id=req.thread_id)
