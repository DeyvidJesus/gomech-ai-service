import os
import logging
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from agents.sql_agent import run_sql_agent
from models import Base
from agents.chat_agent import call_chat
from agents.chart_agent import run_chart_agent

from router_agent import route_question
from schemas import ChatResponse, ChatRequest

load_dotenv()

# ==============================
# Configuração do banco de dados
# ==============================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL precisa estar configurada no .env")

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    future=True,
    connect_args={"connect_timeout": 30, "application_name": "gomech-ai-service"}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# ==============================
# Configuração do FastAPI
# ==============================
app = FastAPI(title="Chatbot Service Async")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================
# Endpoints
# ==============================
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


@app.get("/status")
async def get_service_status():
    try:
        status_info = {
            "service": "Gomech AI Service",
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "endpoints": ["/chat", "/status"],
            "components": {}
        }

        # Verifica conexão com banco
        try:
            from utils.database import test_database_connection, get_database_info

            if test_database_connection(engine):
                db_info = get_database_info(engine)
                db_test = SessionLocal()
                try:
                    tables_check = db_test.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('clients', 'conversations', 'messages')
                    """)).fetchall()

                    table_names = [row[0] for row in tables_check]
                    client_count = 0
                    conversation_count = 0
                    if 'clients' in table_names:
                        client_count = db_test.execute(text("SELECT COUNT(*) FROM clients")).fetchone()[0]
                    if 'conversations' in table_names:
                        conversation_count = db_test.execute(text("SELECT COUNT(*) FROM conversations")).fetchone()[0]

                    status_info["components"]["database"] = {
                        "status": "healthy",
                        "message": "Conexão com PostgreSQL estabelecida",
                        "version": db_info.get("version", "Unknown")[:50] + "..." if db_info.get("version") else "Unknown",
                        "active_connections": db_info.get("active_connections", 0),
                        "tables_available": table_names,
                        "client_count": client_count,
                        "conversation_count": conversation_count,
                        "db_host": DB_HOST,
                        "db_name": DB_NAME
                    }
                finally:
                    db_test.close()
            else:
                raise Exception("Falha no teste de conexão")

        except Exception as e:
            status_info["components"]["database"] = {
                "status": "error",
                "message": f"Erro na conexão com banco: {str(e)}",
                "tables_accessible": False,
                "error_type": type(e).__name__
            }
            status_info["status"] = "degraded"

        # Verifica agentes de IA
        try:
            from agents.sql_agent import run_sql_agent
            from agents.chat_agent import call_chat
            from agents.chart_agent import run_chart_agent

            status_info["components"]["ai_agents"] = {
                "status": "healthy",
                "message": "Agentes de IA carregados com sucesso",
                "available_agents": ["sql_agent", "chat_agent", "chart_agent"]
            }
        except Exception as e:
            status_info["components"]["ai_agents"] = {
                "status": "error",
                "message": f"Erro ao carregar agentes: {str(e)}"
            }
            status_info["status"] = "degraded"

        # Variáveis de ambiente críticas
        env_status = {}
        required_vars = ["DB_USER", "DB_PASS", "DB_HOST", "DB_PORT", "DB_NAME"]
        optional_vars = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]

        for var in required_vars:
            env_status[var] = "configured" if os.getenv(var) else "missing"
            if not os.getenv(var):
                status_info["status"] = "degraded"

        for var in optional_vars:
            env_status[var] = "configured" if os.getenv(var) else "not_configured"

        status_info["components"]["environment"] = {
            "status": "healthy" if all(os.getenv(var) for var in required_vars) else "warning",
            "variables": env_status
        }

        return status_info

    except Exception as e:
        logging.exception("Erro ao obter status: %s", e)
        return {
            "service": "Gomech AI Service",
            "status": "error",
            "message": f"Erro interno: {str(e)}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }


@app.get("/")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "service": "Gomech AI Service",
        "message": "Serviço funcionando normalmente"
    }
