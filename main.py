import os
import logging
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from agents.sql_agent import run_sql_agent
from models import Base
from agents.chat_agent import call_chat
from agents.chart_agent import run_chart_agent

from router_agent import route_question
from schemas import ChatResponse, ChatRequest

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não configurado")

# Configurações de conexão mais robustas para produção
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    client_encoding="utf-8",
    future=True, 
    pool_pre_ping=True,
    pool_recycle=3600,  # Recicla conexões a cada hora
    pool_size=5,        # Máximo 5 conexões no pool
    max_overflow=10,    # Máximo 10 conexões extras
    connect_args={
        "connect_timeout": 30,
        "application_name": "gomech-ai-service"
    }
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Em produção, as tabelas são criadas via Alembic migrations
# Base.metadata.create_all(bind=engine)  # Removido para produção

app = FastAPI(title="Chatbot Service Async")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        
        # Verifica conexão com banco de dados
        try:
            from utils.database import test_database_connection, get_database_info
            
            # Testa conexão básica
            if test_database_connection(engine):
                db_info = get_database_info(engine)
                
                # Testa acesso às tabelas específicas
                db_test = SessionLocal()
                try:
                    # Verifica se as tabelas existem
                    tables_check = db_test.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name IN ('clients', 'conversations', 'messages')
                    """)).fetchall()
                    
                    table_names = [row[0] for row in tables_check]
                    
                    # Conta registros se as tabelas existem
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
                        "conversation_count": conversation_count
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
        
        env_status = {}
        required_vars = ["DATABASE_URL"]
        optional_vars = ["OPENAI_API_KEY", "LANGSMITH_API_KEY"]
        
        for var in required_vars:
            if os.getenv(var):
                env_status[var] = "configured"
            else:
                env_status[var] = "missing"
                status_info["status"] = "degraded"
        
        for var in optional_vars:
            if os.getenv(var):
                env_status[var] = "configured"
            else:
                env_status[var] = "not_configured"
        
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

# --- Health Check simples ---
@app.get("/")
async def health_check():
    """Health check básico"""
    return {
        "status": "healthy",
        "service": "Gomech AI Service",
        "message": "Serviço funcionando normalmente"
    }

# --- Inicialização do servidor ---
if __name__ == "__main__":
    import uvicorn
    
    # Configurações do servidor (usa PORT do .env)
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    
    logging.info(f"Iniciando Gomech AI Service em {HOST}:{PORT} (env: {ENVIRONMENT})")
    
    # Configurações diferentes para dev e prod
    reload_enabled = ENVIRONMENT == "development"
    
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=reload_enabled,
        log_level="info"
    )