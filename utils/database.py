import time
import logging
from sqlalchemy.exc import OperationalError, DisconnectionError
from functools import wraps

logger = logging.getLogger(__name__)

def retry_db_connection(max_retries=3, delay=1, backoff=2):
    """
    Decorator para retry automático em caso de falha de conexão com banco
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Falha na conexão após {max_retries} tentativas: {e}")
                        raise
                    
                    wait_time = delay * (backoff ** (retries - 1))
                    logger.warning(f"Erro de conexão (tentativa {retries}/{max_retries}). Tentando novamente em {wait_time}s: {e}")
                    time.sleep(wait_time)
                except Exception as e:
                    # Para outros tipos de erro, não fazer retry
                    logger.error(f"Erro não relacionado à conexão: {e}")
                    raise
            return None
        return wrapper
    return decorator

def test_database_connection(engine):
    """
    Testa a conexão com o banco de dados
    """
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✅ Conexão com banco de dados estabelecida com sucesso")
            return True
    except Exception as e:
        logger.error(f"❌ Falha na conexão com banco de dados: {e}")
        return False

def get_database_info(engine):
    """
    Obtém informações sobre o banco de dados
    """
    try:
        with engine.connect() as conn:
            # Versão do PostgreSQL
            version_result = conn.execute("SELECT version()")
            version = version_result.fetchone()[0]
            
            # Número de conexões ativas
            connections_result = conn.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active_connections = connections_result.fetchone()[0]
            
            return {
                "version": version,
                "active_connections": active_connections,
                "status": "healthy"
            }
    except Exception as e:
        logger.error(f"Erro ao obter informações do banco: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
