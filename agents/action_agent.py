import os
import re
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)


# ========================================
# Mapeamento de Comandos → Endpoints
# ========================================

ACTION_MAPPINGS = {
    "create_client": {
        "endpoint": "/clients",
        "method": "POST",
        "description": "Cadastrar um novo cliente",
        "required_params": ["name"],
        "optional_params": ["cpf", "phone", "email", "address", "city", "state", "zipCode", "observations"],
        "confirmation_message": "Deseja cadastrar o cliente '{name}'?",
        "auto_execute": True  # Executa automaticamente sem confirmação
    },
    "create_service_order": {
        "endpoint": "/service-orders",
        "method": "POST",
        "description": "Criar uma nova Ordem de Serviço",
        "required_params": ["vehicleId", "clientId", "description"],
        "optional_params": ["problemDescription", "technicianName", "currentKilometers", "estimatedCompletion", "observations", "laborCost", "partsCost", "discount"],
        "confirmation_message": "Deseja realmente criar uma nova Ordem de Serviço?"
    },
    "update_service_order_status": {
        "endpoint": "/service-orders/{id}/status",
        "method": "PUT",
        "description": "Atualizar status de uma Ordem de Serviço",
        "required_params": ["id", "status"],
        "optional_params": ["observations"],
        "confirmation_message": "Deseja realmente atualizar o status da OS #{id} para {status}?"
    },
    "create_inventory_item": {
        "endpoint": "/inventory/items",
        "method": "POST",
        "description": "Criar um item no estoque",
        "required_params": ["partId", "location", "quantity", "unitCost"],
        "optional_params": ["salePrice", "minimumStock", "observations"],
        "confirmation_message": "Deseja realmente adicionar {quantity} unidades da peça ao estoque?"
    },
    "create_part": {
        "endpoint": "/parts",
        "method": "POST",
        "description": "Criar uma nova peça no catálogo",
        "required_params": ["name", "sku", "category"],
        "optional_params": ["brand", "model", "description", "supplierInfo", "unitCost", "salePrice", "markup"],
        "confirmation_message": "Deseja realmente criar a peça '{name}' no catálogo?"
    },
    "add_item_to_service_order": {
        "endpoint": "/service-orders/{serviceOrderId}/items",
        "method": "POST",
        "description": "Adicionar item/peça a uma Ordem de Serviço",
        "required_params": ["serviceOrderId", "productCode", "quantity", "unitPrice"],
        "optional_params": ["description", "type"],
        "confirmation_message": "Deseja adicionar {quantity}x {productCode} à OS #{serviceOrderId}?"
    }
}

STATUS_MAPPING = {
    "pendente": "PENDING",
    "em andamento": "IN_PROGRESS",
    "aguardando peças": "WAITING_PARTS",
    "aguardando aprovação": "WAITING_APPROVAL",
    "concluída": "COMPLETED",
    "concluido": "COMPLETED",
    "cancelada": "CANCELLED",
    "cancelado": "CANCELLED",
}


# ========================================
# Parser de Intenções
# ========================================

_intent_parser_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é um parser de intenções de comandos para o sistema GoMech.

Analise a mensagem do usuário e identifique se é um COMANDO DE AÇÃO.

**COMANDOS SUPORTADOS:**
1. **create_client** - Cadastrar novo cliente
   Exemplos: "Cadastre o cliente João Silva", "Adicionar cliente", "Novo cliente"
   
2. **create_service_order** - Criar nova OS
   Exemplos: "Crie uma OS para o cliente X", "Abrir ordem de serviço", "Nova OS"
   
3. **update_service_order_status** - Atualizar status de OS
   Exemplos: "Marque a OS 123 como concluída", "Atualizar status da OS 45 para em andamento"
   
4. **create_inventory_item** - Adicionar item ao estoque
   Exemplos: "Adicione 10 unidades da peça X ao estoque", "Entrada de estoque"
   
