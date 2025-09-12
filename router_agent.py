import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

_router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

_router_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é um roteador de mensagens.
Decide se a pergunta deve ir para:
- SQL → se precisa de dados reais do banco (clients, vehicles, orders, etc.)
- CHAT → se é conversa, explicação ou não envolve dados reais
- GRÁFICO → se a pergunta pede visualização ou gráfico dos dados

Responda apenas com: "sql", "chat" ou "grafico"
"""),
    ("human", "{question}")
])

def route_question(question: str) -> str:
    chain = _router_prompt | _router_llm
    result = chain.invoke({"question": question})
    return result.content.strip().lower()