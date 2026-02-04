"""
Dependencias para inyección en FastAPI.
Centraliza la creación y gestión de dependencias para toda la aplicación.

Responsabilidades:
1. Proveer sesiones de base de datos
2. Manejar autenticación JWT
3. Verificar roles y permisos
4. Inyectar repositorios concretos
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Generator, Optional

from ..infrastructure.database.session import get_db
from ..infrastructure.database.models import User, UserRole
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
) -> User:
    """
    Obtener usuario actual a partir del token JWT.
    
    Args:
        request: Request HTTP para obtener IP
        credentials: Credenciales JWT del header Authorization
        db: Sesión de base de datos
        
    Returns:
        User: Usuario autenticado
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    try:
        # Obtener IP del cliente
        ip_address = request.client.host if request.client else "unknown"
        
        # Verificar token JWT
        payload = JWTHandler.verify_token(credentials.credentials)
        username: str = payload.get("sub")
        
        if username is None:
            raise AuthenticationException("Credenciales inválidas")
        
        # Buscar usuario en base de datos
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            audit_logger.log_auth_failure(username, "Usuario no encontrado", ip_address)
            raise AuthenticationException("Usuario no encontrado")
        
        if not user.is_active:
            audit_logger.log_auth_failure(username, "Usuario inactivo", ip_address)
            raise AuthenticationException("Usuario inactivo")
        
        # Log de autenticación exitosa
        audit_logger.log_auth_success(username, user.id, ip_address)
        
        return user
        
    except AuthenticationException as e:
        # Log de intento fallido
        username = "unknown"
        try:
            if 'credentials' in locals():
                payload = JWTHandler.extract_user_from_token(credentials.credentials)
                username = payload.get("username", "unknown")
        except:
            pass
        
        audit_logger.log_auth_failure(username, str(e), ip_address if 'ip_address' in locals() else None)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(required_role: UserRole):
    """
    Factory function para crear dependencia que verifica rol de usuario.
    
    Args:
        required_role: Rol mínimo requerido
        
    Returns:
        callable: Dependencia FastAPI
    """
    def role_checker(current_user: User = Depends(get_current_user)):
        if not current_user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere rol: {required_role.value}"
            )
        
        return current_user
    
    return role_checker


# Dependencias específicas por rol para facilitar el uso
def require_admin(current_user: User = Depends(get_current_user)):
    """Requerir rol de administrador"""
    if not current_user.has_permission(UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de administrador"
        )
    return current_user


def require_manager(current_user: User = Depends(get_current_user)):
    """Requerir rol de gerente o superior"""
    if not current_user.has_permission(UserRole.MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de gerente o superior"
        )
    return current_user


def require_operator(current_user: User = Depends(get_current_user)):
    """Requerir rol de operador o superior"""
    if not current_user.has_permission(UserRole.OPERATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de operador o superior"
        )
    return current_user


def require_viewer(current_user: User = Depends(get_current_user)):
    """Requerir rol de visualizador o superior"""
    if not current_user.has_permission(UserRole.VIEWER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de visualizador o superior"
        )
    return current_user


# Dependencias para repositorios
def get_product_repository(db: Session = Depends(get_db_session)):
    """Proveer repositorio de productos"""
    from ..app.infrastructure.repositories.product_repository_impl import SQLAlchemyProductRepository
    return SQLAlchemyProductRepository(db)


def get_movement_repository(db: Session = Depends(get_db_session)):
    """Proveer repositorio de movimientos"""
    from ..app.infrastructure.repositories.movement_repository_impl import SQLAlchemyMovementRepository
    return SQLAlchemyMovementRepository(db)


def get_user_repository(db: Session = Depends(get_db_session)):
    """Proveer repositorio de usuarios"""
    from ..app.infrastructure.repositories.user_repository_impl import SQLAlchemyUserRepository
    return SQLAlchemyUserRepository(db)


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


# Dependencia para verificar permisos específicos
def check_permission(permission: str):
    """
    Verificar si el usuario tiene un permiso específico.
    
    Args:
        permission: Permiso a verificar
        
    Returns:
        callable: Dependencia
    """
    def permission_checker(current_user: User = Depends(get_current_user)):
        if not current_user.can_perform_action(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No tiene permisos para: {permission}"
            )
        return current_user
    
    return permission_checker