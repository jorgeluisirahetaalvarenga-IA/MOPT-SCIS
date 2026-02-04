"""
Excepciones base del sistema - NO dependen de frameworks
Definen el lenguaje ubicuo del dominio
"""
from typing import Any, Dict, Optional


class AppException(Exception):
    """Excepción base de la aplicación"""
    
    def __init__(
        self, 
        message: str, 
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class DomainException(AppException):
    """Excepción del dominio - Violación de regla de negocio"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DOMAIN_ERROR", 400, details)


class BusinessRuleException(DomainException):
    """Violación específica de regla de negocio"""
    def __init__(self, message: str, rule_name: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["rule"] = rule_name
        super().__init__(message, details)


class ValidationException(AppException):
    """Error de validación de datos de entrada"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, "VALIDATION_ERROR", 422, details)


class AuthenticationException(AppException):
    """Error de autenticación"""
    def __init__(self, message: str = "Credenciales inválidas", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", 401, details)


class AuthorizationException(AppException):
    """Error de autorización"""
    def __init__(self, message: str = "No autorizado", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_ERROR", 403, details)


class NotFoundException(AppException):
    """Recurso no encontrado"""
    def __init__(self, resource: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} con ID {resource_id} no encontrado"
        details = details or {}
        details["resource"] = resource
        details["resource_id"] = resource_id
        super().__init__(message, "NOT_FOUND", 404, details)