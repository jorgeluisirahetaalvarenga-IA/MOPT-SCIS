"""
Middleware global para FastAPI.
Intercepta todas las requests y responses para cross-cutting concerns.

Responsabilidades:
1. Logging de requests/responses
2. Manejo de CORS
3. Procesamiento de errores
4. Inyección de headers
"""
import time
import logging
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any

from ..infrastructure.logging.structured_logger import AuditLogger

logger = logging.getLogger(__name__)
audit_logger = AuditLogger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging estructurado de requests y responses.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Obtener información de la request
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Información de autenticación
        auth_info = "anonymous"
        user_id = None
        
        # Intentar extraer información del token si existe
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from ..infrastructure.auth.jwt_handler import JWTHandler
                token = auth_header.split(" ")[1]
                payload = JWTHandler.extract_user_from_token(token)
                auth_info = payload.get("username", "authenticated")
                user_id = payload.get("user_id")
            except:
                auth_info = "invalid_token"
        
        # Log de request
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "user_agent": user_agent[:100],  # Limitar longitud
            "user": auth_info,
            "user_id": user_id,
            "action": "request_start"
        }
        
        logger.info(f"Request: {request.method} {request.url.path}", extra={"extra_data": request_info})
        
        try:
            # Procesar request
            response = await call_next(request)
            
            # Calcular tiempo de respuesta
            process_time = time.time() - start_time
            
            # Log de response
            response_info = {
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "client_ip": client_ip,
                "user": auth_info,
                "user_id": user_id,
                "action": "request_complete"
            }
            
            log_level = "info" if response.status_code < 400 else "warning" if response.status_code < 500 else "error"
            getattr(logger, log_level)(
                f"Response: {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)",
                extra={"extra_data": response_info}
            )
            
            # Agregar header de tiempo de procesamiento
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Log de error no manejado
            process_time = time.time() - start_time
            error_info = {
                "method": request.method,
                "url": str(request.url),
                "client_ip": client_ip,
                "user": auth_info,
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time": round(process_time, 4),
                "action": "request_error"
            }
            
            logger.error(
                f"Unhandled error: {request.method} {request.url.path} - {str(e)}",
                extra={"extra_data": error_info},
                exc_info=True
            )
            
            raise


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware para auditoría de acciones específicas.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Solo auditar ciertos endpoints
        audit_paths = [
            "/api/inventory/movement",
            "/api/auth/login",
            "/api/auth/register",
            "/api/users"
        ]
        
        if any(request.url.path.startswith(path) for path in audit_paths):
            # Obtener información para auditoría
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "unknown")
            
            # Ejecutar request
            response = await call_next(request)
            
            # Registrar en auditoría si es movimiento de inventario
            if request.url.path == "/api/inventory/movement" and request.method == "POST":
                try:
                    # Intentar obtener datos del body (esto es simplificado)
                    body = await request.body()
                    if body:
                        audit_logger.log_movement(
                            movement_data={"request_body": body.decode()[:500]},
                            user_data={"ip": client_ip, "user_agent": user_agent}
                        )
                except:
                    pass
            
            return response
        
        # Para otros endpoints, continuar sin auditoría detallada
        return await call_next(request)


def setup_middlewares(app):
    """
    Configurar todos los middlewares de la aplicación.
    
    Args:
        app: Aplicación FastAPI
    """
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # En producción especificar dominios
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # GZip Middleware (compresión)
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # Comprimir respuestas > 1KB
    )
    
    # Logging Middleware
    app.add_middleware(LoggingMiddleware)
    
    # Audit Middleware
    app.add_middleware(AuditMiddleware)
    
    # Security headers middleware (implementación simple)
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Headers de seguridad
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response