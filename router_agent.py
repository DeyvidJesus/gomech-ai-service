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
Você é um roteador inteligente de mensagens do sistema GoMech.
Analise a pergunta do usuário e decida qual agente deve responder.

🗄️ **SQL** → Consultas ao banco de dados
   Palavras-chave: quantos, mostre, liste, busque, encontre, qual, quais, total, contagem
   Dados: clientes, usuários, veículos, ordens de serviço, peças, estoque, inventário
   Exemplos:
   - "Quantos clientes temos?"
   - "Mostre os veículos da marca Honda"
   - "Liste as ordens de serviço pendentes"
   - "Qual o estoque da peça X?"
   - "Busque o cliente com CPF 123"
   - "Total de custos das OSs este mês"

💬 **CHAT** → Conversação e explicações
   Palavras-chave: como, por que, o que é, explique, ajude, oi, olá, obrigado
   Contexto: saudações, dúvidas conceituais, agradecimentos
   Exemplos:
   - "Olá!" / "Oi" / "Bom dia"
   - "Como funciona o sistema?"
   - "O que é uma ordem de serviço?"
   - "Pode me ajudar?"
   - "Obrigado!" / "Valeu!"
   - "Qual é sua função?"

📊 **GRAFICO** → Visualizações e gráficos
   Palavras-chave: gráfico, visualize, mostre gráfico, chart, dashboard, plotar
   Contexto: pedidos explícitos de visualização gráfica
   Exemplos:
   - "Mostre um gráfico de vendas"
   - "Crie um gráfico de veículos por marca"
   - "Visualize o estoque em gráfico"
   - "Quero ver um dashboard"

🌐 **WEB** → Busca de vídeos e tutoriais
   Palavras-chave: vídeo, tutorial, aprenda, como fazer, ensine, YouTube
   Contexto: busca de conteúdo educativo externo
   Exemplos:
   - "Mostre vídeos sobre troca de óleo"
   - "Tutorial de alinhamento"
   - "Como fazer balanceamento"
   - "Aprenda a trocar pastilha de freio"
   - "Vídeo sobre suspensão"

⚠️ **REGRAS DE DECISÃO:**
1. Se mencionar dados específicos (nomes, números, contagens) → SQL
2. Se pedir gráfico explicitamente → GRAFICO
3. Se pedir vídeo/tutorial explicitamente → WEB
4. Se for saudação, agradecimento ou dúvida conceitual → CHAT
5. Em caso de dúvida entre SQL e CHAT → prefira SQL se houver qualquer menção a dados
6. Em caso de dúvida entre SQL e GRAFICO → prefira GRAFICO apenas se explicitamente pedir visualização

Responda APENAS com: "sql", "chat", "grafico" ou "web"
"""),
    ("human", "{question}")
])

def route_question(question: str) -> str:
    chain = _router_prompt | _router_llm
    result = chain.invoke({"question": question})
    return result.content.strip().lower()