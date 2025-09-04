from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag_engine import ask_question, ask_simple_question
import matplotlib.pyplot as plt
import io
import base64

app = FastAPI(title="GoMech AI Service", version="2.0")

class QueryRequest(BaseModel):
    question: str
    chart: bool = False
    ai_type: str = "standard"  # "standard" ou "enhanced"

class HealthResponse(BaseModel):
    status: str
    message: str
    ai_types_available: list

@app.get("/")
def health_check():
    """Endpoint de health check"""
    return HealthResponse(
        status="healthy",
        message="GoMech AI Service está funcionando",
        ai_types_available=["standard", "enhanced"]
    )

@app.post("/ask")
def ask(req: QueryRequest):
    """Endpoint principal para perguntas de IA"""
    try:
        # Determina qual tipo de IA usar
        if req.ai_type == "enhanced":
            answer = ask_question(req.question)  # RAG com LangChain
        else:
            answer = ask_simple_question(req.question)  # IA padrão mais simples
        
        chart_base64 = None
        
        # Gera gráfico se solicitado
        if req.chart:
            chart_base64 = generate_chart(req.question, answer)
        
        return {
            "answer": answer,
            "chart": chart_base64,
            "ai_type": req.ai_type,
            "question": req.question
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar pergunta: {str(e)}")

@app.post("/ask/standard")
def ask_standard(req: QueryRequest):
    """Endpoint específico para IA padrão"""
    try:
        answer = ask_simple_question(req.question)
        chart_base64 = None
        
        if req.chart:
            chart_base64 = generate_chart(req.question, answer)
        
        return {
            "answer": answer,
            "chart": chart_base64,
            "ai_type": "standard",
            "question": req.question
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na IA padrão: {str(e)}")

@app.post("/ask/enhanced")
def ask_enhanced(req: QueryRequest):
    """Endpoint específico para IA aprimorada com RAG"""
    try:
        answer = ask_question(req.question)  # RAG com LangChain
        chart_base64 = None
        
        if req.chart:
            chart_base64 = generate_chart(req.question, answer)
        
        return {
            "answer": answer,
            "chart": chart_base64,
            "ai_type": "enhanced",
            "question": req.question
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na IA aprimorada: {str(e)}")

def generate_chart(question: str, answer: str):
    """Gera gráfico baseado na pergunta e resposta"""
    try:
        plt.figure(figsize=(10, 6))
        
        # TODO: Implementar lógica mais inteligente para gráficos
        # Por enquanto, gráfico exemplo
        if "vendas" in question.lower() or "receita" in question.lower():
            # Gráfico de vendas exemplo
            months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
            values = [15000, 18000, 22000, 19000, 25000, 28000]
            plt.plot(months, values, marker='o', linewidth=2, markersize=8)
            plt.title(f"Análise: {question}")
            plt.ylabel("Valores (R$)")
            plt.grid(True, alpha=0.3)
        elif "clientes" in question.lower():
            # Gráfico de clientes exemplo
            categories = ["Novos", "Recorrentes", "Inativos"]
            values = [30, 45, 25]
            plt.pie(values, labels=categories, autopct='%1.1f%%')
            plt.title(f"Distribuição: {question}")
        else:
            # Gráfico de barras genérico
            categories = ["Categoria A", "Categoria B", "Categoria C", "Categoria D"]
            values = [20, 35, 30, 15]
            plt.bar(categories, values, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
            plt.title(f"Análise: {question}")
            plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Converte para base64
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close()
        
        return chart_base64
        
    except Exception as e:
        print(f"Erro ao gerar gráfico: {e}")
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5060) 
