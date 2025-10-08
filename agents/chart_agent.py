import os
import io
import re
import base64
from functools import lru_cache
from typing import Optional, List, Literal, Dict, Any

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pandas.api.types import is_numeric_dtype, is_datetime64_any_dtype

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

class ChartPlan(BaseModel):
    chart_type: Literal[
        "line",
        "bar",
        "scatter",
        "pie",
        "histogram",
        "stacked_bar",
        "boxplot",
        "heatmap",
    ] = Field(
        description="Tipo de gráfico a ser gerado"
    )
    title: Optional[str] = Field(
        default=None, description="Título do gráfico"
    )
    x: Optional[str] = Field(
        default=None, description="Coluna para o eixo X"
    )
    y: Optional[str] = Field(
        default=None, description="Coluna para o eixo Y (quando aplicável)"
    )
    hue: Optional[str] = Field(
        default=None, description="Coluna para agrupamento/cor (opcional)"
    )
    sql: Optional[str] = Field(
        default=None, description="Consulta SQL para obter os dados"
    )
    data: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Dados inline em formato de linhas (lista de objetos)"
    )
    explanation: Optional[str] = Field(
        default=None, description="Breve explicação do que foi plotado"
    )


_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

_planner_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
Você é um planejador de visualizações. Dado o pedido do usuário e (se disponível) um resumo do esquema do banco,
retorne um plano ESTRUTURADO em JSON para gerar um gráfico. Siga as regras:
- Escolha chart_type entre: line, bar, scatter, pie, histogram, stacked_bar, boxplot, heatmap
- Defina title, x, y e hue (quando fizer sentido). Para histogram, y pode ser nulo e x deve ser a coluna numérica a ser distribuída
- Se a visualização depender do banco, gere a consulta SQL em sql (SELECT ...). Evite operações destrutivas
- Se o usuário fornecer dados inline (ex.: colunas e linhas no texto), preencha data como uma lista de objetos
- Retorne APENAS o JSON com as chaves do modelo ChartPlan, sem texto adicional
""".strip(),
    ),
    ("human", "Pedido do usuário: {question}\n\nEsquema (opcional):\n{db_schema}")
])


@lru_cache(maxsize=1)
def _get_db_schema_summary() -> str:
    """Retorna um resumo do esquema do banco com cache para melhorar performance."""
    if not DATABASE_URL:
        return ""
    try:
        from langchain_community.utilities import SQLDatabase
        db = SQLDatabase.from_uri(DATABASE_URL)
        return db.get_table_info()
    except Exception:
        return ""


# Engine global para reaproveitamento
ENGINE = create_engine(DATABASE_URL, future=True, pool_pre_ping=True) if DATABASE_URL else None


def _plan_chart(question: str) -> ChartPlan:
    """Gera o plano do gráfico usando LLM com function calling estruturado."""
    db_schema = _get_db_schema_summary()
    chain = _planner_prompt | _llm.with_structured_output(ChartPlan, method="function_calling")
    return chain.invoke({"question": question, "db_schema": db_schema})


def _sanitize_sql(sql: str, allowed_tables: List[str]) -> str:
    """Valida e sanitiza a consulta SQL.

    - Permite apenas SELECT
    - Bloqueia comandos destrutivos (DROP, DELETE, UPDATE, INSERT, ALTER)
    - Restringe o uso a tabelas whitelisted (ex.: clients, vehicles, orders)
    """
    if not sql:
        raise ValueError("SQL vazio")

    normalized = sql.strip().lower()
    if not normalized.startswith("select"):
        raise ValueError("Apenas consultas SELECT são permitidas")

    destructive = re.compile(r"\b(drop|delete|update|insert|alter|truncate|create|grant|revoke|merge)\b", re.IGNORECASE)
    if destructive.search(sql):
        raise ValueError("Comando SQL potencialmente destrutivo detectado")

    # Extrair nomes de tabelas após FROM e JOIN
    table_pattern = re.compile(r"\b(from|join)\s+([a-zA-Z_][\w\.\"]*)", re.IGNORECASE)
    found_tables = set()
    for match in table_pattern.finditer(sql):
        raw = match.group(2).strip().strip('"')
        # se vier schema.table, ficar apenas com tabela
        table = raw.split(".")[-1]
        found_tables.add(table.lower())

    # Se não encontrar tabelas, permitir (ex.: SELECT 1) mas geralmente pediremos dado real
    if found_tables:
        allowed = {t.lower() for t in allowed_tables}
        disallowed = [t for t in found_tables if t not in allowed]
        if disallowed:
            raise ValueError(f"Tabelas não permitidas na consulta: {', '.join(disallowed)}")

    return sql


def _df_from_plan(plan: ChartPlan) -> pd.DataFrame:
    """Cria um DataFrame a partir do plano, usando SQL (sanitizado) ou dados inline."""
    if plan.sql:
        if not DATABASE_URL or not ENGINE:
            raise RuntimeError("DATABASE_URL não configurado para executar SQL")
        safe_sql = _sanitize_sql(plan.sql, allowed_tables=["clients", "vehicles", "service_orders", "service_items", "stock_products"])
        with ENGINE.connect() as conn:
            return pd.read_sql(text(safe_sql), conn)
    if plan.data:
        return pd.DataFrame(plan.data)
    raise ValueError("Plano não contém sql nem dados inline")


def _columns_by_type(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Classifica colunas por tipo: numéricas, categóricas e datas."""
    numeric_cols = [c for c in df.columns if is_numeric_dtype(df[c])]
    datetime_cols = [c for c in df.columns if is_datetime64_any_dtype(df[c])]
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    # Remover duplicatas caso uma coluna caia em múltiplas categorias
    categorical_cols = [c for c in categorical_cols if c not in numeric_cols and c not in datetime_cols]
    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols,
    }


def _chart_requirements_met(plan: ChartPlan, df: pd.DataFrame) -> bool:
    """Verifica se o plano possui colunas suficientes/adequadas para o tipo de gráfico."""
    cols = _columns_by_type(df)
    x, y, hue = plan.x, plan.y, plan.hue
    chart = plan.chart_type

    def is_num(col: Optional[str]) -> bool:
        return bool(col) and col in df.columns and is_numeric_dtype(df[col])

    def is_cat(col: Optional[str]) -> bool:
        return bool(col) and col in cols["categorical"]

    def is_date(col: Optional[str]) -> bool:
        return bool(col) and col in cols["datetime"]

    if chart == "heatmap":
        return len(cols["numeric"]) >= 2
    if chart == "histogram":
        return is_num(x)
    if chart == "pie":
        return (is_cat(x) and is_num(y))
    if chart == "scatter":
        return is_num(x) and is_num(y)
    if chart == "boxplot":
        return (is_cat(x) and is_num(y))
    if chart in ("bar", "stacked_bar", "line"):
        x_ok = is_cat(x) or is_date(x) or (x in df.columns)
        y_ok = is_num(y)
        if chart == "stacked_bar":
            return x_ok and y_ok and is_cat(hue)
        return x_ok and y_ok
    return False


def _suggest_charts_text(df: pd.DataFrame, plan: ChartPlan) -> str:
    """Gera um texto com sugestões de gráficos e colunas possíveis baseadas no DataFrame."""
    cols = _columns_by_type(df)
    num_cols = cols["numeric"]
    cat_cols = cols["categorical"]
    date_cols = cols["datetime"]

    def few(items: List[str], n: int = 3) -> List[str]:
        return items[:n]

    suggestions = []
    if cat_cols and num_cols:
        suggestions.append(f"Barras: x em {few(cat_cols)}, y em {few(num_cols)}")
        suggestions.append(f"Barras empilhadas: x em {few(cat_cols)}, y em {few(num_cols)}, hue em {few([c for c in cat_cols if c != (plan.x or '')])}")
        suggestions.append(f"Boxplot: x em {few(cat_cols)}, y em {few(num_cols)}")
    if date_cols and num_cols:
        suggestions.append(f"Linha: x em {few(date_cols)}, y em {few(num_cols)}")
    if len(num_cols) >= 2:
        suggestions.append(f"Dispersão: x e y em {few(num_cols)}")
        suggestions.append(f"Heatmap: correlação entre {len(num_cols)} variáveis numéricas ({few(num_cols)})")
    if num_cols:
        suggestions.append(f"Histograma: x em {few(num_cols)}")
    if cat_cols and num_cols:
        suggestions.append(f"Pizza: rótulos em {few(cat_cols)} e valores em {few(num_cols)}")

    example_prompts = []
    if cat_cols and num_cols:
        example_prompts.append(f"Faça um gráfico de barras com x={cat_cols[0]} e y={num_cols[0]}")
    if date_cols and num_cols:
        example_prompts.append(f"Faça um gráfico de linha com x={date_cols[0]} e y={num_cols[0]}")
    if len(num_cols) >= 2:
        example_prompts.append(f"Faça um gráfico de dispersão com x={num_cols[0]} e y={num_cols[1]}")
    if cat_cols and num_cols:
        example_prompts.append(f"Faça um boxplot de y={num_cols[0]} por x={cat_cols[0]}")

    header = "Não consegui identificar colunas suficientes para montar o gráfico solicitado.\n\nOpções sugeridas:"
    body = "\n- " + "\n- ".join(suggestions) if suggestions else "\n(Não foi possível sugerir sem colunas adequadas)"
    examples = "\n\nExemplos de prompts:\n- " + "\n- ".join(example_prompts) if example_prompts else ""
    return header + body + examples


