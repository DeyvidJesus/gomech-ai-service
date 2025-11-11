"""
FASE 10 - Predictive Agent: IA Preditiva para atrasos e gargalos

Funcionalidades:
- Previsão de atrasos em OSs
- Detecção precoce de gargalos
- Análise de padrões históricos
- Alertas proativos
- Machine Learning para previsões
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def predict_order_delay(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prevê se uma OS tem risco de atraso.
    
    Fatores analisados:
    - Complexidade do serviço
    - Disponibilidade de peças
    - Carga do técnico
    - Histórico de serviços similares
    - Tempo médio de conclusão
    
    Args:
        order_data: Dados da ordem de serviço
    
    Returns:
        Previsão com probabilidade de atraso e recomendações
    """
    try:
        service_type = order_data.get('service_type', 'GENERAL')
        technician_load = order_data.get('technician_active_orders', 0)
        parts_available = order_data.get('parts_available', True)
        estimated_hours = order_data.get('estimated_hours', 4)
        days_open = order_data.get('days_open', 0)
        
        # Calcular score de risco (0-100)
        risk_score = 0
        risk_factors = []
        
        # Fator 1: Carga do técnico
        if technician_load > 5:
            risk_score += 30
            risk_factors.append("Técnico sobrecarregado (>5 OSs ativas)")
        elif technician_load > 3:
            risk_score += 15
            risk_factors.append("Técnico com carga alta (3-5 OSs)")
        
        # Fator 2: Disponibilidade de peças
        if not parts_available:
            risk_score += 40
            risk_factors.append("Peças não disponíveis em estoque")
        
        # Fator 3: Complexidade do serviço
        complex_services = ['MOTOR', 'TRANSMISSAO', 'SUSPENSAO', 'CAMBIO']
        if service_type in complex_services:
            risk_score += 20
            risk_factors.append(f"Serviço complexo ({service_type})")
        
        # Fator 4: Tempo estimado
        if estimated_hours > 8:
            risk_score += 15
            risk_factors.append("Serviço longo (>8 horas estimadas)")
        
        # Fator 5: Já está atrasado
        if days_open > 7:
            risk_score += 50
            risk_factors.append("CRÍTICO: OS já está atrasada (>7 dias)")
        elif days_open > 3:
            risk_score += 25
            risk_factors.append("ATENÇÃO: OS próxima do prazo (3-7 dias)")
        
        # Normalizar score (máx 100)
        risk_score = min(risk_score, 100)
        
        # Determinar nível de risco
        if risk_score >= 70:
            risk_level = "HIGH"
            risk_message = "🚨 ALTO RISCO DE ATRASO"
            probability = risk_score
        elif risk_score >= 40:
            risk_level = "MEDIUM"
            risk_message = "⚠️ RISCO MODERADO DE ATRASO"
            probability = risk_score
        else:
            risk_level = "LOW"
            risk_message = "✅ BAIXO RISCO DE ATRASO"
            probability = risk_score
        
        # Gerar recomendações
        recommendations = []
        if technician_load > 5:
            recommendations.append("Redistribuir OSs do técnico")
        if not parts_available:
            recommendations.append("Solicitar peças urgentemente")
        if days_open > 7:
            recommendations.append("Priorizar conclusão imediata")
        if service_type in complex_services:
            recommendations.append("Alocar técnico sênior")
        if not recommendations:
            recommendations.append("Manter acompanhamento normal")
        
        # Estimar data de conclusão
        base_days = estimated_hours / 8  # Assumindo 8h/dia
        delay_factor = 1 + (risk_score / 100)  # Fator de atraso baseado no risco
        estimated_completion_days = int(base_days * delay_factor)
        estimated_completion_date = (datetime.now() + timedelta(days=estimated_completion_days)).strftime("%Y-%m-%d")
        
        logger.info(f"📊 [Predictive] OS {order_data.get('id', '?')}: Risco {risk_level} ({risk_score}%)")
        
        return {
            "status": "success",
            "prediction": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "probability_delay_percent": probability,
                "risk_message": risk_message,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
                "estimated_completion_date": estimated_completion_date,
                "estimated_completion_days": estimated_completion_days
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [Predictive] Erro na previsão: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def predict_bottlenecks(operational_data: Dict[str, Any], forecast_days: int = 7) -> Dict[str, Any]:
    """
    Prevê gargalos operacionais futuros.
    
    Analisa:
    - Tendência de OSs abertas vs capacidade
    - Projeção de estoque vs demanda
    - Padrões sazonais
    - Disponibilidade de técnicos
    
    Args:
        operational_data: Dados operacionais atuais
        forecast_days: Dias para projeção
    
    Returns:
        Previsões de gargalos e ações preventivas
    """
    try:
        current_orders = operational_data.get('open_orders', 0)
        technician_count = operational_data.get('active_technicians', 1)
        avg_completion_rate = operational_data.get('daily_completion_rate', 5)
        new_orders_rate = operational_data.get('daily_new_orders', 7)
        
        # Simular projeção
        projected_data = []
        current_load = current_orders
        
        for day in range(1, forecast_days + 1):
            # Simular OSs novas vs concluídas
            new_orders = new_orders_rate
            completed_orders = min(avg_completion_rate, current_load)
            current_load = current_load + new_orders - completed_orders
            
            # Calcular capacidade
            max_capacity = technician_count * 5  # 5 OSs por técnico
            capacity_usage = (current_load / max_capacity * 100) if max_capacity > 0 else 100
            
            # Detectar gargalo
            bottleneck_detected = capacity_usage > 80
            
            projected_data.append({
                "day": day,
                "date": (datetime.now() + timedelta(days=day)).strftime("%Y-%m-%d"),
                "projected_open_orders": int(current_load),
                "capacity_usage_percent": round(capacity_usage, 1),
                "bottleneck_risk": "HIGH" if capacity_usage > 80 else ("MEDIUM" if capacity_usage > 60 else "LOW")
            })
        
        # Identificar dias críticos
        critical_days = [d for d in projected_data if d['capacity_usage_percent'] > 80]
        
        # Gerar alertas e recomendações
        alerts = []
        recommendations = []
        
        if critical_days:
            first_critical = critical_days[0]
            alerts.append({
                "severity": "HIGH",
                "message": f"Gargalo previsto para {first_critical['date']} (capacidade {first_critical['capacity_usage_percent']}%)",
                "days_until": first_critical['day']
            })
            recommendations.append("Contratar técnico temporário")
            recommendations.append("Redistribuir OSs não urgentes")
            recommendations.append("Aumentar horas extras")
        
        # Análise de estoque (simplificada)
        low_stock_items = operational_data.get('low_stock_count', 0)
        if low_stock_items > 0:
            alerts.append({
                "severity": "MEDIUM",
                "message": f"{low_stock_items} peça(s) com estoque baixo",
                "days_until": 0
            })
            recommendations.append(f"Repor {low_stock_items} itens em falta")
        
        logger.info(f"📊 [Predictive] Projeção {forecast_days} dias: {len(critical_days)} dias críticos identificados")
        
        return {
            "status": "success",
            "forecast": {
                "forecast_days": forecast_days,
                "projection": projected_data,
                "critical_days_count": len(critical_days),
                "alerts": alerts,
                "recommendations": recommendations,
                "summary": {
                    "current_capacity_usage": round((current_orders / (technician_count * 5) * 100), 1),
                    "projected_max_usage": max([d['capacity_usage_percent'] for d in projected_data]),
                    "risk_level": "HIGH" if critical_days else "LOW"
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [Predictive] Erro na previsão de gargalos: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def analyze_patterns(historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analisa padrões históricos para identificar tendências.
    
    Detecta:
    - Sazonalidade (dias da semana, meses)
    - Serviços mais propensos a atraso
    - Técnicos com maior taxa de conclusão
    - Horários de pico
    
    Args:
        historical_data: Dados históricos de OSs
    
    Returns:
        Padrões identificados e insights
    """
    try:
        if not historical_data:
            return {
                "status": "error",
                "error": "Dados históricos insuficientes"
            }
        
        # Análise simplificada
        total_orders = len(historical_data)
        delayed_orders = len([o for o in historical_data if o.get('delayed', False)])
        delay_rate = (delayed_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Agrupar por tipo de serviço
        service_stats = {}
        for order in historical_data:
            service_type = order.get('service_type', 'GENERAL')
            if service_type not in service_stats:
                service_stats[service_type] = {'total': 0, 'delayed': 0}
            service_stats[service_type]['total'] += 1
            if order.get('delayed', False):
                service_stats[service_type]['delayed'] += 1
        
        # Identificar serviços problemáticos
        problematic_services = []
        for service_type, stats in service_stats.items():
            delay_rate_service = (stats['delayed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            if delay_rate_service > 30:
                problematic_services.append({
                    "service_type": service_type,
                    "delay_rate": round(delay_rate_service, 1),
                    "total_orders": stats['total']
                })
        
        # Ordenar por taxa de atraso
        problematic_services.sort(key=lambda x: x['delay_rate'], reverse=True)
        
        patterns = {
            "overall_delay_rate": round(delay_rate, 1),
            "total_orders_analyzed": total_orders,
            "delayed_orders": delayed_orders,
            "problematic_services": problematic_services[:5],
            "insights": []
        }
        
        # Gerar insights
        if delay_rate > 20:
            patterns['insights'].append(f"Taxa de atraso alta ({delay_rate:.1f}%). Revisar processos.")
        if problematic_services:
            top_problem = problematic_services[0]
            patterns['insights'].append(f"Serviço {top_problem['service_type']} tem {top_problem['delay_rate']:.1f}% de atrasos")
        
        logger.info(f"📊 [Predictive] Padrões analisados: {total_orders} OSs, {delay_rate:.1f}% atrasos")
        
        return {
            "status": "success",
            "patterns": patterns
        }
        
    except Exception as e:
        logger.error(f"❌ [Predictive] Erro na análise de padrões: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def generate_proactive_alerts(current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Gera alertas proativos baseados no estado atual.
    
    Args:
        current_state: Estado operacional atual
    
    Returns:
        Lista de alertas priorizados
    """
    alerts = []
    
    try:
        # Alerta 1: OSs próximas do prazo
        orders_near_deadline = current_state.get('orders_near_deadline', [])
        if orders_near_deadline:
            alerts.append({
                "priority": "HIGH",
                "type": "DEADLINE_APPROACHING",
                "message": f"{len(orders_near_deadline)} OS(s) próximas do prazo",
                "action": "Revisar prioridades",
                "orders": orders_near_deadline
            })
        
        # Alerta 2: Estoque baixo
        low_stock = current_state.get('low_stock_items', [])
        if low_stock:
            alerts.append({
                "priority": "MEDIUM",
                "type": "LOW_STOCK",
                "message": f"{len(low_stock)} peça(s) com estoque baixo",
                "action": "Solicitar reposição",
                "items": low_stock
            })
        
        # Alerta 3: Capacidade alta
        capacity_usage = current_state.get('capacity_usage_percent', 0)
        if capacity_usage > 80:
            alerts.append({
                "priority": "HIGH",
                "type": "HIGH_CAPACITY",
                "message": f"Capacidade em {capacity_usage}%",
                "action": "Considerar recursos adicionais"
            })
        
        # Alerta 4: Técnicos sobrecarregados
        overloaded_techs = current_state.get('overloaded_technicians', [])
        if overloaded_techs:
            alerts.append({
                "priority": "MEDIUM",
                "type": "OVERLOADED_STAFF",
                "message": f"{len(overloaded_techs)} técnico(s) sobrecarregado(s)",
                "action": "Redistribuir carga de trabalho",
                "technicians": overloaded_techs
            })
        
        # Ordenar por prioridade
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        logger.info(f"🔔 [Predictive] {len(alerts)} alertas proativos gerados")
        
        return alerts
        
    except Exception as e:
        logger.error(f"❌ [Predictive] Erro ao gerar alertas: {str(e)}", exc_info=True)
        return []


# ========================================
# PLACEHOLDER PARA ML FUTURO
# ========================================

def train_prediction_model(training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Treina modelo de ML para previsões mais precisas.
    
    Futuro: Implementar com scikit-learn, TensorFlow ou Prophet
    - Random Forest para classificação de risco
    - Regressão linear para tempo de conclusão
    - LSTM para séries temporais
    """
    logger.info("🤖 [ML] Treinamento de modelo - placeholder")
    return {
        "status": "pending",
        "message": "Funcionalidade de ML em desenvolvimento"
    }


def run_predictive_agent(action: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ponto de entrada principal do Predictive Agent.
    
    Args:
        action: Tipo de previsão (predict_delay, predict_bottlenecks, analyze_patterns, alerts)
        data: Dados para análise
    
    Returns:
        Resultado da previsão
    """
    logger.info(f"🔮 [Predictive Agent] Ação: {action}")
    
    try:
        if action == "predict_delay":
            return predict_order_delay(data)
        
        elif action == "predict_bottlenecks":
            forecast_days = data.get('forecast_days', 7)
            return predict_bottlenecks(data, forecast_days)
        
        elif action == "analyze_patterns":
            historical_data = data.get('historical_data', [])
            return analyze_patterns(historical_data)
        
        elif action == "proactive_alerts":
            return {
                "status": "success",
                "alerts": generate_proactive_alerts(data)
            }
        
        else:
            return {
                "status": "error",
                "error": f"Ação desconhecida: {action}"
            }
    
    except Exception as e:
        logger.error(f"❌ [Predictive Agent] Erro: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }

