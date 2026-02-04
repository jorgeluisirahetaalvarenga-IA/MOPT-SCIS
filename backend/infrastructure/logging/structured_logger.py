"""
Logging estructurado para la aplicación.
Implementa logs en formato JSON para mejor procesamiento.

Características:
- Formato JSON estructurado
- Diferentes niveles de log
- Logs separados por propósito
- Rotación automática de archivos
"""
import logging
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler


class StructuredFormatter(logging.Formatter):
    """
    Formatter para logs estructurados en JSON.
    Convierte registros de log a objetos JSON.
    """
    
    def format(self, record):
        # Crear objeto de log base
        log_object = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.threadName if record.threadName else "main",
            "process": record.process if hasattr(record, 'process') else os.getpid()
        }
        
        # Agregar extras si existen
        if hasattr(record, 'extra_data'):
            log_object.update(record.extra_data)
        
        # Agregar excepción si existe
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        
        # Agregar stack trace si existe
        if hasattr(record, 'stack_info') and record.stack_info:
            log_object["stack_trace"] = self.formatStack(record.stack_info)
        
        return json.dumps(log_object, ensure_ascii=False, default=str)


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/app.log",
    audit_log_file: str = "logs/audit.log",
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Configurar logging estructurado completo.
    
    Args:
        log_level: Nivel de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Archivo para logs generales
        audit_log_file: Archivo para logs de auditoría
        max_file_size: Tamaño máximo de archivo antes de rotar
        backup_count: Número de archivos de backup a mantener
        
    Returns:
        logging.Logger: Logger raíz configurado
    """
    # Crear directorio de logs si no existe
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    os.makedirs(os.path.dirname(audit_log_file), exist_ok=True)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remover handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler para consola (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredFormatter())
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    # Handler para archivo de aplicación (con rotación)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(StructuredFormatter())
    file_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    
    # Logger específico para auditoría
    audit_logger = logging.getLogger("audit")
    audit_handler = RotatingFileHandler(
        audit_log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    audit_handler.setFormatter(StructuredFormatter())
    audit_handler.setLevel(logging.INFO)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False  # No propagar al root logger
    
    # Logger específico para seguridad
    security_logger = logging.getLogger("security")
    security_handler = RotatingFileHandler(
        "logs/security.log",
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    security_handler.setFormatter(StructuredFormatter())
    security_handler.setLevel(logging.WARNING)
    security_logger.addHandler(security_handler)
    security_logger.propagate = False
    
    # Configurar log level para dependencias externas
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    return root_logger


class AuditLogger:
    """Logger especializado para auditoría de negocio"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log_movement(self, movement_data: Dict[str, Any], user_data: Dict[str, Any]):
        """Log de movimiento de inventario"""
        self.logger.info(
            "Inventory movement recorded",
            extra={
                "extra_data": {
                    "event_type": "INVENTORY_MOVEMENT",
                    "movement_data": movement_data,
                    "user_data": user_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_auth_success(self, username: str, user_id: int, ip_address: Optional[str] = None):
        """Log de autenticación exitosa"""
        self.logger.info(
            "Authentication successful",
            extra={
                "extra_data": {
                    "event_type": "AUTHENTICATION_SUCCESS",
                    "username": username,
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_auth_failure(self, username: str, reason: str, ip_address: Optional[str] = None):
        """Log de autenticación fallida"""
        self.logger.warning(
            "Authentication failed",
            extra={
                "extra_data": {
                    "event_type": "AUTHENTICATION_FAILURE",
                    "username": username,
                    "reason": reason,
                    "ip_address": ip_address,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_user_action(self, user_id: int, action: str, details: Dict[str, Any]):
        """Log de acción de usuario"""
        self.logger.info(
            "User action performed",
            extra={
                "extra_data": {
                    "event_type": "USER_ACTION",
                    "user_id": user_id,
                    "action": action,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_system_event(self, event_type: str, details: Dict[str, Any]):
        """Log de evento del sistema"""
        self.logger.info(
            "System event",
            extra={
                "extra_data": {
                    "event_type": event_type,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


class SecurityLogger:
    """Logger especializado para eventos de seguridad"""
    
    def __init__(self):
        self.logger = logging.getLogger("security")
    
    def log_security_event(self, event_type: str, severity: str, details: Dict[str, Any]):
        """Log de evento de seguridad"""
        log_method = getattr(self.logger, severity.lower(), self.logger.warning)
        
        log_method(
            f"Security event: {event_type}",
            extra={
                "extra_data": {
                    "event_type": event_type,
                    "severity": severity,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_brute_force_attempt(self, username: str, ip_address: str, attempt_count: int):
        """Log de intento de fuerza bruta"""
        self.log_security_event(
            event_type="BRUTE_FORCE_ATTEMPT",
            severity="WARNING",
            details={
                "username": username,
                "ip_address": ip_address,
                "attempt_count": attempt_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def log_suspicious_activity(self, user_id: int, activity: str, details: Dict[str, Any]):
        """Log de actividad sospechosa"""
        self.log_security_event(
            event_type="SUSPICIOUS_ACTIVITY",
            severity="ERROR",
            details={
                "user_id": user_id,
                "activity": activity,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Decorador para logging de funciones
def log_execution(logger_name: str = "app", level: str = "INFO"):
    """
    Decorador para logging automático de ejecución de funciones.
    
    Args:
        logger_name: Nombre del logger a usar
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        function: Decorador
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name)
            log_method = getattr(logger, level.lower())
            
            # Log de entrada
            log_method(
                f"Executing {func.__name__}",
                extra={
                    "extra_data": {
                        "function": func.__name__,
                        "module": func.__module__,
                        "args": str(args)[:200],  # Limitar longitud
                        "kwargs": str(kwargs)[:200],
                        "action": "start"
                    }
                }
            )
            
            try:
                # Ejecutar función
                result = func(*args, **kwargs)
                
                # Log de éxito
                log_method(
                    f"Completed {func.__name__}",
                    extra={
                        "extra_data": {
                            "function": func.__name__,
                            "success": True,
                            "action": "complete"
                        }
                    }
                )
                
                return result
                
            except Exception as e:
                # Log de error
                logger.error(
                    f"Failed {func.__name__}",
                    extra={
                        "extra_data": {
                            "function": func.__name__,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "success": False,
                            "action": "error"
                        }
                    },
                    exc_info=True
                )
                raise
                
        return wrapper
    return decorator