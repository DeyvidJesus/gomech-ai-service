"""
FASE 10 - Vision Agent: Interpretação de imagem com IA

Funcionalidades:
- Análise de fotos de peças danificadas
- Identificação de problemas visuais
- Sugestão de substituição/reparo
- Estimativa de gravidade
- OCR para leitura de códigos de peça
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import base64

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)


def analyze_part_image_openai(image_base64: str, part_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Analisa imagem de peça usando OpenAI Vision API (GPT-4 Vision).
    
    Args:
        image_base64: Imagem em formato base64
        part_context: Contexto adicional (tipo de peça, veículo, etc)
    
    Returns:
        Análise detalhada da imagem com recomendações
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Construir prompt
        base_prompt = """
Você é um mecânico especialista analisando uma foto de peça automotiva.

Analise a imagem e forneça:

1. **Identificação**: Que peça é essa? (ex: pastilha de freio, filtro de óleo, correia)
2. **Condição**: Estado atual (novo, usado, desgastado, danificado, crítico)
3. **Problemas Visíveis**: Liste todos os problemas que você identifica
4. **Gravidade**: Classifique de 1-5 (1=normal, 5=crítico/perigoso)
5. **Recomendação**: O que deve ser feito? (trocar imediatamente, monitorar, limpar, etc)
6. **Risco**: Existe risco de segurança se não for resolvido?
7. **Estimativa de Vida Útil**: Quanto tempo ainda pode durar (em km ou meses)

