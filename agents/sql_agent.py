import os
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

db = SQLDatabase.from_uri(DATABASE_URL)
_sql_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

sql_agent = create_sql_agent(
    llm=_sql_llm,
    db=db,
    agent_type="openai-tools",
    verbose=True
)

def run_sql_agent(question: str) -> str:
    logger.info(f"SQL Agent chamado com pergunta: {question}")
    resposta = sql_agent.invoke({"input": question})
    return resposta["output"]
