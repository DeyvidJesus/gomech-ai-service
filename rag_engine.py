import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import PGVector
from langchain.chains import RetrievalQA
from pydantic import SecretStr

load_dotenv()

DB_URL = os.getenv("DB_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validação das variáveis de ambiente
if not DB_URL:
    raise ValueError("DB_URL não foi definida no arquivo .env")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não foi definida no arquivo .env")

# LLM para IA aprimorada (RAG)
llm_enhanced = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=SecretStr(OPENAI_API_KEY)
)

# LLM para IA padrão (sem RAG)
llm_standard = ChatOpenAI(
    model="gpt-3.5-turbo",  # Modelo mais barato para IA padrão
    temperature=0.3,
    api_key=SecretStr(OPENAI_API_KEY)
)

# Configuração embeddings + pgVector (apenas para IA aprimorada)
embeddings = OpenAIEmbeddings(api_key=SecretStr(OPENAI_API_KEY))

# Conecta no Postgres com extensão pgVector
vectorstore = PGVector(
    connection_string=DB_URL,
    embedding_function=embeddings,
    collection_name="vector_store"
)

# Cria retriever (para RAG)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Cria chain de QA para IA aprimorada
qa_chain = RetrievalQA.from_chain_type(
    llm=llm_enhanced,
    retriever=retriever,
    chain_type="stuff"
)

def ask_question(query: str) -> str:
    """
    IA APRIMORADA: Executa uma query com RAG no pgVector + LLM
    Usa retrieval-augmented generation para respostas mais contextualizadas
    """
    try:
        # Adiciona contexto específico para dados da oficina mecânica
        enhanced_query = f"""
        Como assistente especializado em dados de oficina mecânica, responda a seguinte pergunta 
        baseado nos dados disponíveis na base de conhecimento:
        
        {query}
        
        Se a pergunta for sobre análises, forneça insights detalhados. 
        Se for sobre dados específicos, seja preciso nos números.
        Sempre contextualize sua resposta com informações relevantes dos dados.
        """
        
        result = qa_chain.run(enhanced_query)
        return result
        
    except Exception as e:
        # Fallback para IA padrão em caso de erro
        print(f"Erro na IA aprimorada, usando fallback: {e}")
        return ask_simple_question(query)

def ask_simple_question(query: str) -> str:
    """
    IA PADRÃO: Executa uma query simples sem RAG
    Usa apenas o LLM sem busca em base de conhecimento
    """
    try:
        # Contexto básico para perguntas sobre oficina mecânica
        system_prompt = """
        Você é um assistente de IA para uma oficina mecânica chamada GoMech.
        
        Responda perguntas sobre:
        - Gestão de oficina mecânica
        - Análise de dados de serviços automotivos
        - Relatórios de vendas e clientes
        - Operações de manutenção veicular
        
        Seja profissional, preciso e útil. Se não tiver dados específicos,
        forneça orientações gerais baseadas em boas práticas do setor.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        response = llm_standard.invoke(messages)
        return response.content
        
    except Exception as e:
        return f"Erro ao processar pergunta: {str(e)}"

def get_ai_status():
    """
    Verifica o status dos serviços de IA
    """
    status = {
        "standard_ai": False,
        "enhanced_ai": False,
        "database_connection": False,
        "embeddings": False
    }
    
    try:
        # Testa IA padrão
        test_response = llm_standard.invoke([{"role": "user", "content": "teste"}])
        if test_response:
            status["standard_ai"] = True
    except:
        pass
    
    try:
        # Testa IA aprimorada
        test_response = llm_enhanced.invoke([{"role": "user", "content": "teste"}])
        if test_response:
            status["enhanced_ai"] = True
    except:
        pass
    
    try:
        # Testa conexão com database
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            status["database_connection"] = True
    except:
        pass
    
    try:
        # Testa embeddings
        test_embedding = embeddings.embed_query("teste")
        if test_embedding:
            status["embeddings"] = True
    except:
        pass
    
    return status

# Função para indexar novos documentos (para futuro uso)
def index_document(text: str, metadata: dict = None):
    """
    Indexa um novo documento no vector store
    """
    try:
        vectorstore.add_texts([text], metadatas=[metadata or {}])
        return True
    except Exception as e:
        print(f"Erro ao indexar documento: {e}")
        return False 
