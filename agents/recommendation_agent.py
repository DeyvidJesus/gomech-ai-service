import os
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
from datetime import datetime
import io
import csv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=OPENAI_API_KEY)


# ========================================
# FASE 9: FUNÇÕES DE GESTÃO E ESTRATÉGIA
# ========================================

def calculate_service_profitability(service_orders: List[Dict]) -> Dict[str, Any]:
    """
    Calcula rentabilidade por tipo de serviço.
    
    Retorna:
    - Margem de lucro por serviço
    - Custos diretos vs receita
    - Serviços mais lucrativos
    - Recomendações de precificação
    """
    profitability = {}
    service_types = {}
    
    for order in service_orders:
        service_type = order.get('service_type', 'GENERAL')
        total = order.get('total_value', 0)
        labor_cost = order.get('labor_cost', 0)
        parts_cost = order.get('parts_cost', 0)
        
        if service_type not in service_types:
            service_types[service_type] = {
                'count': 0,
                'total_revenue': 0,
                'total_costs': 0,
                'total_labor_cost': 0,
                'total_parts_cost': 0
            }
        
        service_types[service_type]['count'] += 1
        service_types[service_type]['total_revenue'] += total
        service_types[service_type]['total_costs'] += (labor_cost + parts_cost)
        service_types[service_type]['total_labor_cost'] += labor_cost
        service_types[service_type]['total_parts_cost'] += parts_cost
    
    # Calcular métricas de rentabilidade
    rankings = []
    for service_type, data in service_types.items():
        revenue = data['total_revenue']
        costs = data['total_costs']
        profit = revenue - costs
        margin = (profit / revenue * 100) if revenue > 0 else 0
        avg_revenue = revenue / data['count'] if data['count'] > 0 else 0
        avg_profit = profit / data['count'] if data['count'] > 0 else 0
        
        rankings.append({
            'service_type': service_type,
            'count': data['count'],
            'total_revenue': revenue,
            'total_costs': costs,
            'total_profit': profit,
            'margin_percent': margin,
            'avg_revenue_per_service': avg_revenue,
            'avg_profit_per_service': avg_profit,
            'labor_cost': data['total_labor_cost'],
            'parts_cost': data['total_parts_cost']
        })
    
    # Ordenar por margem de lucro
    rankings.sort(key=lambda x: x['margin_percent'], reverse=True)
    
    return {
        'service_profitability': rankings,
        'top_profitable': rankings[0] if rankings else None,
        'least_profitable': rankings[-1] if rankings else None,
        'total_services_analyzed': sum(s['count'] for s in rankings),
        'overall_margin': sum(s['total_profit'] for s in rankings) / sum(s['total_revenue'] for s in rankings) * 100 if rankings else 0
    }


