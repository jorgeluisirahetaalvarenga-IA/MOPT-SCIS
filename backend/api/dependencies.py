"""
Dependencias para inyección en FastAPI.
Centraliza la creación y gestión de dependencias para toda la aplicación.

Responsabilidades:
1. Proveer sesiones de base de datos
2. Manejar autenticación JWT
3. Verificar roles y permisos
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Generator, Optional

from ..infrastructure.database.session import get_db
from ..infrastructure.auth.jwt_handler import JWTHandler
from ..app.core.exceptions import AuthenticationException, AuthorizationException
from ..infrastructure.logging.structured_logger import AuditLogger, SecurityLogger

# Servicios globales
security = HTTPBearer()
audit_logger = AuditLogger()
security_logger = SecurityLogger()


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependencia para obtener sesión de base de datos.
    
    Returns:
        Generator[Session]: Generador de sesiones SQLAlchemy
    """
    db = next(get_db())
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
):
    """
    Obtener usuario actual a partir del token JWT.
    
    Returns:
        User: Usuario autenticado
    """
    try:
        # Obtener IP del cliente
        ip_address = request.client.host if request.client else "unknown"
        
        # Verificar token JWT
        payload = JWTHandler.verify_token(credentials.credentials)
        username: str = payload.get("sub")
        
        if username is None:
            raise AuthenticationException("Credenciales inválidas")
        
        # Buscar usuario usando JWT handler (evitar importación de repositorios aquí)
        user_data = JWTHandler.get_user_from_token(credentials.credentials, db)
        
        if not user_data:
            audit_logger.log_auth_failure(username, "Usuario no encontrado", ip_address)
            raise AuthenticationException("Usuario no encontrado")
        
        if not user_data.get("is_active", False):
            audit_logger.log_auth_failure(username, "Usuario inactivo", ip_address)
            raise AuthenticationException("Usuario inactivo")
        
        # Log de autenticación exitosa
        audit_logger.log_auth_success(
            username, 
            user_data.get("id"), 
            ip_address
        )
        
        return user_data
        
    except AuthenticationException as e:
        username = "unknown"
        try:
            if 'credentials' in locals():
                payload = JWTHandler.extract_user_from_token(credentials.credentials)
                username = payload.get("username", "unknown")
        except:
            pass
        
        audit_logger.log_auth_failure(
            username, 
            str(e), 
            ip_address if 'ip_address' in locals() else None
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_role: str):
    """
    Factory function para crear dependencia que verifica rol de usuario.
    
    Args:
        required_role: Rol mínimo requerido
        
    Returns:
        callable: Dependencia FastAPI
    """
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "")
        user_roles = ["viewer", "operator", "manager", "admin"]
        
        # Verificar jerarquía de roles
        if user_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sin rol asignado"
            )
        
        if user_roles.index(user_role) < user_roles.index(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere rol: {required_role}"
            )
        
        return current_user
    
    return role_checker


# Dependencias específicas por rol para facilitar el uso
def require_admin(current_user: dict = Depends(get_current_user)):
    """Requerir rol de administrador"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador"
        )
    return current_user


def require_manager(current_user: dict = Depends(get_current_user)):
    """Requerir rol de gerente o superior"""
    required = ["manager", "admin"]
    if current_user.get("role") not in required:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de gerente o superior"
        )
    return current_user


def require_operator(current_user: dict = Depends(get_current_user)):
    """Requerir rol de operador o superior"""
    required = ["operator", "manager", "admin"]
    if current_user.get("role") not in required:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de operador o superior"
        )
    return current_user


def require_viewer(current_user: dict = Depends(get_current_user)):
    """Requerir rol de visualizador o superior"""
    required = ["viewer", "operator", "manager", "admin"]
    if current_user.get("role") not in required:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de visualizador o superior"
        )
    return current_user


# Dependencias para servicios
def get_jwt_handler():
    """Proveer manejador JWT"""
    return JWTHandler


def get_audit_logger():
    """Proveer logger de auditoría"""
    return audit_logger


def get_security_logger():
    """Proveer logger de seguridad"""
    return security_logger