Seja específico e técnico. Use terminologia automotiva apropriada.
"""
        
        if part_context:
            base_prompt += f"\n\n**Contexto adicional:** {part_context}"
        
        # Fazer requisição para GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4o",  # ou gpt-4-vision-preview
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": base_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        analysis_text = response.choices[0].message.content
        
        # Extrair informações estruturadas (parsing simples)
        analysis = {
            "raw_analysis": analysis_text,
            "identified_part": _extract_field(analysis_text, "Identificação"),
            "condition": _extract_field(analysis_text, "Condição"),
            "problems": _extract_field(analysis_text, "Problemas Visíveis"),
            "severity": _extract_severity(analysis_text),
            "recommendation": _extract_field(analysis_text, "Recomendação"),
            "safety_risk": _extract_field(analysis_text, "Risco"),
            "estimated_lifespan": _extract_field(analysis_text, "Estimativa de Vida Útil")
        }
        
        logger.info(f"👁️ [Vision] Imagem analisada: {analysis['identified_part']} - Gravidade {analysis['severity']}/5")
        
        return {
            "status": "success",
            "analysis": analysis,
            "message": "Imagem analisada com sucesso!"
        }
        
    except Exception as e:
        logger.error(f"❌ [Vision] Erro na análise: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Erro ao analisar imagem"
        }


def detect_damage_level(image_base64: str) -> Dict[str, Any]:
    """
    Detecta nível de dano em uma peça automotiva.
    
    Classificação:
    - NORMAL: Peça em bom estado
    - WEAR: Desgaste normal de uso
    - DAMAGE: Dano evidente, requer atenção
    - CRITICAL: Dano crítico, substituir imediatamente
    
    Args:
        image_base64: Imagem em formato base64
    
    Returns:
        Nível de dano e detalhes
    """
    try:
        # Usar análise completa
        result = analyze_part_image_openai(image_base64)
        
        if result["status"] != "success":
            return result
        
        severity = result["analysis"]["severity"]
        
        # Mapear gravidade para nível de dano
        if severity >= 4:
            damage_level = "CRITICAL"
            damage_message = "🚨 CRÍTICO: Substituição imediata necessária"
            action = "REPLACE_IMMEDIATELY"
        elif severity == 3:
            damage_level = "DAMAGE"
            damage_message = "⚠️ DANO: Requer atenção em breve"
            action = "SCHEDULE_REPLACEMENT"
        elif severity == 2:
            damage_level = "WEAR"
            damage_message = "👀 DESGASTE: Monitorar condição"
            action = "MONITOR"
        else:
            damage_level = "NORMAL"
            damage_message = "✅ NORMAL: Peça em bom estado"
            action = "NO_ACTION"
        
        return {
            "status": "success",
            "damage_level": damage_level,
            "damage_message": damage_message,
            "severity_score": severity,
            "recommended_action": action,
            "full_analysis": result["analysis"]
        }
        
    except Exception as e:
        logger.error(f"❌ [Vision] Erro na detecção de dano: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def suggest_replacement_part(identified_part: str, vehicle_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Sugere peça de substituição baseada na identificação.
    
    Args:
        identified_part: Nome da peça identificada
        vehicle_info: Informações do veículo (marca, modelo, ano)
    
    Returns:
        Sugestões de peças e onde comprar
    """
    try:
        # Base de conhecimento simplificada
        part_suggestions = {
            "pastilha de freio": {
                "category": "FREIOS",
                "alternatives": ["Pastilha cerâmica", "Pastilha semi-metálica", "Pastilha orgânica"],
                "average_price": "R$ 120-280",
                "brands": ["Cobreq", "Fras-le", "TRW", "Bosch"],
                "lifespan_km": "30.000-50.000"
            },
            "filtro de óleo": {
                "category": "MOTOR",
                "alternatives": ["Filtro original", "Filtro premium"],
                "average_price": "R$ 25-60",
                "brands": ["Mann", "Mahle", "Tecfil", "Bosch"],
                "lifespan_km": "10.000-15.000"
            },
            "correia": {
                "category": "MOTOR",
                "alternatives": ["Correia dentada", "Kit correia + tensionador"],
                "average_price": "R$ 150-450",
                "brands": ["Gates", "Continental", "Dayco"],
                "lifespan_km": "60.000-100.000"
            },
            "disco de freio": {
                "category": "FREIOS",
                "alternatives": ["Disco ventilado", "Disco sólido", "Disco perfurado"],
                "average_price": "R$ 180-450",
                "brands": ["Fremax", "Cobreq", "TRW"],
                "lifespan_km": "60.000-80.000"
            }
        }
        
        # Buscar peça (matching simples)
        part_key = None
        for key in part_suggestions.keys():
            if key.lower() in identified_part.lower():
                part_key = key
                break
        
        if part_key:
            suggestion = part_suggestions[part_key]
            
            # Adicionar contexto do veículo se disponível
            if vehicle_info:
                make = vehicle_info.get('make', '')
                model = vehicle_info.get('model', '')
                year = vehicle_info.get('year', '')
                suggestion['vehicle_specific'] = f"{make} {model} {year}"
            
            logger.info(f"🔍 [Vision] Sugestão de peça: {part_key} - {suggestion['average_price']}")
            
            return {
                "status": "success",
                "part_name": part_key,
                "suggestion": suggestion,
                "message": f"Sugestões encontradas para {part_key}"
            }
        else:
            return {
                "status": "success",
                "part_name": identified_part,
                "message": "Peça identificada, mas sem sugestões específicas no banco de dados",
                "recommendation": "Consultar fornecedor com código da peça"
            }
        
    except Exception as e:
        logger.error(f"❌ [Vision] Erro ao sugerir peça: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def extract_part_code_ocr(image_base64: str) -> Dict[str, Any]:
    """
    Extrai código de peça da imagem usando OCR.
    
    Útil para ler:
    - Códigos gravados em peças
    - Etiquetas de identificação
    - Números de série
    
    Args:
        image_base64: Imagem em formato base64
    
    Returns:
        Códigos extraídos
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Prompt específico para OCR
        ocr_prompt = """
Analise esta imagem e extraia TODOS os códigos, números e textos visíveis.

Procure por:
- Códigos de peça (ex: AB12345, GM-5678)
- Números de série
- Códigos de barras (se visível o número)
- Marca e modelo
- Qualquer texto gravado na peça

Liste cada código encontrado em uma linha separada.
Se não encontrar nenhum código, responda "NENHUM CÓDIGO VISÍVEL".
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ocr_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )
        
        extracted_text = response.choices[0].message.content
        
        # Processar resultado
        if "NENHUM CÓDIGO" in extracted_text.upper():
            codes = []
        else:
            # Extrair códigos (parsing simples)
            codes = [line.strip() for line in extracted_text.split('\n') if line.strip() and not line.startswith('-')]
        
        logger.info(f"🔍 [Vision/OCR] {len(codes)} código(s) extraído(s)")
        
        return {
            "status": "success",
            "codes_found": len(codes),
            "codes": codes,
            "raw_text": extracted_text,
            "message": f"{len(codes)} código(s) encontrado(s)" if codes else "Nenhum código visível na imagem"
        }
        
    except Exception as e:
        logger.error(f"❌ [Vision/OCR] Erro na extração: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def run_vision_agent(action: str, image_base64: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Ponto de entrada principal do Vision Agent.
    
    Args:
        action: Tipo de análise (analyze, detect_damage, suggest_part, extract_code)
        image_base64: Imagem em formato base64
        context: Contexto adicional (tipo de peça, veículo, etc)
    
    Returns:
        Resultado da análise visual
    """
    logger.info(f"👁️ [Vision Agent] Ação: {action}")
    
    try:
        if action == "analyze":
            part_context = context.get('part_context') if context else None
            return analyze_part_image_openai(image_base64, part_context)
        
        elif action == "detect_damage":
            return detect_damage_level(image_base64)
        
        elif action == "suggest_part":
            identified_part = context.get('identified_part', '') if context else ''
            vehicle_info = context.get('vehicle_info') if context else None
            return suggest_replacement_part(identified_part, vehicle_info)
        
        elif action == "extract_code":
            return extract_part_code_ocr(image_base64)
        
        else:
            return {
                "status": "error",
                "error": f"Ação desconhecida: {action}"
            }
    
    except Exception as e:
        logger.error(f"❌ [Vision Agent] Erro: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


# ========================================
# HELPERS
# ========================================

def _extract_field(text: str, field_name: str) -> str:
    """Extrai campo específico do texto de análise."""
    try:
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if field_name in line and ':' in line:
                # Pegar conteúdo após o ':'
                value = line.split(':', 1)[1].strip()
                # Se estiver em asteriscos, remover
                value = value.replace('**', '').strip()
                return value if value else "Não especificado"
        return "Não especificado"
    except:
        return "Não especificado"


def _extract_severity(text: str) -> int:
    """Extrai gravidade (1-5) do texto de análise."""
    try:
        import re
        # Procurar por padrão "Gravidade: X" ou "X/5"
        match = re.search(r'(?:Gravidade|gravidade).*?(\d)/5', text)
        if match:
            return int(match.group(1))
        
        # Tentar outros padrões
        match = re.search(r'(?:Gravidade|gravidade).*?(\d)', text)
        if match:
            return int(match.group(1))
        
        # Se não encontrar, tentar inferir por palavras-chave
        text_lower = text.lower()
        if any(word in text_lower for word in ['crítico', 'perigoso', 'imediato', 'urgente']):
            return 5
        elif any(word in text_lower for word in ['danificado', 'problema', 'defeito']):
            return 4
        elif any(word in text_lower for word in ['desgastado', 'gasto', 'atenção']):
            return 3
        elif any(word in text_lower for word in ['usado', 'normal', 'bom']):
            return 2
        else:
            return 1
    except:
        return 3  # Valor padrão médio