def identify_operational_bottlenecks(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identifica gargalos operacionais.
    
    Analisa:
    - Tempo médio de execução por serviço
    - Técnicos sobrecarregados
    - Peças em falta
    - OSs atrasadas
    - Filas de espera
    """
    bottlenecks = {
        'critical': [],
        'warnings': [],
        'opportunities': [],
        'overall_health_score': 100  # Começa com 100 e deduz por problema
    }
    
    # Análise de tempo de serviço
    if 'service_orders' in data:
        orders = data['service_orders']
        
        # OSs pendentes há muito tempo
        long_pending = [o for o in orders if o.get('status') in ['PENDING', 'IN_PROGRESS'] and o.get('days_open', 0) > 7]
        if long_pending:
            count = len(long_pending)
            bottlenecks['critical'].append({
                'type': 'delayed_orders',
                'severity': 'HIGH',
                'count': count,
                'description': f'{count} OSs pendentes há mais de 7 dias',
                'impact': 'Insatisfação do cliente e perda de receita',
                'recommendation': 'Priorizar conclusão de OSs antigas e revisar capacidade da equipe'
            })
            bottlenecks['overall_health_score'] -= 15
        
        # Análise de capacidade
        in_progress = [o for o in orders if o.get('status') == 'IN_PROGRESS']
        if len(in_progress) > 15:
            bottlenecks['warnings'].append({
                'type': 'capacity_issue',
                'severity': 'MEDIUM',
                'count': len(in_progress),
                'description': f'{len(in_progress)} OSs em andamento simultaneamente',
                'impact': 'Possível sobrecarga da equipe',
                'recommendation': 'Considerar contratação temporária ou redistribuição de trabalho'
            })
            bottlenecks['overall_health_score'] -= 10
    
    # Análise de técnicos
    if 'technicians' in data:
        techs = data['technicians']
        overloaded = [t for t in techs if t.get('active_orders', 0) > 5]
        
        if overloaded:
            bottlenecks['critical'].append({
                'type': 'overloaded_technicians',
                'severity': 'HIGH',
                'count': len(overloaded),
                'description': f'{len(overloaded)} técnico(s) com mais de 5 OSs ativas',
                'impact': 'Risco de erros e atrasos',
                'recommendation': 'Redistribuir OSs e revisar balanceamento de carga'
            })
            bottlenecks['overall_health_score'] -= 15
        
        # Técnicos ociosos
        idle = [t for t in techs if t.get('active_orders', 0) == 0 and t.get('status') == 'ACTIVE']
        if idle and not overloaded:
            bottlenecks['opportunities'].append({
                'type': 'idle_capacity',
                'severity': 'LOW',
                'count': len(idle),
                'description': f'{len(idle)} técnico(s) disponível(is)',
                'impact': 'Capacidade ociosa',
                'recommendation': 'Alocar novos serviços ou realizar manutenções preventivas'
            })
    
    # Análise de estoque
    if 'inventory' in data:
        items = data['inventory']
        out_of_stock = [i for i in items if i.get('quantity', 0) <= i.get('min_quantity', 0)]
        
        if out_of_stock:
            bottlenecks['critical'].append({
                'type': 'stock_shortage',
                'severity': 'HIGH',
                'count': len(out_of_stock),
                'description': f'{len(out_of_stock)} peça(s) em falta ou abaixo do mínimo',
                'impact': 'Atrasos em serviços por falta de peças',
                'recommendation': 'Reposição urgente de estoque e revisão de pontos de reposição'
            })
            bottlenecks['overall_health_score'] -= 20
        
        # Itens parados há muito tempo
        slow_moving = [i for i in items if i.get('last_movement_days', 0) > 180]
        if slow_moving:
            bottlenecks['warnings'].append({
                'type': 'slow_inventory',
                'severity': 'MEDIUM',
                'count': len(slow_moving),
                'description': f'{len(slow_moving)} peça(s) sem movimentação há mais de 6 meses',
                'impact': 'Capital parado e possível obsolescência',
                'recommendation': 'Promover liquidação ou devolver ao fornecedor'
            })
            bottlenecks['overall_health_score'] -= 5
    
    # Determinar status geral
    if bottlenecks['overall_health_score'] >= 80:
        bottlenecks['status'] = 'HEALTHY'
        bottlenecks['status_message'] = '✅ Operação saudável'
    elif bottlenecks['overall_health_score'] >= 60:
        bottlenecks['status'] = 'WARNING'
        bottlenecks['status_message'] = '⚠️ Alguns pontos de atenção'
    else:
        bottlenecks['status'] = 'CRITICAL'
        bottlenecks['status_message'] = '🚨 Gargalos críticos identificados'
    
    return bottlenecks


def internal_benchmark(organizations_data: List[Dict]) -> Dict[str, Any]:
    """
    Realiza benchmark interno entre oficinas (multi-tenant).
    
    Compara:
    - Faturamento médio
    - Ticket médio
    - Taxa de conversão
    - Satisfação do cliente
    - Produtividade
    """
    if not organizations_data or len(organizations_data) < 2:
        return {
            'error': 'É necessário dados de pelo menos 2 organizações para benchmark',
            'available_orgs': len(organizations_data) if organizations_data else 0
        }
    
    benchmarks = []
    
    for org in organizations_data:
        org_id = org.get('organization_id')
        org_name = org.get('organization_name', f'Org {org_id}')
        
        metrics = {
            'organization_id': org_id,
            'organization_name': org_name,
            'monthly_revenue': org.get('monthly_revenue', 0),
            'avg_ticket': org.get('avg_ticket', 0),
            'completed_orders': org.get('completed_orders', 0),
            'avg_completion_time_days': org.get('avg_completion_time_days', 0),
            'client_satisfaction': org.get('avg_nps', 0),
            'technician_count': org.get('technician_count', 1),
            'revenue_per_technician': org.get('monthly_revenue', 0) / max(org.get('technician_count', 1), 1),
            'orders_per_technician': org.get('completed_orders', 0) / max(org.get('technician_count', 1), 1)
        }
        benchmarks.append(metrics)
    
    # Calcular médias e rankings
    avg_revenue = sum(b['monthly_revenue'] for b in benchmarks) / len(benchmarks)
    avg_ticket = sum(b['avg_ticket'] for b in benchmarks) / len(benchmarks)
    avg_satisfaction = sum(b['client_satisfaction'] for b in benchmarks) / len(benchmarks)
    avg_orders = sum(b['completed_orders'] for b in benchmarks) / len(benchmarks)
    
    # Ranquear por diferentes métricas
    revenue_ranking = sorted(benchmarks, key=lambda x: x['monthly_revenue'], reverse=True)
    ticket_ranking = sorted(benchmarks, key=lambda x: x['avg_ticket'], reverse=True)
    satisfaction_ranking = sorted(benchmarks, key=lambda x: x['client_satisfaction'], reverse=True)
    productivity_ranking = sorted(benchmarks, key=lambda x: x['orders_per_technician'], reverse=True)
    
    # Identificar líderes e oportunidades
    return {
        'summary': {
            'total_organizations': len(benchmarks),
            'avg_monthly_revenue': avg_revenue,
            'avg_ticket': avg_ticket,
            'avg_satisfaction': avg_satisfaction,
            'avg_orders_per_month': avg_orders
        },
        'rankings': {
            'by_revenue': [{'rank': i+1, **org} for i, org in enumerate(revenue_ranking)],
            'by_ticket': [{'rank': i+1, **org} for i, org in enumerate(ticket_ranking)],
            'by_satisfaction': [{'rank': i+1, **org} for i, org in enumerate(satisfaction_ranking)],
            'by_productivity': [{'rank': i+1, **org} for i, org in enumerate(productivity_ranking)]
        },
        'leaders': {
            'highest_revenue': revenue_ranking[0],
            'highest_ticket': ticket_ranking[0],
            'highest_satisfaction': satisfaction_ranking[0],
            'most_productive': productivity_ranking[0]
        },
        'insights': _generate_benchmark_insights(benchmarks, avg_revenue, avg_ticket, avg_satisfaction)
    }


def _generate_benchmark_insights(benchmarks: List[Dict], avg_revenue: float, avg_ticket: float, avg_satisfaction: float) -> List[str]:
    """Gera insights baseados no benchmark interno."""
    insights = []
    
    # Análise de dispersão de faturamento
    revenues = [b['monthly_revenue'] for b in benchmarks]
    max_revenue = max(revenues)
    min_revenue = min(revenues)
    gap = max_revenue - min_revenue
    
    if gap > avg_revenue * 0.5:  # Se há mais de 50% de diferença
        insights.append(f"💡 Há grande variação no faturamento (R$ {gap:.2f} de diferença). Oficinas com menor desempenho podem aprender com as líderes.")
    
    # Análise de ticket médio
    tickets = [b['avg_ticket'] for b in benchmarks]
    max_ticket = max(tickets)
    min_ticket = min(tickets)
    
    if max_ticket > min_ticket * 1.3:  # Se diferença > 30%
        insights.append(f"🎯 Ticket médio varia de R$ {min_ticket:.2f} a R$ {max_ticket:.2f}. Oficinas com menor ticket podem revisar precificação.")
    
    # Análise de satisfação
    satisfactions = [b['client_satisfaction'] for b in benchmarks]
    low_satisfaction = [b for b in benchmarks if b['client_satisfaction'] < avg_satisfaction * 0.9]
    
    if low_satisfaction:
        insights.append(f"⚠️ {len(low_satisfaction)} oficina(s) com satisfação abaixo da média. Investir em qualidade do atendimento.")
    
    # Análise de produtividade
    productivities = [b['orders_per_technician'] for b in benchmarks]
    avg_prod = sum(productivities) / len(productivities)
    low_prod = [b for b in benchmarks if b['orders_per_technician'] < avg_prod * 0.8]
    
    if low_prod:
        insights.append(f"📊 {len(low_prod)} oficina(s) com produtividade abaixo da média. Revisar processos e distribuição de trabalho.")
    
    return insights


def generate_management_report(report_type: str, data: Dict[str, Any], format: str = 'json') -> Any:
    """
    Gera relatórios agregados para gestão.
    
    Tipos de relatório:
    - 'profitability': Rentabilidade por serviço
    - 'bottlenecks': Gargalos operacionais
    - 'benchmark': Comparativo entre oficinas
    - 'executive': Resumo executivo completo
    
    Formatos:
    - 'json': Estrutura JSON
    - 'csv': CSV para exportação
    - 'text': Texto formatado
    """
    logger.info(f"📊 Gerando relatório: {report_type} (formato: {format})")
    
    if report_type == 'profitability':
        service_orders = data.get('service_orders', [])
        result = calculate_service_profitability(service_orders)
        
        if format == 'csv':
            return _convert_to_csv(result['service_profitability'], [
                'service_type', 'count', 'total_revenue', 'total_costs', 
                'total_profit', 'margin_percent', 'avg_revenue_per_service', 'avg_profit_per_service'
            ])
        elif format == 'text':
            return _format_profitability_text(result)
        else:
            return result
    
    elif report_type == 'bottlenecks':
        result = identify_operational_bottlenecks(data)
        
        if format == 'text':
            return _format_bottlenecks_text(result)
        else:
            return result
    
    elif report_type == 'benchmark':
        organizations = data.get('organizations', [])
        result = internal_benchmark(organizations)
        
        if format == 'csv':
            return _convert_to_csv(result['rankings']['by_revenue'], [
                'rank', 'organization_name', 'monthly_revenue', 'avg_ticket', 
                'client_satisfaction', 'orders_per_technician'
            ])
        elif format == 'text':
            return _format_benchmark_text(result)
        else:
            return result
    
    elif report_type == 'executive':
        # Relatório executivo completo
        executive_summary = {
            'report_date': datetime.now().isoformat(),
            'report_type': 'executive_summary',
            'sections': {}
        }
        
        # Adicionar seções se dados disponíveis
        if 'service_orders' in data:
            executive_summary['sections']['profitability'] = calculate_service_profitability(data['service_orders'])
        
        executive_summary['sections']['operational_health'] = identify_operational_bottlenecks(data)
        
        if 'organizations' in data and len(data['organizations']) >= 2:
            executive_summary['sections']['benchmark'] = internal_benchmark(data['organizations'])
        
        if format == 'text':
            return _format_executive_text(executive_summary)
        else:
            return executive_summary
    
    else:
        return {'error': f'Tipo de relatório desconhecido: {report_type}'}


def _convert_to_csv(data: List[Dict], columns: List[str]) -> str:
    """Converte lista de dicionários para CSV."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def _format_profitability_text(result: Dict) -> str:
    """Formata relatório de rentabilidade em texto."""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 RELATÓRIO DE RENTABILIDADE POR SERVIÇO")
    lines.append("=" * 60)
    lines.append(f"\nTotal de serviços analisados: {result['total_services_analyzed']}")
    lines.append(f"Margem geral: {result['overall_margin']:.2f}%\n")
    
    lines.append("\n🏆 SERVIÇOS MAIS RENTÁVEIS:")
    for i, service in enumerate(result['service_profitability'][:5], 1):
        lines.append(f"\n{i}. {service['service_type']}")
        lines.append(f"   Quantidade: {service['count']} serviços")
        lines.append(f"   Receita Total: R$ {service['total_revenue']:.2f}")
        lines.append(f"   Custo Total: R$ {service['total_costs']:.2f}")
        lines.append(f"   Lucro Total: R$ {service['total_profit']:.2f}")
        lines.append(f"   Margem: {service['margin_percent']:.2f}%")
        lines.append(f"   Lucro Médio por Serviço: R$ {service['avg_profit_per_service']:.2f}")
    
    return "\n".join(lines)


def _format_bottlenecks_text(result: Dict) -> str:
    """Formata relatório de gargalos em texto."""
    lines = []
    lines.append("=" * 60)
    lines.append("🔍 ANÁLISE DE GARGALOS OPERACIONAIS")
    lines.append("=" * 60)
    lines.append(f"\nStatus: {result['status_message']}")
    lines.append(f"Score de Saúde: {result['overall_health_score']}/100\n")
    
    if result['critical']:
        lines.append("\n🚨 PROBLEMAS CRÍTICOS:")
        for issue in result['critical']:
            lines.append(f"\n• {issue['description']}")
            lines.append(f"  Impacto: {issue['impact']}")
            lines.append(f"  Recomendação: {issue['recommendation']}")
    
    if result['warnings']:
        lines.append("\n⚠️ PONTOS DE ATENÇÃO:")
        for issue in result['warnings']:
            lines.append(f"\n• {issue['description']}")
            lines.append(f"  Impacto: {issue['impact']}")
            lines.append(f"  Recomendação: {issue['recommendation']}")
    
    if result['opportunities']:
        lines.append("\n💡 OPORTUNIDADES:")
        for opp in result['opportunities']:
            lines.append(f"\n• {opp['description']}")
            lines.append(f"  Recomendação: {opp['recommendation']}")
    
    return "\n".join(lines)


def _format_benchmark_text(result: Dict) -> str:
    """Formata relatório de benchmark em texto."""
    lines = []
    lines.append("=" * 60)
    lines.append("📈 BENCHMARK INTERNO ENTRE OFICINAS")
    lines.append("=" * 60)
    lines.append(f"\nTotal de organizações: {result['summary']['total_organizations']}")
    lines.append(f"Faturamento médio: R$ {result['summary']['avg_monthly_revenue']:.2f}")
    lines.append(f"Ticket médio: R$ {result['summary']['avg_ticket']:.2f}")
    lines.append(f"Satisfação média: {result['summary']['avg_satisfaction']:.1f}\n")
    
    lines.append("\n🏆 LÍDERES:")
    lines.append(f"\n• Maior Faturamento: {result['leaders']['highest_revenue']['organization_name']}")
    lines.append(f"  R$ {result['leaders']['highest_revenue']['monthly_revenue']:.2f}/mês")
    
    lines.append(f"\n• Maior Ticket Médio: {result['leaders']['highest_ticket']['organization_name']}")
    lines.append(f"  R$ {result['leaders']['highest_ticket']['avg_ticket']:.2f}")
    
    lines.append(f"\n• Maior Satisfação: {result['leaders']['highest_satisfaction']['organization_name']}")
    lines.append(f"  {result['leaders']['highest_satisfaction']['client_satisfaction']:.1f} pontos")
    
    lines.append(f"\n• Mais Produtiva: {result['leaders']['most_productive']['organization_name']}")
    lines.append(f"  {result['leaders']['most_productive']['orders_per_technician']:.1f} OSs/técnico")
    
    if result['insights']:
        lines.append("\n\n💡 INSIGHTS:")
        for insight in result['insights']:
            lines.append(f"• {insight}")
    
    return "\n".join(lines)


def _format_executive_text(summary: Dict) -> str:
    """Formata relatório executivo completo em texto."""
    lines = []
    lines.append("=" * 70)
    lines.append("📊 RELATÓRIO EXECUTIVO - GESTÃO ESTRATÉGICA")
    lines.append("=" * 70)
    lines.append(f"\nData do Relatório: {summary['report_date']}\n")
    
    for section_name, section_data in summary['sections'].items():
        if section_name == 'profitability':
            lines.append(_format_profitability_text(section_data))
        elif section_name == 'operational_health':
            lines.append(_format_bottlenecks_text(section_data))
        elif section_name == 'benchmark':
            lines.append(_format_benchmark_text(section_data))
        lines.append("\n")
    
    return "\n".join(lines)


# ========================================
# FIM DAS FUNÇÕES DE GESTÃO E ESTRATÉGIA
# ========================================


def _analyze_operational_data(stats: dict) -> str:
    """
    Analisa dados operacionais e gera insights estruturados.
    
    Usa lógica simples para identificar padrões e oportunidades.
    """
    insights = []
    
    # Análise de OSs hoje
    if 'os_today' in stats:
        os_data = stats['os_today']
        if os_data['count'] == 0:
            insights.append("⚠️ **Alerta**: Nenhuma OS concluída hoje. Verifique o andamento dos trabalhos.")
        elif os_data['count'] >= 5:
            insights.append(f"✅ **Ótimo desempenho**: {os_data['count']} OSs concluídas hoje, gerando R$ {os_data['revenue']:.2f}")
    
    # Análise de ticket médio
    if 'monthly_ticket' in stats:
        ticket_data = stats['monthly_ticket']
        avg = ticket_data['avg_ticket']
        
        if avg < 300:
            insights.append(f"💡 **Oportunidade**: Ticket médio de R$ {avg:.2f} está baixo. Considere:")
            insights.append("   • Oferecer serviços adicionais (revisão completa, limpeza)")
            insights.append("   • Revisar markup das peças (ideal: 30-50%)")
            insights.append("   • Sugerir manutenções preventivas")
            # Previsão simples: aumento de 10% no ticket médio
            new_avg = avg * 1.10
            revenue_increase = (new_avg - avg) * ticket_data['count']
            insights.append(f"   📈 **Projeção**: Aumentando ticket médio em 10% → +R$ {revenue_increase:.2f}/mês")
        elif avg > 800:
            insights.append(f"🌟 **Excelente**: Ticket médio de R$ {avg:.2f} está ótimo!")
        else:
            insights.append(f"📊 Ticket médio atual: R$ {avg:.2f}")
    
    # Análise de clientes recorrentes
    if 'recurrent_clients' in stats:
        rec_data = stats['recurrent_clients']
        if rec_data['count'] > 0:
            recurrence_rate = (rec_data['total_orders'] / rec_data['count']) if rec_data['count'] > 0 else 0
            insights.append(f"🔄 **Fidelização**: {rec_data['count']} clientes recorrentes (média de {recurrence_rate:.1f} OSs cada)")
            
            if recurrence_rate < 2.5:
                insights.append("💡 **Sugestão**: Para aumentar recorrência:")
                insights.append("   • Implementar programa de fidelidade")
                insights.append("   • Enviar lembretes de revisão por WhatsApp")
                insights.append("   • Oferecer desconto na 3ª OS")
    
    # Análise de peças mais usadas
    if 'top_parts' in stats and len(stats['top_parts']) > 0:
        top_part = stats['top_parts'][0]
        insights.append(f"🔧 **Peça mais usada**: {top_part['name']} ({top_part['usage_count']} vezes)")
        insights.append("   💡 Mantenha estoque adequado desta peça para evitar rupturas")
    
    # Análise de status de OSs
    if 'os_status' in stats:
        status_data = stats['os_status']
        pending = status_data.get('PENDING', 0)
        in_progress = status_data.get('IN_PROGRESS', 0)
        
        total_open = pending + in_progress
        if total_open > 20:
            insights.append(f"⚠️ **Atenção**: {total_open} OSs em aberto ({pending} pendentes, {in_progress} em andamento)")
            insights.append("   • Considere priorizar as mais antigas")
            insights.append("   • Verifique se há gargalos na equipe")
    
    return "\n".join(insights) if insights else "📊 Dados operacionais dentro da normalidade."


def _generate_predictions(stats: dict) -> str:
    """
    Gera previsões simples baseadas em dados históricos.
    
    Usa regressão linear simples para projetar tendências.
    """
    predictions = []
    
    # Previsão de faturamento
    if 'monthly_ticket' in stats:
        monthly_data = stats['monthly_ticket']
        current_revenue = monthly_data['total_revenue']
        avg_ticket = monthly_data['avg_ticket']
        os_count = monthly_data['count']
        
        if os_count > 0:
            # Projeção para o próximo mês (assumindo crescimento de 5%)
            projected_os = int(os_count * 1.05)
            projected_revenue = projected_os * avg_ticket
            growth = projected_revenue - current_revenue
            
            predictions.append("📈 **Projeção para próximo mês:**")
            predictions.append(f"   • OSs estimadas: {projected_os} (crescimento de 5%)")
            predictions.append(f"   • Faturamento projetado: R$ {projected_revenue:.2f}")
            predictions.append(f"   • Crescimento esperado: +R$ {growth:.2f} ({(growth/current_revenue*100):.1f}%)")
    
    # Previsão de demanda de peças
    if 'top_parts' in stats and len(stats['top_parts']) > 0:
        predictions.append("\n🔧 **Previsão de demanda de peças (próximo mês):**")
        for part in stats['top_parts'][:3]:
            # Projeção simples: mesma taxa de uso
            projected_qty = int(part['quantity'] * 1.1)  # +10% de margem
            predictions.append(f"   • {part['name']}: ~{projected_qty} unidades")
    
    return "\n".join(predictions) if predictions else ""

_recommendation_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Você é um consultor de negócios especializado em oficinas mecânicas.

💡 **SUAS CAPACIDADES:**
1. Sugerir melhorias operacionais
2. Dar insights sobre gestão de estoque
3. Recomendar otimizações de processos
4. Prever tendências e necessidades
5. Propor ações para aumentar receita/reduzir custos

🔧 **CONTEXTO DA OFICINA MECÂNICA:**
- Gerencia ordens de serviço, clientes, veículos e estoque
- Precisa otimizar giro de estoque
- Busca aumentar produtividade dos técnicos
- Quer melhorar satisfação dos clientes
- Necessita controlar custos e margens

📊 **TIPOS DE RECOMENDAÇÕES:**
- **Estoque**: Peças com baixo giro, estoque mínimo ideal, compras estratégicas
- **Operacional**: Agilizar processos, reduzir tempo de atendimento
- **Comercial**: Upselling, serviços complementares, fidelização
- **Financeiro**: Markup ideal, controle de custos, análise de margem
- **Equipe**: Distribuição de trabalho, treinamentos, produtividade

💬 **COMO RESPONDER:**
- Seja prático e objetivo
- Sugira ações concretas e implementáveis
- Use dados e métricas quando possível
- Explique o "porquê" das recomendações
- Priorize impacto vs esforço

🎯 **EXEMPLOS DE INSIGHTS:**
- "Para melhorar o giro de estoque, analise peças paradas há mais de 6 meses"
- "Técnicos com muitas OSs pendentes podem precisar de redistribuição"
- "Oferecer pacotes de revisão pode aumentar a recorrência de clientes"
- "Markup abaixo de 30% pode comprometer a margem de lucro"

Seja consultivo, empático e focado em resultados práticos! 🚀
"""),
    ("human", "{question}")
])

def run_recommendation_agent(question: str, stats: Optional[dict] = None, action: str = 'analyze') -> str:
    """
    Agente de recomendações e insights (FASE 9: Gestão Estratégica).
    
    Fornece:
    - Sugestões de melhorias baseadas em dados reais
    - Insights de negócio com estatísticas
    - Previsões e tendências
    - Otimizações de processos
    - Ações estratégicas
    - Rentabilidade por serviço
    - Identificação de gargalos operacionais
    - Benchmark interno entre oficinas
    - Relatórios gerenciais (JSON/CSV/Texto)
    
    Args:
        question: Pergunta do usuário
        stats: Estatísticas operacionais (opcional)
        action: Tipo de análise ('analyze', 'profitability', 'bottlenecks', 'benchmark', 'report')
    """
    logger.info(f"💡 [Recommendation Agent] Pergunta: {question} | Action: {action}")
    
    try:
        # ============================================
        # FASE 9: COMANDOS GERENCIAIS ESPECÍFICOS
        # ============================================
        
        question_lower = question.lower()
        
        # Comando: "Me mostre os serviços com maior margem"
        if any(keyword in question_lower for keyword in ['maior margem', 'mais lucrativ', 'rentabilidade', 'margem de lucro']):
            if stats and 'service_orders' in stats:
                profitability = calculate_service_profitability(stats['service_orders'])
                
                response = "📊 **ANÁLISE DE RENTABILIDADE POR SERVIÇO**\n\n"
                
                if profitability['top_profitable']:
                    top = profitability['top_profitable']
                    response += f"🏆 **Serviço Mais Lucrativo:** {top['service_type']}\n"
                    response += f"   • Margem: {top['margin_percent']:.2f}%\n"
                    response += f"   • Lucro Total: R$ {top['total_profit']:.2f}\n"
                    response += f"   • Receita Total: R$ {top['total_revenue']:.2f}\n"
                    response += f"   • Quantidade: {top['count']} serviços\n\n"
                
                response += "📈 **TOP 5 SERVIÇOS POR MARGEM:**\n\n"
                for i, service in enumerate(profitability['service_profitability'][:5], 1):
                    response += f"{i}. **{service['service_type']}**\n"
                    response += f"   • Margem: {service['margin_percent']:.2f}%\n"
                    response += f"   • Lucro Médio: R$ {service['avg_profit_per_service']:.2f}\n"
                    response += f"   • Quantidade: {service['count']} serviços\n\n"
                
                response += f"\n💡 **Margem Geral:** {profitability['overall_margin']:.2f}%\n"
                response += f"📊 **Total Analisado:** {profitability['total_services_analyzed']} serviços"
                
                return response
            else:
                return "📊 Para analisar rentabilidade, preciso de dados de ordens de serviço. Por favor, forneça os dados necessários."
        
        # Comando: "Identifique gargalos" ou "problemas operacionais"
        if any(keyword in question_lower for keyword in ['gargalo', 'problema operacional', 'bottleneck', 'atraso', 'sobrecarga']):
            if stats:
                bottlenecks = identify_operational_bottlenecks(stats)
                
                response = f"🔍 **ANÁLISE DE GARGALOS OPERACIONAIS**\n\n"
                response += f"{bottlenecks['status_message']}\n"
                response += f"**Score de Saúde:** {bottlenecks['overall_health_score']}/100\n\n"
                
                if bottlenecks['critical']:
                    response += "🚨 **PROBLEMAS CRÍTICOS:**\n\n"
                    for issue in bottlenecks['critical']:
                        response += f"• **{issue['description']}**\n"
                        response += f"  💥 Impacto: {issue['impact']}\n"
                        response += f"  💡 Recomendação: {issue['recommendation']}\n\n"
                
                if bottlenecks['warnings']:
                    response += "⚠️ **PONTOS DE ATENÇÃO:**\n\n"
                    for issue in bottlenecks['warnings']:
                        response += f"• **{issue['description']}**\n"
                        response += f"  ⚡ Impacto: {issue['impact']}\n"
                        response += f"  💡 Recomendação: {issue['recommendation']}\n\n"
                
                if bottlenecks['opportunities']:
                    response += "💡 **OPORTUNIDADES:**\n\n"
                    for opp in bottlenecks['opportunities']:
                        response += f"• {opp['description']}\n"
                        response += f"  ✨ Recomendação: {opp['recommendation']}\n\n"
                
                if not bottlenecks['critical'] and not bottlenecks['warnings']:
                    response += "✅ Parabéns! Não foram identificados gargalos críticos ou avisos importantes.\n"
                    response += "Continue mantendo a operação saudável! 🚀"
                
                return response
            else:
                return "🔍 Para identificar gargalos, preciso de dados operacionais. Por favor, forneça os dados necessários."
        
        # Comando: "Benchmark" ou "comparar oficinas"
        if any(keyword in question_lower for keyword in ['benchmark', 'comparar', 'comparação', 'ranking', 'posição']):
            if stats and 'organizations' in stats and len(stats['organizations']) >= 2:
                benchmark = internal_benchmark(stats['organizations'])
                
                if 'error' in benchmark:
                    return f"⚠️ {benchmark['error']}"
                
                response = "📈 **BENCHMARK INTERNO ENTRE OFICINAS**\n\n"
                response += f"**Total de Organizações:** {benchmark['summary']['total_organizations']}\n\n"
                
                response += "🏆 **LÍDERES POR CATEGORIA:**\n\n"
                response += f"• **Maior Faturamento:** {benchmark['leaders']['highest_revenue']['organization_name']}\n"
                response += f"  R$ {benchmark['leaders']['highest_revenue']['monthly_revenue']:.2f}/mês\n\n"
                
                response += f"• **Maior Ticket Médio:** {benchmark['leaders']['highest_ticket']['organization_name']}\n"
                response += f"  R$ {benchmark['leaders']['highest_ticket']['avg_ticket']:.2f}\n\n"
                
                response += f"• **Maior Satisfação:** {benchmark['leaders']['highest_satisfaction']['organization_name']}\n"
                response += f"  {benchmark['leaders']['highest_satisfaction']['client_satisfaction']:.1f} pontos\n\n"
                
                response += f"• **Mais Produtiva:** {benchmark['leaders']['most_productive']['organization_name']}\n"
                response += f"  {benchmark['leaders']['most_productive']['orders_per_technician']:.1f} OSs/técnico\n\n"
                
                if benchmark['insights']:
                    response += "💡 **INSIGHTS:**\n\n"
                    for insight in benchmark['insights']:
                        response += f"• {insight}\n"
                
                response += f"\n📊 **MÉDIAS GERAIS:**\n"
                response += f"• Faturamento Médio: R$ {benchmark['summary']['avg_monthly_revenue']:.2f}\n"
                response += f"• Ticket Médio: R$ {benchmark['summary']['avg_ticket']:.2f}\n"
                response += f"• Satisfação Média: {benchmark['summary']['avg_satisfaction']:.1f} pontos"
                
                return response
            else:
                return "📈 Para benchmark, preciso de dados de pelo menos 2 organizações. Esse recurso está disponível apenas para ambientes multi-tenant."
        
        # Comando: "Gerar relatório"
        if any(keyword in question_lower for keyword in ['relatório', 'relatorio', 'gerar relatório', 'exportar']):
            report_type = 'executive'  # Padrão
            report_format = 'text'  # Padrão
            
            if 'rentabilidade' in question_lower or 'lucr' in question_lower:
                report_type = 'profitability'
            elif 'gargalo' in question_lower or 'operacion' in question_lower:
                report_type = 'bottlenecks'
            elif 'benchmark' in question_lower or 'compar' in question_lower:
                report_type = 'benchmark'
            
            if 'csv' in question_lower:
                report_format = 'csv'
            elif 'json' in question_lower:
                report_format = 'json'
            
            if stats:
                report = generate_management_report(report_type, stats, report_format)
                
                if report_format == 'json':
                    return f"```json\n{json.dumps(report, indent=2, ensure_ascii=False)}\n```"
                elif report_format == 'csv':
                    return f"```csv\n{report}\n```"
                else:
                    return report
            else:
                return "📊 Para gerar relatórios, preciso de dados operacionais. Por favor, forneça os dados necessários."
        
        # ============================================
        # ANÁLISE PADRÃO COM LLM
        # ============================================
        
        # Se temos estatísticas, adicionar análise quantitativa
        stats_context = ""
        if stats:
            # Gerar insights baseados em dados
            data_insights = _analyze_operational_data(stats)
            predictions = _generate_predictions(stats)
            
            stats_context = f"\n\n📊 **Análise dos Dados Atuais:**\n{data_insights}"
            if predictions:
                stats_context += f"\n\n{predictions}"
        
        # Enriquecer prompt com contexto de dados
        enriched_question = question
        if stats_context:
            enriched_question = f"{question}\n\nDados disponíveis para análise:{stats_context}"
        
        chain = _recommendation_prompt | _llm
        result = chain.invoke({"question": enriched_question})
        response = result.content.strip()
        
        logger.info(f"✅ [Recommendation Agent] Resposta gerada com sucesso")
        
        # Se temos estatísticas, incluir insights no retorno
        final_response = response
        if stats_context:
            final_response = f"{response}\n\n{stats_context}"
        
        return final_response
        
    except Exception as e:
        logger.error(f"❌ [Recommendation Agent] Erro: {str(e)}", exc_info=True)
        return """
😕 Ops! Tive um problema ao gerar recomendações.

💡 **O que posso fazer (FASE 9 - Gestão Estratégica):**
- Analisar rentabilidade por serviço
- Identificar gargalos operacionais
- Realizar benchmark interno entre oficinas
- Gerar relatórios gerenciais (JSON/CSV/Texto)
- Analisar dados do seu estoque
- Recomendar ações para melhorar processos
- Dar insights sobre gestão financeira
- Sugerir estratégias de fidelização

**Exemplos de perguntas:**
- "Me mostre os serviços com maior margem"
- "Identifique gargalos operacionais"
- "Faça um benchmark entre as oficinas"
- "Gere um relatório executivo"
- "Como melhorar a rentabilidade?"
- "Análise de produtividade da equipe"
- "Que insights você tem sobre meu negócio?"

Tente reformular sua pergunta e vou te ajudar! 🚀
"""

