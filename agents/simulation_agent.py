"""
FASE 10 - Simulation Agent: Modo "Simulação e Cenário" (What-if Analysis)

Funcionalidades:
- Simulação de mudanças de preço
- Análise de impacto de decisões
- Projeção de cenários futuros
- Comparação de alternativas
- Análise de sensibilidade
"""

import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=OPENAI_API_KEY)


def simulate_price_change(current_data: Dict[str, Any], price_change_percent: float) -> Dict[str, Any]:
    """
    Simula impacto de mudança de preço.
    
    Args:
        current_data: Dados atuais (receita, volume, margem)
        price_change_percent: Mudança percentual (+5 = +5%, -10 = -10%)
    
    Returns:
        Projeção de impacto
    """
    try:
        current_revenue = current_data.get('monthly_revenue', 0)
        current_volume = current_data.get('monthly_orders', 0)
        current_avg_ticket = current_data.get('avg_ticket', 0)
        current_margin = current_data.get('profit_margin_percent', 40)
        
        # Calcular novo preço médio
        new_avg_ticket = current_avg_ticket * (1 + price_change_percent / 100)
        
        # Estimar elasticidade de demanda (simplificado)
        # Assumindo elasticidade de -0.8 (para cada 1% de aumento, -0.8% de demanda)
        elasticity = -0.8
        demand_change_percent = price_change_percent * elasticity
        new_volume = int(current_volume * (1 + demand_change_percent / 100))
        
        # Calcular nova receita
        new_revenue = new_avg_ticket * new_volume
        revenue_change = new_revenue - current_revenue
        revenue_change_percent = (revenue_change / current_revenue * 100) if current_revenue > 0 else 0
        
        # Calcular impacto na margem
        # Assumindo que custos fixos permanecem constantes
        cost_ratio = (100 - current_margin) / 100
        current_profit = current_revenue * (current_margin / 100)
        new_profit = new_revenue - (current_revenue * cost_ratio)
        new_margin = (new_profit / new_revenue * 100) if new_revenue > 0 else 0
        
        # Gerar análise
        is_positive = revenue_change > 0
        impact_level = "POSITIVE" if is_positive else "NEGATIVE" if revenue_change < -current_revenue * 0.05 else "NEUTRAL"
        
        recommendation = ""
        if price_change_percent > 0:
            if is_positive:
                recommendation = f"✅ Aumento de {price_change_percent}% é benéfico. Receita aumenta R$ {revenue_change:.2f}"
            else:
                recommendation = f"⚠️ Aumento de {price_change_percent}% reduz receita devido à queda de demanda"
        else:
            if is_positive:
                recommendation = f"✅ Redução de {abs(price_change_percent)}% atrai mais clientes, aumentando receita"
            else:
                recommendation = f"❌ Redução de {abs(price_change_percent)}% reduz receita significativamente"
        
        logger.info(f"💰 [Simulation] Mudança de preço {price_change_percent:+.1f}%: Receita {revenue_change:+.2f} ({impact_level})")
        
        return {
            "status": "success",
            "scenario": "price_change",
            "input": {
                "price_change_percent": price_change_percent,
                "current_avg_ticket": current_avg_ticket,
                "current_monthly_revenue": current_revenue,
                "current_monthly_orders": current_volume
            },
            "projection": {
                "new_avg_ticket": round(new_avg_ticket, 2),
                "new_monthly_orders": new_volume,
                "new_monthly_revenue": round(new_revenue, 2),
                "revenue_change": round(revenue_change, 2),
                "revenue_change_percent": round(revenue_change_percent, 2),
                "new_profit_margin": round(new_margin, 2),
                "profit_change": round(new_profit - current_profit, 2)
            },
            "impact": {
                "level": impact_level,
                "recommendation": recommendation
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [Simulation] Erro na simulação de preço: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def simulate_capacity_change(current_data: Dict[str, Any], additional_technicians: int) -> Dict[str, Any]:
    """
    Simula impacto de adicionar/remover técnicos.
    
    Args:
        current_data: Dados atuais (técnicos, OSs, receita)
        additional_technicians: Número de técnicos a adicionar (+) ou remover (-)
    
    Returns:
        Projeção de impacto
    """
    try:
        current_techs = current_data.get('technician_count', 5)
        monthly_orders = current_data.get('monthly_orders', 100)
        avg_ticket = current_data.get('avg_ticket', 500)
        monthly_revenue = current_data.get('monthly_revenue', 50000)
        tech_cost_monthly = current_data.get('tech_cost_monthly', 3500)
        
        # Capacidade atual
        current_capacity = current_techs * 20  # 20 OSs por técnico/mês
        capacity_usage = (monthly_orders / current_capacity * 100) if current_capacity > 0 else 100
        
        # Nova capacidade
        new_techs = current_techs + additional_technicians
        new_capacity = new_techs * 20
        
        # Estimar nova demanda atendida
        # Se atual está em 100% de capacidade e adicionamos técnico, podemos atender mais
        if capacity_usage >= 90:
            # Com capacidade liberada, podemos atender demanda reprimida
            potential_new_orders = int(current_capacity * 0.3)  # 30% de demanda reprimida estimada
        else:
            potential_new_orders = 0
        
        new_monthly_orders = monthly_orders + potential_new_orders if additional_technicians > 0 else int(monthly_orders * (new_techs / current_techs))
        new_capacity_usage = (new_monthly_orders / new_capacity * 100) if new_capacity > 0 else 0
        
        # Calcular impacto financeiro
        new_monthly_revenue = new_monthly_orders * avg_ticket
        revenue_change = new_monthly_revenue - monthly_revenue
        
        new_tech_costs = new_techs * tech_cost_monthly
        tech_cost_change = new_tech_costs - (current_techs * tech_cost_monthly)
        
        net_impact = revenue_change - tech_cost_change
        roi = (net_impact / abs(tech_cost_change) * 100) if tech_cost_change != 0 else 0
        
        # Análise
        is_beneficial = net_impact > 0
        payback_months = abs(tech_cost_change / revenue_change) if revenue_change > 0 else float('inf')
        
        if additional_technicians > 0:
            if is_beneficial:
                recommendation = f"✅ Contratar {additional_technicians} técnico(s) gera retorno de R$ {net_impact:.2f}/mês"
            else:
                recommendation = f"❌ Contratar {additional_technicians} técnico(s) não é viável no momento (ROI negativo)"
        else:
            if is_beneficial:
                recommendation = f"⚠️ Reduzir {abs(additional_technicians)} técnico(s) economiza R$ {abs(tech_cost_change):.2f}/mês"
            else:
                recommendation = f"❌ Reduzir {abs(additional_technicians)} técnico(s) prejudica receita significativamente"
        
        logger.info(f"👷 [Simulation] Mudança de capacidade {additional_technicians:+d} técnicos: Impacto R$ {net_impact:+.2f}/mês")
        
        return {
            "status": "success",
            "scenario": "capacity_change",
            "input": {
                "additional_technicians": additional_technicians,
                "current_technicians": current_techs,
                "current_capacity_usage": round(capacity_usage, 1)
            },
            "projection": {
                "new_technicians": new_techs,
                "new_capacity": new_capacity,
                "new_monthly_orders": new_monthly_orders,
                "new_capacity_usage": round(new_capacity_usage, 1),
                "new_monthly_revenue": round(new_monthly_revenue, 2),
                "revenue_change": round(revenue_change, 2),
                "tech_cost_change": round(tech_cost_change, 2),
                "net_impact": round(net_impact, 2),
                "roi_percent": round(roi, 1),
                "payback_months": round(payback_months, 1) if payback_months != float('inf') else "N/A"
            },
            "impact": {
                "is_beneficial": is_beneficial,
                "recommendation": recommendation
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [Simulation] Erro na simulação de capacidade: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def simulate_marketing_campaign(current_data: Dict[str, Any], campaign_cost: float, expected_conversion: float) -> Dict[str, Any]:
    """
    Simula ROI de campanha de marketing.
    
    Args:
        current_data: Dados atuais
        campaign_cost: Custo da campanha
        expected_conversion: Taxa de conversão esperada (ex: 0.05 = 5%)
    
    Returns:
        Projeção de ROI
    """
    try:
        monthly_orders = current_data.get('monthly_orders', 100)
        avg_ticket = current_data.get('avg_ticket', 500)
        profit_margin = current_data.get('profit_margin_percent', 40) / 100
        
        # Estimar alcance da campanha
        # Assumindo R$ 10 por lead alcançado
        leads_reached = int(campaign_cost / 10)
        new_clients = int(leads_reached * expected_conversion)
        
        # Assumindo que cada novo cliente gera 1-3 OSs no período
        avg_orders_per_client = 2
        new_orders = new_clients * avg_orders_per_client
        
        # Calcular receita adicional
        additional_revenue = new_orders * avg_ticket
        additional_profit = additional_revenue * profit_margin
        
        # ROI
        net_profit = additional_profit - campaign_cost
        roi = (net_profit / campaign_cost * 100) if campaign_cost > 0 else 0
        
        is_profitable = net_profit > 0
        
        if is_profitable:
            recommendation = f"✅ Campanha viável! ROI de {roi:.1f}% (R$ {net_profit:.2f} de lucro líquido)"
        else:
            recommendation = f"❌ Campanha não viável. Prejuízo de R$ {abs(net_profit):.2f}"
        
        logger.info(f"📢 [Simulation] Campanha R$ {campaign_cost:.2f}: ROI {roi:+.1f}%")
        
        return {
            "status": "success",
            "scenario": "marketing_campaign",
            "input": {
                "campaign_cost": campaign_cost,
                "expected_conversion": expected_conversion
            },
            "projection": {
                "leads_reached": leads_reached,
                "new_clients": new_clients,
                "new_orders": new_orders,
                "additional_revenue": round(additional_revenue, 2),
                "additional_profit": round(additional_profit, 2),
                "net_profit": round(net_profit, 2),
                "roi_percent": round(roi, 1)
            },
            "impact": {
                "is_profitable": is_profitable,
                "recommendation": recommendation
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [Simulation] Erro na simulação de campanha: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def compare_scenarios(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compara múltiplos cenários lado a lado.
    
    Args:
        scenarios: Lista de resultados de simulações
    
    Returns:
        Comparação estruturada
    """
    try:
        if not scenarios or len(scenarios) < 2:
            return {
                "status": "error",
                "error": "É necessário pelo menos 2 cenários para comparar"
            }
        
        # Extrair métricas-chave de cada cenário
        comparison = []
        for i, scenario in enumerate(scenarios, 1):
            if scenario.get('status') != 'success':
                continue
            
            projection = scenario.get('projection', {})
            impact = scenario.get('impact', {})
            
            comparison.append({
                "scenario_number": i,
                "scenario_type": scenario.get('scenario', 'unknown'),
                "revenue_change": projection.get('revenue_change', projection.get('additional_revenue', 0)),
                "net_impact": projection.get('net_impact', projection.get('net_profit', 0)),
                "roi": projection.get('roi_percent', 0),
                "recommendation": impact.get('recommendation', 'N/A')
            })
        
        # Ordenar por impacto líquido
        comparison.sort(key=lambda x: x['net_impact'], reverse=True)
        
        # Identificar melhor cenário
        best_scenario = comparison[0] if comparison else None
        
        logger.info(f"🔄 [Simulation] Comparação de {len(comparison)} cenários concluída")
        
        return {
            "status": "success",
            "comparison": comparison,
            "best_scenario": best_scenario,
            "summary": f"Cenário {best_scenario['scenario_number']} ({best_scenario['scenario_type']}) apresenta melhor resultado"
        }
        
    except Exception as e:
        logger.error(f"❌ [Simulation] Erro na comparação: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def run_simulation_agent(query: str, current_data: Dict[str, Any]) -> str:
    """
    Processa perguntas "E se..." usando LLM + simulações.
    
    Args:
        query: Pergunta do usuário (ex: "E se eu aumentar o preço em 5%?")
        current_data: Dados operacionais atuais
    
    Returns:
        Resposta com análise de cenário
    """
    logger.info(f"🎲 [Simulation Agent] Query: {query}")
    
    try:
        # Detectar tipo de simulação
        query_lower = query.lower()
        
        # Simulação de preço
        if any(word in query_lower for word in ['preço', 'preco', 'valor', 'cobrar']):
            # Extrair porcentagem
            import re
            match = re.search(r'(\d+)%', query)
            if match:
                change_percent = float(match.group(1))
                # Detectar se é aumento ou redução
                if any(word in query_lower for word in ['reduzir', 'diminuir', 'baixar', 'descontar']):
                    change_percent = -change_percent
                
                result = simulate_price_change(current_data, change_percent)
                
                if result['status'] == 'success':
                    proj = result['projection']
                    response = f"""
🎲 **SIMULAÇÃO: Mudança de Preço {change_percent:+.1f}%**

📊 **Projeção:**
• Novo Ticket Médio: R$ {proj['new_avg_ticket']:.2f}
• Nova Receita Mensal: R$ {proj['new_monthly_revenue']:.2f}
• Mudança na Receita: R$ {proj['revenue_change']:+.2f} ({proj['revenue_change_percent']:+.1f}%)
• Nova Margem: {proj['new_profit_margin']:.1f}%

💡 **Recomendação:**
{result['impact']['recommendation']}
"""
                    return response
        
        # Simulação de capacidade
        elif any(word in query_lower for word in ['técnico', 'tecnico', 'contratar', 'funcionário', 'funcionario']):
            # Extrair número de técnicos
            import re
            match = re.search(r'(\d+)', query)
            if match:
                techs = int(match.group(1))
                if any(word in query_lower for word in ['demitir', 'reduzir', 'menos']):
                    techs = -techs
                
                result = simulate_capacity_change(current_data, techs)
                
                if result['status'] == 'success':
                    proj = result['projection']
                    response = f"""
🎲 **SIMULAÇÃO: {techs:+d} Técnico(s)**

📊 **Projeção:**
• Nova Capacidade: {proj['new_capacity']} OSs/mês
• Uso de Capacidade: {proj['new_capacity_usage']:.1f}%
• Nova Receita: R$ {proj['new_monthly_revenue']:.2f}
• Impacto Líquido: R$ {proj['net_impact']:+.2f}/mês
• ROI: {proj['roi_percent']:+.1f}%

💡 **Recomendação:**
{result['impact']['recommendation']}
"""
                    return response
        
        # Usar LLM para análise geral
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
Você é um consultor de negócios especializado em análise de cenários "E se...".

Analise a pergunta do usuário e forneça insights sobre o impacto potencial da mudança proposta.

Use os dados operacionais fornecidos para contextualizar sua resposta.

Seja específico, quantitativo quando possível, e sempre inclua:
1. Impacto esperado
2. Riscos e benefícios
3. Recomendação final
"""),
            ("human", "Pergunta: {query}\n\nDados atuais: {data}")
        ])
        
        chain = prompt | _llm
        result = chain.invoke({"query": query, "data": str(current_data)})
        
        return result.content
        
    except Exception as e:
        logger.error(f"❌ [Simulation Agent] Erro: {str(e)}", exc_info=True)
        return f"Erro ao processar simulação: {str(e)}"

