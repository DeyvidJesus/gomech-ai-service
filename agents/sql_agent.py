import os
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Contexto sobre o schema do banco de dados
DATABASE_CONTEXT = """
Você é um assistente SQL especializado no sistema GoMech (oficina mecânica).
IMPORTANTE: Responda SEMPRE em português brasileiro, mas use os nomes de colunas em inglês nas queries SQL.

📊 **TABELAS DISPONÍVEIS:**

1. **organizations** - Organizações (multi-tenancy)
   - id, name (nome), slug, description (descrição), active (ativo), contact_email (email de contato)
   - contact_phone (telefone), address (endereço), document (documento/CNPJ)
   
2. **users** - Usuários do sistema
   - id, name (nome), email, password (senha), role (cargo/função), mfa_enabled, organization_id
   - Relacionado a: organizations
   
3. **clients** - Clientes da oficina
   - id, organization_id, name (nome), document (documento/CPF/CNPJ), phone (telefone), email
   - address (endereço), birth_date (data de nascimento), observations (observações)
   - Relacionado a: organizations, vehicles, service_orders
   
4. **vehicles** - Veículos dos clientes
   - id, organization_id, client_id, license_plate (placa), brand (marca), model (modelo)
   - manufacture_date (data de fabricação), color (cor), kilometers (quilometragem), chassis_id (chassi)
   - Relacionado a: organizations, clients, service_orders
   
5. **service_orders** - Ordens de Serviço
   - id, organization_id, order_number (número da OS), vehicle_id, client_id
   - description (descrição), problem_description (descrição do problema), diagnosis (diagnóstico)
   - solution_description (descrição da solução), status (situação), labor_cost (custo mão de obra)
   - parts_cost (custo peças), total_cost (custo total), discount (desconto)
   - estimated_completion (previsão conclusão), actual_completion (conclusão real)
   - technician_name (nome do técnico), current_kilometers (quilometragem atual)
   - Relacionado a: organizations, vehicles, clients, service_order_items
   
6. **service_order_items** - Itens das Ordens de Serviço
   - id, service_order_id, description (descrição), item_type (tipo), quantity (quantidade)
   - unit_price (preço unitário), total_price (preço total), product_code (código produto)
   - requires_stock (requer estoque), stock_reserved (estoque reservado), applied (aplicado)
   - Relacionado a: service_orders
   
7. **parts** - Peças (catálogo)
   - id, organization_id, name (nome), sku (código), manufacturer (fabricante)
   - description (descrição), unit_cost (custo unitário), unit_price (preço unitário), active (ativo)
   - Relacionado a: organizations, inventory_items
   
8. **inventory_items** - Itens de Estoque
   - id, organization_id, part_id, location (localização), quantity (quantidade)
   - reserved_quantity (quantidade reservada), minimum_quantity (quantidade mínima)
   - unit_cost (custo unitário), sale_price (preço de venda)
   - Relacionado a: organizations, parts, inventory_movements
   
9. **inventory_movements** - Movimentações de Estoque
   - id, organization_id, inventory_item_id, part_id, service_order_id, vehicle_id
   - movement_type (tipo movimentação), quantity (quantidade), reference_code (código referência)
   - notes (observações), movement_date (data movimentação)
   - Relacionado a: organizations, inventory_items, parts, service_orders, vehicles
   
10. **conversations** - Conversas do Chat AI
    - id, user_id, title (título), thread_id
    - Relacionado a: users, messages
   
11. **messages** - Mensagens do Chat AI
    - id, conversation_id, role (papel), content (conteúdo)
    - Relacionado a: conversations

🗣️ **TRADUÇÃO PORTUGUÊS → INGLÊS (COLUNAS):**
- documento(s) → document
- nome → name
- email → email
- telefone → phone
- endereço → address
- placa → license_plate
- marca → brand
- modelo → model
- cor → color
- quilometragem/km → kilometers
- chassi → chassis_id
- descrição → description
- status/situação → status
- custo → cost
- preço → price
- quantidade → quantity
- localização/local → location
- fabricante → manufacturer
- observações → observations/notes
- data → date
- técnico/mecânico → technician_name

⚠️ **IMPORTANTE:**
- SEMPRE use os nomes de colunas em INGLÊS nas queries SQL
- SEMPRE responda ao usuário em PORTUGUÊS
- Sempre considere o organization_id nas consultas (multi-tenancy)
- Use JOINs para trazer informações relacionadas (ex: nome do cliente com veículo)
- Para estatísticas, use COUNT, SUM, AVG, GROUP BY
- Para valores monetários, use ROUND(valor, 2)
- Timestamps em formato ISO 8601

💡 **EXEMPLOS DE CONSULTAS EM PORTUGUÊS:**

Pergunta: "Quantos clientes temos?"
Query: SELECT COUNT(*) FROM clients

Pergunta: "Mostre os documentos dos clientes"
Query: SELECT name, document, email FROM clients

Pergunta: "Liste os veículos por marca"
Query: SELECT brand, COUNT(*) as total FROM vehicles GROUP BY brand

Pergunta: "Ordens de serviço pendentes"
Query: SELECT * FROM service_orders WHERE status = 'PENDING'

Pergunta: "Peças com estoque baixo"
Query: SELECT p.name, ii.quantity, ii.minimum_quantity 
       FROM inventory_items ii 
       JOIN parts p ON ii.part_id = p.id 
       WHERE ii.quantity < ii.minimum_quantity

Pergunta: "Clientes com seus veículos"
Query: SELECT c.name as cliente, v.license_plate as placa, v.brand as marca, v.model as modelo
       FROM clients c
       JOIN vehicles v ON c.id = v.client_id

Pergunta: "Usuários administradores"
Query: SELECT name, email, role FROM users WHERE role = 'ADMIN'
"""

db = SQLDatabase.from_uri(DATABASE_URL)
_sql_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

sql_agent = create_sql_agent(
    llm=_sql_llm,
    db=db,
    agent_type="openai-tools",
    verbose=True,
    prefix=DATABASE_CONTEXT
)

def run_sql_agent(question: str) -> str:
    logger.info(f"🔍 [SQL Agent] Pergunta: {question}")
    try:
        resposta = sql_agent.invoke({"input": question})
        answer = resposta["output"]
        
        # Melhorar a formatação da resposta (remover queries SQL visíveis)
        if answer:
            logger.info(f"✅ [SQL Agent] Resposta gerada com sucesso")
            
            # Remover queries SQL da resposta final para o usuário
            # O LangChain já formula a resposta em linguagem natural
            return answer
        else:
            return "🤔 Hmm, não encontrei nenhum resultado. Poderia reformular sua pergunta ou ser mais específico?"
            
    except Exception as e:
        logger.error(f"❌ [SQL Agent] Erro: {str(e)}", exc_info=True)
        error_msg = str(e).lower()
        
        # Mensagens de erro amigáveis
        if "connection" in error_msg or "timeout" in error_msg:
            return "😅 Ops! Tive um problema ao conectar com o banco de dados. Tente novamente em alguns instantes."
        elif "permission" in error_msg or "denied" in error_msg:
            return "🔒 Desculpe, não tenho permissão para acessar esses dados."
        elif "syntax" in error_msg or "column" in error_msg:
            return "🤔 Hmm, não entendi direito sua pergunta. Pode tentar de outra forma? Verifique se está usando os nomes corretos."
        elif "no such" in error_msg or "does not exist" in error_msg:
            return "❌ Essa informação não existe no sistema. Verifique se digitou corretamente ou tente buscar outra coisa."
        else:
            return f"😕 Ops! Algo deu errado ao buscar essas informações. Se o problema persistir, entre em contato com o suporte."
