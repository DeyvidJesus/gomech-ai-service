import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.vectorstores.pgvector import PGVector
from langchain.chains import RetrievalQA

load_dotenv()

DB_URL = os.getenv("DB_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0, 
    api_key=OPENAI_API_KEY
)

# Configuração embeddings + pgVector
embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

# Conecta no Postgres com extensão pgVector
vectorstore = PGVector(
    connection_string=DB_URL,
    embedding_function=embeddings,
    collection_name="vector_store"
)

# Cria retriever (para RAG)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Cria chain de QA
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff"
)

def ask_question(query: str) -> str:
    """Executa uma query com RAG no pgVector + LLM"""
    result = qa_chain.run(query)
    return result
