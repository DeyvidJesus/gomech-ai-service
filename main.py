import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from agents.sql_agent import run_sql_agent
from models import Base
from agents.chat_agent import call_chat
from agents.chart_agent import run_chart_agent

from pydantic import BaseModel

from router_agent import route_question
from schemas import ChatResponse, ChatRequest

# --- Configuração ---
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurado")

# --- Banco de dados ---
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Cria tabelas (somente para DEV — em produção usar Alembic)
Base.metadata.create_all(bind=engine)

# --- FastAPI ---
app = FastAPI(title="Chatbot Service Async")

# --- Dependency DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Endpoint principal ---
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    try:
        route = route_question(req.message)
        if route == "sql":
            answer = run_sql_agent(req.message)
            return {"reply": answer, "thread_id": req.thread_id or "unknown"}
        elif route == "grafico":
            result = run_chart_agent(req.message)
            return {
                "reply": result.get("reply", ""),
                "thread_id": req.thread_id or "unknown",
                "image_base64": result.get("chart_base64"),
                "image_mime": result.get("chart_mime"),
            }
        else:
            return await call_chat(req, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except SQLAlchemyError as e:
        logging.exception("Erro no banco: %s", e)
        raise HTTPException(status_code=500, detail="Erro no banco de dados")
    except Exception as e:
        logging.exception("Erro interno: %s", e)
        raise HTTPException(status_code=500, detail="Erro interno")

    return ChatResponse(reply=result["reply"], thread_id=result["thread_id"])
