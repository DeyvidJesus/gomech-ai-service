from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rag_engine import ask_question
import matplotlib.pyplot as plt
import io, base64

app = FastAPI(title="GoMech AI Service", version="1.0")


class QueryRequest(BaseModel):
    question: str
    chart: bool = False


@app.post("/ask")
def ask(req: QueryRequest):
    try:
        answer = ask_question(req.question)

        chart_base64 = None
        if req.chart:
            plt.figure()
            plt.bar(["Exemplo A", "Exemplo B"], [10, 20])  # TODO: Remover
            plt.title(req.question)
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            chart_base64 = base64.b64encode(buf.read()).decode("utf-8")

        return {"answer": answer, "chart": chart_base64}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
