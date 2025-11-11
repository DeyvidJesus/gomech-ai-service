import os
import logging
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from agents.sql_agent import run_sql_agent, get_operational_stats
from agents.chat_agent import call_chat
from agents.chart_agent import run_chart_agent
from agents.web_agent import run_web_agent
from agents.audit_agent import run_audit_agent
from agents.recommendation_agent import run_recommendation_agent
from agents.action_agent import run_action_agent

# FASE 10: Novos agentes
from agents.voice_agent import run_voice_agent, text_to_speech_openai, process_voice_command
from agents.vision_agent import run_vision_agent, detect_damage_level, suggest_replacement_part, extract_part_code_ocr
from agents.predictive_agent import run_predictive_agent, predict_order_delay, predict_bottlenecks, generate_proactive_alerts
from agents.simulation_agent import run_simulation_agent, simulate_price_change, simulate_capacity_change, compare_scenarios

from router_agent import route_question, route_multimodal_input
from schemas import ChatResponse, ChatRequest, PendingAction, ActionConfirmation
from models import User

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
    connect_args={"connect_timeout": 180, "application_name": "gomech-ai-service"}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# ==============================
# Configuração do FastAPI
# ==============================
app = FastAPI(title="Chatbot Service Async")

# ==============================
# Configuração de CORS
# ==============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        # Log do contexto se fornecido
        if req.context:
            logging.info(f"📍 [Context] Rota do frontend: {req.context}")
        
        # Roteamento inteligente com contexto
        route = route_question(req.message, req.context)
        logging.info(f"🎯 [Router] Pergunta: '{req.message[:50]}...' → Rota: {route.upper()}")
        
        if route == "sql":
            answer = run_sql_agent(req.message)
            return {"reply": answer, "thread_id": req.thread_id or "unknown"}
            
        elif route == "grafico":
            result = run_chart_agent(req.message)
            return {
                "reply": result.get("reply", "Aqui está a visualização que você pediu! 📊"),
                "thread_id": req.thread_id or "unknown",
                "image_base64": result.get("chart_base64"),
                "image_mime": result.get("chart_mime"),
            }
            
        elif route == "web":
            result = run_web_agent(req.message)
            return {
                "reply": result.get("reply", "Encontrei alguns vídeos que podem te ajudar! 🎥"),
                "thread_id": req.thread_id or "unknown",
                "videos": result.get("videos", [])
            }
        
        elif route == "audit":
            # Buscar email do usuário para consultas personalizadas
            user_email = None
            if req.user_id:
                try:
                    user = db.query(User).filter_by(id=req.user_id).first()
                    if user:
                        user_email = user.email
                except Exception as e:
                    logging.warning(f"⚠️ [Audit] Não foi possível obter email do usuário: {e}")
            
            answer = run_audit_agent(req.message, user_email=user_email)
            return {"reply": answer, "thread_id": req.thread_id or "unknown"}
        
        elif route == "recommendation":
            # Obter estatísticas operacionais para enriquecer recomendações
            stats = get_operational_stats()
            answer = run_recommendation_agent(req.message, stats)
            return {"reply": answer, "thread_id": req.thread_id or "unknown"}
        
        elif route == "action":
            # Processar comando de ação
            action_result = run_action_agent(req.message)
            
            if not action_result.get("is_command"):
                # Não é um comando, encaminhar para chat
                return await call_chat(req, db)
            
            response = {
                "reply": action_result.get("reply", "Comando processado"),
                "thread_id": req.thread_id or "unknown"
            }
            
            # Se há ação pendente de confirmação, incluir no response
            if action_result.get("pending_confirmation"):
                pending_action = PendingAction(
                    action=action_result["action"],
                    action_description=action_result["action_description"],
                    params=action_result["params"],
                    endpoint=action_result["endpoint"],
                    method=action_result["method"],
                    confirmation_message=action_result["confirmation_message"]
                )
                response["pending_action"] = pending_action
            
            return response
            
        else:  # chat
            return await call_chat(req, db)
            
    except TimeoutError as e:
        logging.error(f"⏱️ [Timeout] {str(e)}")
        raise HTTPException(
            status_code=408,
            detail="⏱️ A consulta está demorando muito. Por favor, tente novamente ou simplifique sua pergunta."
        )
    except ValueError as e:
        logging.error(f"❌ [ValueError] {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"❌ Dados inválidos: {str(e)}"
        )
    except SQLAlchemyError as e:
        logging.error(f"🗄️ [Database Error] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="🗄️ Ops! Tivemos um problema ao acessar o banco de dados. Tente novamente em alguns instantes."
        )
    except Exception as e:
        logging.exception(f"💥 [Unexpected Error] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"😕 Ops! Algo inesperado aconteceu. Nossa equipe foi notificada. Por favor, tente novamente."
        )


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
                        AND table_name IN (
                            'organizations', 'users', 'clients', 'vehicles', 
                            'service_orders', 'service_order_items', 'parts', 
                            'inventory_items', 'inventory_movements', 
                            'conversations', 'messages'
                        )
                        ORDER BY table_name
                    """)).fetchall()

                    table_names = [row[0] for row in tables_check]
                    
                    # Contagens básicas
                    stats = {}
                    if 'organizations' in table_names:
                        stats['organizations'] = db_test.execute(text("SELECT COUNT(*) FROM organizations")).fetchone()[0]
                    if 'users' in table_names:
                        stats['users'] = db_test.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
                    if 'clients' in table_names:
                        stats['clients'] = db_test.execute(text("SELECT COUNT(*) FROM clients")).fetchone()[0]
                    if 'vehicles' in table_names:
                        stats['vehicles'] = db_test.execute(text("SELECT COUNT(*) FROM vehicles")).fetchone()[0]
                    if 'service_orders' in table_names:
                        stats['service_orders'] = db_test.execute(text("SELECT COUNT(*) FROM service_orders")).fetchone()[0]
                    if 'parts' in table_names:
                        stats['parts'] = db_test.execute(text("SELECT COUNT(*) FROM parts")).fetchone()[0]
                    if 'inventory_items' in table_names:
                        stats['inventory_items'] = db_test.execute(text("SELECT COUNT(*) FROM inventory_items")).fetchone()[0]
                    if 'conversations' in table_names:
                        stats['conversations'] = db_test.execute(text("SELECT COUNT(*) FROM conversations")).fetchone()[0]

                    status_info["components"]["database"] = {
                        "status": "healthy",
                        "message": "Conexão com PostgreSQL estabelecida",
                        "version": db_info.get("version", "Unknown")[:50] + "..." if db_info.get("version") else "Unknown",
                        "active_connections": db_info.get("active_connections", 0),
                        "tables_available": table_names,
                        "record_counts": stats,
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
            from agents.web_agent import run_web_agent

            status_info["components"]["ai_agents"] = {
                "status": "healthy",
                "message": "Agentes de IA carregados com sucesso",
                "available_agents": ["sql_agent", "chat_agent", "chart_agent", "web_agent"],
                "routing": {
                    "sql": "Consultas ao banco de dados (clientes, veículos, ordens, inventário)",
                    "chat": "Conversação geral e explicações",
                    "grafico": "Visualização de dados com gráficos",
                    "web": "Busca de vídeos no YouTube sobre mecânica"
                }
            }
        except Exception as e:
            status_info["components"]["ai_agents"] = {
                "status": "error",
                "message": f"Erro ao carregar agentes: {str(e)}"
            }
            status_info["status"] = "degraded"

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


@app.get("/insights")
async def get_insights():
    """
    Endpoint dedicado para obter insights operacionais.
    
    Retorna análises, estatísticas e recomendações baseadas em dados reais.
    Ideal para dashboards e painéis analíticos.
    """
    try:
        # Obter estatísticas operacionais
        stats = get_operational_stats()
        
        if 'error' in stats:
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao obter estatísticas: {stats['error']}"
            )
        
        # Gerar análise e recomendações
        from agents.recommendation_agent import _analyze_operational_data, _generate_predictions
        
        analysis = _analyze_operational_data(stats)
        predictions = _generate_predictions(stats)
        
        return {
            "status": "success",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": stats,
            "analysis": analysis,
            "predictions": predictions,
            "insights_summary": {
                "os_today": stats.get('os_today', {}),
                "monthly_performance": {
                    "avg_ticket": stats.get('monthly_ticket', {}).get('avg_ticket', 0),
                    "total_revenue": stats.get('monthly_ticket', {}).get('total_revenue', 0),
                    "os_count": stats.get('monthly_ticket', {}).get('count', 0)
                },
                "recurrence": {
                    "clients": stats.get('recurrent_clients', {}).get('count', 0),
                    "orders": stats.get('recurrent_clients', {}).get('total_orders', 0)
                },
                "top_parts": stats.get('top_parts', [])[:3]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.exception(f"💥 [Insights Error] {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar insights: {str(e)}"
        )


# ==============================
# FASE 9: Endpoints de Gestão Estratégica
# ==============================

@app.post("/management/profitability")
async def analyze_profitability(data: dict):
    """
    Análise de rentabilidade por serviço.
    
    Body esperado:
    {
        "service_orders": [...],
        "question": "Me mostre os serviços com maior margem"
    }
    """
    try:
        from agents.recommendation_agent import calculate_service_profitability
        
        service_orders = data.get("service_orders", [])
        result = calculate_service_profitability(service_orders)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logging.exception(f"💥 [Profitability Analysis] Erro: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao analisar rentabilidade: {str(e)}"
        )


@app.post("/management/bottlenecks")
async def analyze_bottlenecks(data: dict):
    """
    Identificação de gargalos operacionais.
    
    Body esperado:
    {
        "service_orders": [...],
        "technicians": [...],
        "inventory": [...]
    }
    """
    try:
        from agents.recommendation_agent import identify_operational_bottlenecks
        
        result = identify_operational_bottlenecks(data)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logging.exception(f"💥 [Bottleneck Analysis] Erro: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao identificar gargalos: {str(e)}"
        )


@app.post("/management/benchmark")
async def perform_benchmark(data: dict):
    """
    Benchmark interno entre oficinas.
    
    Body esperado:
    {
        "organizations": [
            {
                "organization_id": 1,
                "organization_name": "Oficina A",
                "monthly_revenue": 50000,
                "avg_ticket": 500,
                ...
            },
            ...
        ]
    }
    """
    try:
        from agents.recommendation_agent import internal_benchmark
        
        organizations = data.get("organizations", [])
        result = internal_benchmark(organizations)
        
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logging.exception(f"💥 [Benchmark Analysis] Erro: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao realizar benchmark: {str(e)}"
        )


@app.post("/management/report")
async def generate_management_report(data: dict):
    """
    Gera relatórios gerenciais em diferentes formatos.
    
    Body esperado:
    {
        "report_type": "executive|profitability|bottlenecks|benchmark",
        "format": "json|csv|text",
        "service_orders": [...],
        "organizations": [...],
        "technicians": [...],
        "inventory": [...]
    }
    """
    try:
        from agents.recommendation_agent import generate_management_report
        
        report_type = data.get("report_type", "executive")
        format_type = data.get("format", "json")
        
        # Preparar dados
        report_data = {
            "service_orders": data.get("service_orders", []),
            "organizations": data.get("organizations", []),
            "technicians": data.get("technicians", []),
            "inventory": data.get("inventory", [])
        }
        
        result = generate_management_report(report_type, report_data, format_type)
        
        return {
            "status": "success",
            "report_type": report_type,
            "format": format_type,
            "data": result
        }
    except Exception as e:
        logging.exception(f"💥 [Report Generation] Erro: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


@app.post("/action/confirm")
async def confirm_action(confirmation: ActionConfirmation):
    """
    Executa uma ação confirmada pelo usuário.
    
    Faz chamada HTTP ao backend Java para executar a ação.
    """
    try:
        import requests
        
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8080")
        endpoint = confirmation.endpoint
        method = confirmation.method
        params = confirmation.params
        
        # Substituir placeholders no endpoint (ex: {id})
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in endpoint:
                endpoint = endpoint.replace(placeholder, str(value))
                # Remover parâmetro já usado no path
                del params[key]
                break
        
        url = f"{backend_url}{endpoint}"
        logging.info(f"🚀 [Action Execution] {method} {url} - Params: {params}")
        
        if method == "POST":
            response = requests.post(url, json=params, timeout=180)
        elif method == "PUT":
            response = requests.put(url, json=params, timeout=180)
        elif method == "PATCH":
            response = requests.patch(url, json=params, timeout=180)
        elif method == "DELETE":
            response = requests.delete(url, timeout=180)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Método HTTP não suportado: {method}"
            )
        
        # Verificar resultado
        if response.status_code in [200, 201, 204]:
            logging.info(f"✅ [Action Execution] Sucesso: {response.status_code}")
            
            result_data = {}
            if response.text:
                try:
                    result_data = response.json()
                except:
                    result_data = {"response": response.text}
            
            return {
                "status": "success",
                "message": "Ação executada com sucesso! ✅",
                "result": result_data
            }
        else:
            logging.error(f"❌ [Action Execution] Erro: {response.status_code} - {response.text}")
            return {
                "status": "error",
                "message": f"Erro ao executar ação: {response.status_code}",
                "error": response.text
            }
            
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=408,
            detail="Tempo esgotado ao executar ação no backend"
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao backend"
        )
    except Exception as e:
        logging.exception(f"💥 [Action Execution] Erro: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar ação: {str(e)}"
        )


# ========================================
# FASE 10: ENDPOINTS MULTIMODAIS
# ========================================

@app.post("/voice/transcribe")
async def transcribe_audio(data: dict):
    """
    Transcreve áudio para texto usando Whisper ou Google Speech.
    
    Body: {
        "audio_base64": "...",
        "engine": "whisper" | "google",
        "language": "pt" | "en" | "es" | "fr" | "de"
    }
    """
    try:
        audio_base64 = data.get("audio_base64")
        engine = data.get("engine", "whisper")
        language = data.get("language", "pt")
        
        if not audio_base64:
            raise HTTPException(status_code=400, detail="audio_base64 é obrigatório")
        
        result = run_voice_agent(audio_base64, engine, language)
        
        logging.info(f"🎤 [Voice API] Transcrição concluída: {result.get('status')}")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Voice API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/synthesize")
async def synthesize_speech(data: dict):
    """
    Converte texto em áudio usando OpenAI TTS.
    
    Body: {
        "text": "...",
        "voice": "alloy" | "echo" | "fable" | "onyx" | "nova" | "shimmer"
    }
    """
    try:
        text = data.get("text")
        voice = data.get("voice", "nova")
        
        if not text:
            raise HTTPException(status_code=400, detail="text é obrigatório")
        
        result = text_to_speech_openai(text, voice)
        
        logging.info(f"🔊 [TTS API] Síntese concluída: {result.get('status')}")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [TTS API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/command")
async def process_voice_full(data: dict):
    """
    Processa comando por voz completo (STT + processamento + TTS opcional).
    
    Body: {
        "audio_base64": "...",
        "tts_enabled": true | false
    }
    """
    try:
        audio_base64 = data.get("audio_base64")
        tts_enabled = data.get("tts_enabled", False)
        
        if not audio_base64:
            raise HTTPException(status_code=400, detail="audio_base64 é obrigatório")
        
        result = process_voice_command(audio_base64, tts_enabled)
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Voice Command API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vision/analyze")
async def analyze_image(data: dict):
    """
    Analisa imagem de peça automotiva.
    
    Body: {
        "image_base64": "...",
        "part_context": "..." (opcional)
    }
    """
    try:
        image_base64 = data.get("image_base64")
        part_context = data.get("part_context")
        
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 é obrigatório")
        
        context = {"part_context": part_context} if part_context else None
        result = run_vision_agent("analyze", image_base64, context)
        
        logging.info(f"👁️ [Vision API] Análise concluída: {result.get('status')}")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Vision API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vision/detect-damage")
async def detect_damage(data: dict):
    """
    Detecta nível de dano em peça.
    
    Body: {
        "image_base64": "..."
    }
    """
    try:
        image_base64 = data.get("image_base64")
        
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 é obrigatório")
        
        result = detect_damage_level(image_base64)
        
        logging.info(f"🔍 [Damage Detection API] Nível: {result.get('damage_level')}")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Damage Detection API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vision/suggest-part")
async def suggest_part(data: dict):
    """
    Sugere peça de substituição.
    
    Body: {
        "identified_part": "...",
        "vehicle_info": {
            "make": "...",
            "model": "...",
            "year": 2020
        }
    }
    """
    try:
        identified_part = data.get("identified_part")
        vehicle_info = data.get("vehicle_info")
        
        if not identified_part:
            raise HTTPException(status_code=400, detail="identified_part é obrigatório")
        
        result = suggest_replacement_part(identified_part, vehicle_info)
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Part Suggestion API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vision/extract-code")
async def extract_code(data: dict):
    """
    Extrai códigos de peça da imagem usando OCR.
    
    Body: {
        "image_base64": "..."
    }
    """
    try:
        image_base64 = data.get("image_base64")
        
        if not image_base64:
            raise HTTPException(status_code=400, detail="image_base64 é obrigatório")
        
        result = extract_part_code_ocr(image_base64)
        
        logging.info(f"🔍 [OCR API] {result.get('codes_found', 0)} código(s) extraído(s)")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [OCR API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predictive/order-delay")
async def predict_delay(data: dict):
    """
    Prevê se uma OS tem risco de atraso.
    
    Body: {
        "order_data": {
            "id": 123,
            "service_type": "...",
            "technician_active_orders": 5,
            "parts_available": true,
            "estimated_hours": 4,
            "days_open": 2
        }
    }
    """
    try:
        order_data = data.get("order_data")
        
        if not order_data:
            raise HTTPException(status_code=400, detail="order_data é obrigatório")
        
        result = predict_order_delay(order_data)
        
        if result.get('status') == 'success':
            pred = result['prediction']
            logging.info(f"🔮 [Predictive API] OS {order_data.get('id')}: Risco {pred['risk_level']} ({pred['risk_score']}%)")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Predictive API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predictive/bottlenecks")
async def predict_bottlenecks_endpoint(data: dict):
    """
    Prevê gargalos operacionais futuros.
    
    Body: {
        "operational_data": {
            "open_orders": 25,
            "active_technicians": 5,
            "daily_completion_rate": 8,
            "daily_new_orders": 10,
            "low_stock_count": 3
        },
        "forecast_days": 7
    }
    """
    try:
        operational_data = data.get("operational_data")
        forecast_days = data.get("forecast_days", 7)
        
        if not operational_data:
            raise HTTPException(status_code=400, detail="operational_data é obrigatório")
        
        result = predict_bottlenecks(operational_data, forecast_days)
        
        if result.get('status') == 'success':
            forecast = result['forecast']
            logging.info(f"📊 [Bottlenecks API] Projeção {forecast_days} dias: {forecast['summary']['risk_level']}")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Bottlenecks API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predictive/alerts")
async def get_proactive_alerts(data: dict):
    """
    Gera alertas proativos baseados no estado atual.
    
    Body: {
        "current_state": {
            "orders_near_deadline": [...],
            "low_stock_items": [...],
            "capacity_usage_percent": 85,
            "overloaded_technicians": [...]
        }
    }
    """
    try:
        current_state = data.get("current_state")
        
        if not current_state:
            raise HTTPException(status_code=400, detail="current_state é obrigatório")
        
        alerts = generate_proactive_alerts(current_state)
        
        logging.info(f"🔔 [Alerts API] {len(alerts)} alerta(s) gerado(s)")
        
        return {
            "status": "success",
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except Exception as e:
        logging.exception(f"💥 [Alerts API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulation/price-change")
async def simulate_price(data: dict):
    """
    Simula impacto de mudança de preço.
    
    Body: {
        "current_data": {
            "monthly_revenue": 50000,
            "monthly_orders": 100,
            "avg_ticket": 500,
            "profit_margin_percent": 40
        },
        "price_change_percent": 5
    }
    """
    try:
        current_data = data.get("current_data")
        price_change_percent = data.get("price_change_percent")
        
        if not current_data or price_change_percent is None:
            raise HTTPException(status_code=400, detail="current_data e price_change_percent são obrigatórios")
        
        result = simulate_price_change(current_data, price_change_percent)
        
        if result.get('status') == 'success':
            proj = result['projection']
            logging.info(f"💰 [Simulation API] Preço {price_change_percent:+.1f}%: Receita {proj['revenue_change']:+.2f}")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Simulation API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulation/capacity-change")
async def simulate_capacity(data: dict):
    """
    Simula impacto de adicionar/remover técnicos.
    
    Body: {
        "current_data": {
            "technician_count": 5,
            "monthly_orders": 100,
            "avg_ticket": 500,
            "monthly_revenue": 50000,
            "tech_cost_monthly": 3500
        },
        "additional_technicians": 2
    }
    """
    try:
        current_data = data.get("current_data")
        additional_technicians = data.get("additional_technicians")
        
        if not current_data or additional_technicians is None:
            raise HTTPException(status_code=400, detail="current_data e additional_technicians são obrigatórios")
        
        result = simulate_capacity_change(current_data, additional_technicians)
        
        if result.get('status') == 'success':
            proj = result['projection']
            logging.info(f"👷 [Simulation API] Capacidade {additional_technicians:+d} técnicos: ROI {proj['roi_percent']:+.1f}%")
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Simulation API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulation/what-if")
async def what_if_analysis(data: dict):
    """
    Análise "E se..." usando IA.
    
    Body: {
        "query": "E se eu aumentar o preço em 10%?",
        "current_data": {
            "monthly_revenue": 50000,
            "monthly_orders": 100,
            ...
        }
    }
    """
    try:
        query = data.get("query")
        current_data = data.get("current_data")
        
        if not query or not current_data:
            raise HTTPException(status_code=400, detail="query e current_data são obrigatórios")
        
        result = run_simulation_agent(query, current_data)
        
        logging.info(f"🎲 [What-if API] Query: {query[:50]}...")
        
        return {
            "status": "success",
            "query": query,
            "analysis": result
        }
        
    except Exception as e:
        logging.exception(f"💥 [What-if API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulation/compare")
async def compare_scenarios_endpoint(data: dict):
    """
    Compara múltiplos cenários.
    
    Body: {
        "scenarios": [
            { resultado de simulação 1 },
            { resultado de simulação 2 },
            ...
        ]
    }
    """
    try:
        scenarios = data.get("scenarios")
        
        if not scenarios or not isinstance(scenarios, list):
            raise HTTPException(status_code=400, detail="scenarios (array) é obrigatório")
        
        result = compare_scenarios(scenarios)
        
        return result
        
    except Exception as e:
        logging.exception(f"💥 [Compare API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/multimodal/chat")
async def multimodal_chat(data: dict):
    """
    Endpoint multimodal: aceita texto, voz e imagem simultaneamente.
    
    Body: {
        "text": "..." (opcional),
        "audio_base64": "..." (opcional),
        "image_base64": "..." (opcional),
        "context": "/service-orders",
        "tts_enabled": false
    }
    """
    try:
        # Preparar dados de entrada
        input_data = {
            "text": data.get("text"),
            "audio_base64": data.get("audio_base64"),
            "image_base64": data.get("image_base64"),
            "metadata": data.get("metadata", {})
        }
        
        context = data.get("context")
        tts_enabled = data.get("tts_enabled", False)
        
        # Rotear entrada multimodal
        routing = route_multimodal_input(input_data, context)
        
        logging.info(f"🎭 [Multimodal] Modalidade: {routing['is_multimodal']}, Route: {routing['route']}")
        
        results = {}
        transcription_text = None
        
        # Processar ações em sequência de prioridade
        for action in routing["actions"]:
            agent = action["agent"]
            action_type = action["action"]
            
            # 1. Transcrever áudio (se presente)
            if agent == "voice" and action_type == "transcribe":
                voice_result = run_voice_agent(input_data["audio_base64"])
                if voice_result.get("status") == "success":
                    transcription_text = voice_result.get("transcription")
                    results["transcription"] = transcription_text
                    # Usar transcrição como texto se não houver texto
                    if not input_data["text"]:
                        input_data["text"] = transcription_text
            
            # 2. Analisar imagem (se presente)
            elif agent == "vision":
                vision_result = run_vision_agent(action_type, input_data["image_base64"], {"part_context": input_data.get("text")})
                results["vision_analysis"] = vision_result
            
            # 3. Processar texto/comando
            elif agent in ["chat", "sql", "recommendation", "predictive", "simulation"]:
                # Usar o texto (original ou transcrito)
                query_text = input_data["text"]
                
                if agent == "chat":
                    text_result = call_chat(query_text, context)
                elif agent == "sql":
                    text_result = run_sql_agent(query_text)
                elif agent == "recommendation":
                    text_result = run_recommendation_agent(query_text)
                elif agent == "predictive":
                    text_result = run_predictive_agent("predict_delay", {"order_data": {}})  # Placeholder
                elif agent == "simulation":
                    text_result = run_simulation_agent(query_text, {})  # Placeholder
                
                results["reply"] = text_result
        
        # 4. Converter resposta em áudio (se habilitado)
        if tts_enabled and results.get("reply"):
            tts_result = text_to_speech_openai(results["reply"])
            if tts_result.get("status") == "success":
                results["audio_response"] = tts_result.get("audio_base64")
                results["audio_mime"] = tts_result.get("audio_mime")
        
        # Montar resposta final
        return {
            "status": "success",
            "routing": routing,
            "results": results,
            "message": "Processamento multimodal concluído!"
        }
        
    except Exception as e:
        logging.exception(f"💥 [Multimodal API] Erro: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
