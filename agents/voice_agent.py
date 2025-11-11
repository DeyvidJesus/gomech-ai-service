"""
FASE 10 - Voice Agent: Comando por voz (Speech-to-Text)

Suporta:
- Google Speech-to-Text API
- OpenAI Whisper API
- Transcrição de áudio para texto
- Conversão de resposta texto para voz (Text-to-Speech)
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import base64

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CLOUD_KEY = os.getenv("GOOGLE_CLOUD_API_KEY")

logger = logging.getLogger(__name__)


def transcribe_audio_whisper(audio_base64: str, language: str = "pt") -> Dict[str, Any]:
    """
    Transcreve áudio usando OpenAI Whisper API.
    
    Args:
        audio_base64: Áudio em formato base64
        language: Código do idioma (pt, en, es, etc)
    
    Returns:
        Dict com texto transcrito e metadados
    """
    try:
        import openai
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Decodificar base64
        audio_bytes = base64.b64decode(audio_base64)
        
        # Salvar temporariamente (Whisper API precisa de arquivo)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio_path = temp_audio.name
        
        # Transcrever com Whisper
        with open(temp_audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )
        
        # Limpar arquivo temporário
        os.remove(temp_audio_path)
        
        logger.info(f"🎤 [Whisper] Áudio transcrito: {transcript.text[:100]}...")
        
        return {
            "status": "success",
            "text": transcript.text,
            "language": language,
            "engine": "whisper"
        }
        
    except Exception as e:
        logger.error(f"❌ [Whisper] Erro na transcrição: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "text": ""
        }


def transcribe_audio_google(audio_base64: str, language: str = "pt-BR") -> Dict[str, Any]:
    """
    Transcreve áudio usando Google Cloud Speech-to-Text API.
    
    Args:
        audio_base64: Áudio em formato base64
        language: Código do idioma (pt-BR, en-US, es-ES, etc)
    
    Returns:
        Dict com texto transcrito e metadados
    """
    try:
        from google.cloud import speech
        
        # Configurar cliente
        client = speech.SpeechClient()
        
        # Decodificar base64
        audio_bytes = base64.b64decode(audio_base64)
        
        # Configurar requisição
        audio = speech.RecognitionAudio(content=audio_bytes)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=language,
            enable_automatic_punctuation=True,
            model="latest_long"
        )
        
        # Transcrever
        response = client.recognize(config=config, audio=audio)
        
        # Extrair melhor resultado
        if response.results:
            transcript = response.results[0].alternatives[0].transcript
            confidence = response.results[0].alternatives[0].confidence
            
            logger.info(f"🎤 [Google Speech] Áudio transcrito: {transcript[:100]}... (confidence: {confidence:.2f})")
            
            return {
                "status": "success",
                "text": transcript,
                "confidence": confidence,
                "language": language,
                "engine": "google"
            }
        else:
            return {
                "status": "error",
                "error": "Nenhum resultado de transcrição",
                "text": ""
            }
        
    except Exception as e:
        logger.error(f"❌ [Google Speech] Erro na transcrição: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "text": ""
        }


def text_to_speech_openai(text: str, voice: str = "nova", speed: float = 1.1) -> Dict[str, Any]:
    """
    Converte texto em áudio usando OpenAI TTS API.
    
    Args:
        text: Texto para converter
        voice: Voz a usar (alloy, echo, fable, onyx, nova, shimmer)
        speed: Velocidade da fala (0.25 a 4.0, padrão 1.1)
    
    Returns:
        Dict com áudio em base64 e metadados
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Limitar texto para evitar respostas muito longas
        # OpenAI TTS suporta até 4096 caracteres
        max_chars = 4096
        original_length = len(text)
        
        if len(text) > max_chars:
            # Truncar inteligentemente - tentar cortar em uma frase completa
            text = text[:max_chars]
            last_period = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_period > max_chars * 0.8:  # Se encontrar ponto após 80% do texto
                text = text[:last_period + 1]
            else:
                text = text + "..."
            
            logger.warning(f"⚠️ [OpenAI TTS] Texto truncado de {original_length} para {len(text)} caracteres")
        
        logger.info(f"🔊 [OpenAI TTS] Iniciando síntese: {len(text)} chars, voz: {voice}, velocidade: {speed}")
        
        # Gerar áudio com velocidade ajustada
        response = client.audio.speech.create(
            model="tts-1",  # Modelo mais rápido (use tts-1-hd para maior qualidade)
            voice=voice,
            input=text,
            speed=speed  # Velocidade natural e pausada
        )
        
        # Converter para base64
        audio_bytes = response.content
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        logger.info(f"🔊 [OpenAI TTS] Texto convertido em áudio: {len(text)} caracteres, velocidade: {speed}")
        
        return {
            "status": "success",
            "audio_base64": audio_base64,
            "audio_mime": "audio/mpeg",
            "voice": voice,
            "speed": speed,
            "engine": "openai"
        }
        
    except Exception as e:
        logger.error(f"❌ [OpenAI TTS] Erro na conversão: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def run_voice_agent(audio_base64: str, engine: str = "whisper", language: str = "pt") -> Dict[str, Any]:
    """
    Processa comando por voz completo.
    
    Fluxo:
    1. Transcreve áudio → texto (Whisper ou Google)
    2. Retorna texto para processamento pelo RouterAgent
    
    Args:
        audio_base64: Áudio em formato base64
        engine: Motor de transcrição (whisper, google)
        language: Código do idioma
    
    Returns:
        Dict com texto transcrito e metadados
    """
    logger.info(f"🎤 [Voice Agent] Iniciando transcrição com {engine}")
    
    try:
        # Escolher engine
        if engine == "google":
            result = transcribe_audio_google(audio_base64, f"{language}-BR" if language == "pt" else language)
        else:  # whisper (padrão)
            result = transcribe_audio_whisper(audio_base64, language)
        
        if result["status"] == "success":
            logger.info(f"✅ [Voice Agent] Transcrição concluída: {result['text'][:100]}...")
            return {
                "status": "success",
                "transcription": result["text"],
                "engine": result["engine"],
                "language": language,
                "message": "Áudio transcrito com sucesso!"
            }
        else:
            logger.error(f"❌ [Voice Agent] Erro na transcrição: {result.get('error')}")
            return {
                "status": "error",
                "error": result.get("error", "Erro desconhecido na transcrição"),
                "message": "Não foi possível transcrever o áudio"
            }
    
    except Exception as e:
        logger.error(f"❌ [Voice Agent] Erro geral: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Erro ao processar comando por voz"
        }


def process_voice_command(audio_base64: str, tts_enabled: bool = False) -> Dict[str, Any]:
    """
    Processa comando por voz completo com resposta opcional em áudio.
    
    Fluxo completo:
    1. Speech-to-Text (áudio → texto)
    2. Processar comando (RouterAgent)
    3. Text-to-Speech (resposta → áudio) [opcional]
    
    Args:
        audio_base64: Áudio do comando
        tts_enabled: Se True, retorna resposta também em áudio
    
    Returns:
        Dict com texto transcrito, resposta e áudio opcional
    """
    try:
        # 1. Transcrever áudio
        transcription = run_voice_agent(audio_base64)
        
        if transcription["status"] != "success":
            return transcription
        
        text_command = transcription["transcription"]
        
        # 2. Processar comando (será feito pelo RouterAgent no main.py)
        # Aqui apenas retornamos a transcrição
        result = {
            "status": "success",
            "transcription": text_command,
            "message": "Comando transcrito. Processando..."
        }
        
        # 3. Converter resposta em áudio (se habilitado)
        # Isso será feito após o RouterAgent processar
        if tts_enabled:
            result["tts_enabled"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"❌ [Voice Command] Erro: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "message": "Erro ao processar comando por voz"
        }


# ========================================
# CONFIGURAÇÕES E HELPERS
# ========================================

def get_supported_voices() -> Dict[str, list]:
    """Retorna lista de vozes suportadas."""
    return {
        "openai": [
            {"id": "alloy", "name": "Alloy", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "gender": "male"},
            {"id": "fable", "name": "Fable", "gender": "neutral"},
            {"id": "onyx", "name": "Onyx", "gender": "male"},
            {"id": "nova", "name": "Nova", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female"}
        ]
    }


def get_supported_languages() -> list:
    """Retorna lista de idiomas suportados."""
    return [
        {"code": "pt", "name": "Português", "whisper": "pt", "google": "pt-BR"},
        {"code": "en", "name": "English", "whisper": "en", "google": "en-US"},
        {"code": "es", "name": "Español", "whisper": "es", "google": "es-ES"},
        {"code": "fr", "name": "Français", "whisper": "fr", "google": "fr-FR"},
        {"code": "de", "name": "Deutsch", "whisper": "de", "google": "de-DE"}
    ]


# ========================================
# PLACEHOLDER PARA IMPLEMENTAÇÃO FUTURA
# ========================================

def configure_voice_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configura preferências de voz do usuário.
    
    Configurações suportadas:
    - engine: whisper ou google
    - language: código do idioma
    - tts_voice: voz preferida
    - tts_enabled: habilitar Text-to-Speech
    - auto_detect_language: detectar idioma automaticamente
    """
    # Placeholder - implementar lógica de persistência
    logger.info(f"⚙️ [Voice Settings] Configurações atualizadas: {settings}")
    return {
        "status": "success",
        "settings": settings,
        "message": "Configurações de voz atualizadas!"
    }