5. **create_part** - Criar nova peça no catálogo
   Exemplos: "Cadastre a peça Filtro de óleo", "Criar nova peça"
   
6. **add_item_to_service_order** - Adicionar item a OS
   Exemplos: "Adicione o filtro de óleo na OS 123", "Incluir peça na ordem 45"

**EXTRAÇÃO DE PARÂMETROS:**
Extraia todos os parâmetros possíveis da mensagem, como:
- IDs (veículo, cliente, OS, peça)
- Nomes (cliente, técnico, peça)
- Números (quantidade, preço, quilometragem)
- Status (pendente, concluída, etc)
- Datas
- Descrições

**FORMATO DE RESPOSTA:**
Se for um comando, responda em JSON:
{{
  "is_command": true,
  "action": "nome_do_comando",
  "params": {{
    "param1": "valor1",
    "param2": "valor2"
  }},
  "missing_params": ["param3", "param4"]
}}

Se NÃO for um comando, responda:
{{
  "is_command": false
}}

Seja preciso na extração de parâmetros. Se o usuário mencionar um ID, capture-o. Se mencionar um nome, capture-o.
"""),
    ("human", "{message}")
])


def _parse_intent(message: str) -> Dict[str, Any]:
    """
    Usa LLM para detectar intenção de comando e extrair parâmetros.
    """
    try:
        chain = _intent_parser_prompt | _llm
        result = chain.invoke({"message": message})
        
        # Tentar parsear JSON da resposta
        import json
        response_text = result.content.strip()
        
        # Remover markdown code blocks se presentes
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        parsed = json.loads(response_text)
        return parsed
        
    except Exception as e:
        logger.error(f"❌ [Action Parser] Erro ao parsear intenção: {str(e)}")
        return {"is_command": False}


def _normalize_status(status: str) -> Optional[str]:
    """
    Normaliza status para o formato esperado pelo backend.
    """
    status_lower = status.lower().strip()
    return STATUS_MAPPING.get(status_lower, status.upper())


def _validate_and_enrich_params(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida parâmetros e enriquece com valores padrão se necessário.
    """
    action_config = ACTION_MAPPINGS.get(action)
    if not action_config:
        return params
    
    # Normalizar status se presente
    if "status" in params:
        params["status"] = _normalize_status(params["status"])
    
    # Converter tipos se necessário
    numeric_fields = ["id", "vehicleId", "clientId", "serviceOrderId", "partId", "quantity", "unitCost", "salePrice", "unitPrice", "laborCost", "partsCost", "discount", "currentKilometers"]
    for field in numeric_fields:
        if field in params and isinstance(params[field], str):
            try:
                # Tentar converter para int ou float
                if "." in params[field] or "cost" in field.lower() or "price" in field.lower():
                    params[field] = float(params[field])
                else:
                    params[field] = int(params[field])
            except ValueError:
                pass
    
    return params


# ========================================
# Verificação de Parâmetros
# ========================================

def _check_missing_params(action: str, params: Dict[str, Any]) -> List[str]:
    """
    Verifica quais parâmetros obrigatórios estão faltando.
    """
    action_config = ACTION_MAPPINGS.get(action)
    if not action_config:
        return []
    
    required = action_config["required_params"]
    missing = [param for param in required if param not in params or params[param] is None]
    
    return missing


