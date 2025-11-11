from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class VideoResult(BaseModel):
    title: str
    video_id: str
    iframe_url: str
    thumbnail: str
    channel: str

class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str
    user_id: int
    context: Optional[str] = None

class PendingAction(BaseModel):
    """Representa uma ação pendente de confirmação"""
    action: str
    action_description: str
    params: Dict[str, Any]
    endpoint: str
    method: str
    confirmation_message: str

class ActionConfirmation(BaseModel):
    """Request para confirmar uma ação"""
    action: str
    params: Dict[str, Any]
    endpoint: str
    method: str
    user_id: int

class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    image_base64: Optional[str] = None
    image_mime: Optional[str] = None
    videos: Optional[List[VideoResult]] = []
    pending_action: Optional[PendingAction] = None


# ========================================
# FASE 10: SCHEMAS MULTIMODAIS
# ========================================

class VoiceTranscribeRequest(BaseModel):
    """Request para transcrição de áudio"""
    audio_base64: str
    engine: Optional[str] = "whisper"  # "whisper" ou "google"
    language: Optional[str] = "pt"

class VoiceTranscribeResponse(BaseModel):
    """Response de transcrição"""
    status: str
    transcription: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    message: Optional[str] = None

class VoiceSynthesizeRequest(BaseModel):
    """Request para síntese de fala"""
    text: str
    voice: Optional[str] = "nova"  # alloy, echo, fable, onyx, nova, shimmer

class VoiceSynthesizeResponse(BaseModel):
    """Response de síntese de fala"""
    status: str
    audio_base64: Optional[str] = None
    audio_mime: Optional[str] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None

class VisionAnalyzeRequest(BaseModel):
    """Request para análise de imagem"""
    image_base64: str
    part_context: Optional[str] = None

class VisionAnalysisResult(BaseModel):
    """Resultado da análise de imagem"""
    part_type: Optional[str] = None
    condition: Optional[str] = None  # NORMAL, WEAR, DAMAGE, CRITICAL
    damage_severity: Optional[int] = None  # 0-5
    possible_causes: Optional[List[str]] = []
    suggested_action: Optional[str] = None
    extracted_codes: Optional[List[str]] = []
    detailed_analysis: Optional[str] = None

class VisionAnalyzeResponse(BaseModel):
    """Response de análise de imagem"""
    status: str
    analysis: Optional[VisionAnalysisResult] = None
    message: Optional[str] = None

class PredictiveOrderData(BaseModel):
    """Dados da ordem de serviço para previsão"""
    id: Optional[int] = None
    service_type: Optional[str] = None
    technician_active_orders: Optional[int] = None
    parts_available: Optional[bool] = True
    estimated_hours: Optional[float] = None
    days_open: Optional[int] = None

class PredictivePrediction(BaseModel):
    """Resultado da previsão"""
    will_delay: bool
    risk_score: int  # 0-100
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    delay_days_estimate: Optional[int] = None
    reasons: List[str]
    recommendations: List[str]

class PredictiveDelayResponse(BaseModel):
    """Response de previsão de atraso"""
    status: str
    prediction: Optional[PredictivePrediction] = None
    message: Optional[str] = None

class PredictiveOperationalData(BaseModel):
    """Dados operacionais para previsão de gargalos"""
    open_orders: Optional[int] = None
    active_technicians: Optional[int] = None
    daily_completion_rate: Optional[float] = None
    daily_new_orders: Optional[float] = None
    low_stock_count: Optional[int] = None

class PredictiveBottleneckForecast(BaseModel):
    """Previsão de gargalos"""
    will_bottleneck: bool
    bottleneck_date: Optional[str] = None
    days_until_bottleneck: Optional[int] = None
    summary: Dict[str, Any]
    issues: List[Dict[str, Any]]
    recommendations: List[str]

class PredictiveBottlenecksResponse(BaseModel):
    """Response de previsão de gargalos"""
    status: str
    forecast: Optional[PredictiveBottleneckForecast] = None
    message: Optional[str] = None

class SimulationCurrentData(BaseModel):
    """Dados atuais para simulação"""
    monthly_revenue: Optional[float] = None
    monthly_orders: Optional[int] = None
    avg_ticket: Optional[float] = None
    profit_margin_percent: Optional[float] = None
    technician_count: Optional[int] = None
    tech_cost_monthly: Optional[float] = None

class SimulationProjection(BaseModel):
    """Projeção de simulação"""
    new_monthly_revenue: Optional[float] = None
    new_monthly_orders: Optional[int] = None
    new_avg_ticket: Optional[float] = None
    revenue_change: float
    orders_change: Optional[int] = None
    profit_change: Optional[float] = None
    roi_percent: Optional[float] = None

class SimulationResponse(BaseModel):
    """Response de simulação"""
    status: str
    projection: Optional[SimulationProjection] = None
    analysis: Optional[str] = None
    recommendation: Optional[str] = None
    assumptions: Optional[List[str]] = []
    message: Optional[str] = None

class MultimodalChatRequest(BaseModel):
    """Request para chat multimodal"""
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    image_base64: Optional[str] = None
    context: Optional[str] = None
    tts_enabled: Optional[bool] = False
    metadata: Optional[Dict[str, Any]] = {}

class MultimodalChatResponse(BaseModel):
    """Response de chat multimodal"""
    status: str
    routing: Dict[str, Any]
    results: Dict[str, Any]
    message: str