def _suggest_charts_list(df: pd.DataFrame, plan: ChartPlan) -> List[str]:
    """Retorna uma lista com sugestões curtas para orientar o usuário a completar o pedido."""
    cols = _columns_by_type(df)
    num_cols = cols["numeric"]
    cat_cols = cols["categorical"]
    date_cols = cols["datetime"]
    out: List[str] = []
    if cat_cols and num_cols:
        out.append(f"Barras: x={cat_cols[0]}, y={num_cols[0]}")
    if cat_cols and num_cols:
        out.append(f"Barras empilhadas: x={cat_cols[0]}, y={num_cols[0]}, hue={cat_cols[min(1, len(cat_cols)-1)]}")
    if date_cols and num_cols:
        out.append(f"Linha: x={date_cols[0]}, y={num_cols[0]}")
    if len(num_cols) >= 2:
        out.append(f"Dispersão: x={num_cols[0]}, y={num_cols[1]}")
        out.append("Heatmap de correlação entre colunas numéricas")
    if cat_cols and num_cols:
        out.append(f"Boxplot: x={cat_cols[0]}, y={num_cols[0]}")
        out.append(f"Pizza: rótulos={cat_cols[0]}, valores={num_cols[0]}")
    if num_cols:
        out.append(f"Histograma: x={num_cols[0]}")
    return out


def _plot_from_df(df: pd.DataFrame, plan: ChartPlan) -> bytes:
    """Gera a figura a partir do DataFrame conforme o plano e retorna bytes PNG."""
    sns.set_theme(style="whitegrid")
    sns.set_palette(sns.color_palette("tab10"))
    fig, ax = plt.subplots(figsize=(8, 5))

    chart = plan.chart_type
    x = plan.x
    y = plan.y
    hue = plan.hue

    if chart == "line":
        line = sns.lineplot(data=df, x=x, y=y, hue=hue, marker="o", ax=ax)
        # Adicionar rótulos para pontos (valor de y)
        for l in ax.lines:
            xy = l.get_xydata()
            for xp, yp in xy:
                ax.annotate(f"{yp:.0f}", (xp, yp), textcoords="offset points", xytext=(0, 5), ha="center", fontsize=8)
    elif chart == "bar":
        sns.barplot(data=df, x=x, y=y, hue=hue, ax=ax)
        for container in ax.containers:
            try:
                ax.bar_label(container, fmt="%.0f")
            except Exception:
                pass
    elif chart == "stacked_bar":
        sns.barplot(data=df, x=x, y=y, hue=hue, dodge=False, ax=ax)
        for container in ax.containers:
            try:
                ax.bar_label(container, fmt="%.0f")
            except Exception:
                pass
    elif chart == "boxplot":
        sns.boxplot(data=df, x=x, y=y, hue=hue, ax=ax)
    elif chart == "scatter":
        sns.scatterplot(data=df, x=x, y=y, hue=hue, ax=ax)
    elif chart == "histogram":
        sns.histplot(data=df, x=x, hue=hue, kde=True, bins="auto", ax=ax)
    elif chart == "heatmap":
        corr = df.corr(numeric_only=True)
        if corr.empty:
            raise ValueError("Não há colunas numéricas suficientes para heatmap")
        sns.heatmap(corr, annot=True, cmap="coolwarm", ax=ax)
    elif chart == "pie":
        # Para pizza, usamos matplotlib diretamente. Requer agregação prévia.
        values_col = y if y and y in df.columns else (x if x and x in df.columns else None)
        labels_col = x if values_col == y else y
        if values_col is None or labels_col is None:
            # fallback: frequências da primeira coluna
            target_col = x if x and x in df.columns else df.columns[0]
            counts = df[target_col].value_counts()
            values = counts.values
            labels = counts.index.astype(str).tolist()
        else:
            grouped = df.groupby(labels_col)[values_col].sum(numeric_only=True)
            values = grouped.values
            labels = grouped.index.astype(str).tolist()
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
        ax.axis("equal")
    else:
        raise ValueError(f"Tipo de gráfico não suportado: {chart}")

    if plan.title:
        ax.set_title(plan.title)

    plt.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer.read()


_explain_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
Você é um analista de dados. Explique em 2 frases curtas e claras, em português,
o que o gráfico descrito abaixo mostra. Seja objetivo e evite jargões.
""".strip(),
    ),
    (
        "human",
        """
Plano: {plan}
Resumo dos dados (describe):
{summary}
""".strip(),
    ),
])


def explain_chart(df: pd.DataFrame, plan: ChartPlan) -> str:
    """Gera uma explicação curta do gráfico usando o LLM com base no describe."""
    try:
        summary = df.describe(include="all").to_string()
    except Exception:
        summary = ""
    chain = _explain_prompt | _llm
    resp = chain.invoke({"plan": plan.model_dump(), "summary": summary})
    return (resp.content or "Aqui está o gráfico solicitado.").strip()


def run_chart_agent(question: str) -> Dict[str, Any]:
    """Executa o agente de gráficos de ponta a ponta e retorna o payload padronizado."""
    try:
        plan = _plan_chart(question)
    except Exception as e:
        return {"reply": f"Não consegui planejar a visualização automaticamente: {e}"}

    try:
        df = _df_from_plan(plan)
        if df.empty:
            return {"reply": "Consulta retornou vazio. Não há dados para plotar."}
    except Exception as e:
        return {"reply": f"Falha ao obter dados: {e}"}

    # Se o plano não possui colunas necessárias, ofereça sugestões em vez de falhar
    if not _chart_requirements_met(plan, df):
        suggestions_text = _suggest_charts_text(df, plan)
        suggestions_list = _suggest_charts_list(df, plan)
        return {
            "reply": suggestions_text,
            "suggestions": suggestions_list,
            "columns_by_type": _columns_by_type(df),
        }

    try:
        image_bytes = _plot_from_df(df, plan)
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        caption = plan.explanation or explain_chart(df, plan)
        return {
            "reply": caption or "Aqui está o gráfico solicitado.",
            "chart_base64": b64,
            "chart_mime": "image/png",
        }
    except Exception as e:
        return {"reply": f"Falha ao renderizar gráfico: {e}"}