def _generate_missing_params_message(action: str, missing: List[str]) -> str:
    """
    Gera mensagem amigável pedindo os parâmetros faltantes.
    """
    action_config = ACTION_MAPPINGS.get(action)
    action_desc = action_config["description"] if action_config else "executar a ação"
    
    param_names = {
        "id": "ID da OS",
        "vehicleId": "ID do veículo",
        "clientId": "ID do cliente",
        "description": "descrição do serviço",
        "status": "novo status (ex: CONCLUÍDA, EM ANDAMENTO, PENDENTE)",
        "partId": "ID da peça",
        "location": "localização no estoque",
        "quantity": "quantidade",
        "unitCost": "custo unitário",
        "name": "nome (cliente ou peça)",
        "sku": "código SKU",
        "category": "categoria",
        "serviceOrderId": "ID da OS",
        "productCode": "código do produto",
        "unitPrice": "preço unitário",
        "cpf": "CPF do cliente",
        "phone": "telefone do cliente",
        "email": "e-mail do cliente",
        "address": "endereço do cliente"
    }
    
    missing_names = [param_names.get(p, p) for p in missing]
    
    if len(missing_names) == 1:
        return f"📋 Para {action_desc}, preciso saber: **{missing_names[0]}**\n\nPor favor, informe esse dado."
    else:
        items = "\n".join([f"• {name}" for name in missing_names])
        return f"📋 Para {action_desc}, preciso dos seguintes dados:\n\n{items}\n\nPor favor, informe esses dados."


# ========================================
# Função Principal
# ========================================

def run_action_agent(message: str) -> Dict[str, Any]:
    """
    Detecta e processa comandos de ação.
    
    Args:
        message: Mensagem do usuário
    
    Returns:
        Dict com:
        - is_command: bool
        - action: str (nome da ação)
        - params: dict (parâmetros extraídos)
        - pending_confirmation: bool
        - confirmation_message: str
        - missing_params: list
        - reply: str (resposta para o usuário)
    """
    logger.info(f"🤖 [Action Agent] Mensagem: {message}")
    
    # 1. Parsear intenção
    intent = _parse_intent(message)
    
    if not intent.get("is_command"):
        return {
            "is_command": False,
            "reply": "Não identifiquei um comando de ação nessa mensagem."
        }
    
    action = intent.get("action")
    params = intent.get("params", {})
    
    logger.info(f"✅ [Action Agent] Ação identificada: {action}")
    logger.info(f"📋 [Action Agent] Parâmetros: {params}")
    
    # 2. Validar se a ação existe
    if action not in ACTION_MAPPINGS:
        return {
            "is_command": True,
            "action": action,
            "reply": f"❌ Ação '{action}' não é suportada. Comandos disponíveis: criar OS, atualizar status, criar peça, adicionar item."
        }
    
    action_config = ACTION_MAPPINGS[action]
    
    # 3. Enriquecer e validar parâmetros
    params = _validate_and_enrich_params(action, params)
    
    # 4. Verificar parâmetros faltantes
    missing = _check_missing_params(action, params)
    
    if missing:
        return {
            "is_command": True,
            "action": action,
            "params": params,
            "missing_params": missing,
            "pending_confirmation": False,
            "reply": _generate_missing_params_message(action, missing)
        }
    
    # 5. Verificar se a ação deve ser executada automaticamente
    auto_execute = action_config.get("auto_execute", False)
    
    if auto_execute:
        # Ação será executada automaticamente, sem confirmação
        return {
            "is_command": True,
            "action": action,
            "params": params,
            "missing_params": [],
            "pending_confirmation": False,
            "auto_execute": True,
            "action_description": action_config["description"],
            "endpoint": action_config["endpoint"],
            "method": action_config["method"],
            "reply": f"⏳ Executando: {action_config['description']}..."
        }
    
    # 6. Gerar mensagem de confirmação (para ações que precisam)
    confirmation_msg = action_config["confirmation_message"]
    
    # Substituir placeholders na mensagem
    for key, value in params.items():
        confirmation_msg = confirmation_msg.replace(f"{{{key}}}", str(value))
    
    return {
        "is_command": True,
        "action": action,
        "params": params,
        "missing_params": [],
        "pending_confirmation": True,
        "auto_execute": False,
        "confirmation_message": confirmation_msg,
        "action_description": action_config["description"],
        "endpoint": action_config["endpoint"],
        "method": action_config["method"],
        "reply": f"✅ Comando identificado!\n\n{confirmation_msg}"
    }

