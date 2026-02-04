"""
Entidad Usuario - Autenticación y autorización en el dominio.
Maneja identidad, roles y permisos de usuarios del sistema.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import enum

from ....app.core.exceptions import BusinessRuleException
from ....app.domain.exceptions import (
    InvalidCredentialsError,
    UserInactiveError,
    InsufficientPermissionsError
)


class UserRole(str, enum.Enum):
    """
    Roles de usuario definidos como Enum en el dominio.
    
    Jerarquía (de mayor a menor privilegio):
    1. ADMIN: Administrador del sistema - Acceso total
    2. MANAGER: Gerente - Gestiona inventario y reportes
    3. OPERATOR: Operador - Realiza movimientos de inventario
    4. VIEWER: Visualizador - Solo consultas y reportes
    """
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"
    
    @classmethod
    def get_hierarchy(cls) -> Dict['UserRole', int]:
        """Obtener jerarquía de roles - Parte del dominio"""
        return {
            cls.ADMIN: 4,
            cls.MANAGER: 3,
            cls.OPERATOR: 2,
            cls.VIEWER: 1
        }
    
    @classmethod
    def from_string(cls, role_str: str) -> 'UserRole':
        """Crear UserRole desde string con validación"""
        try:
            return cls(role_str.lower())
        except ValueError:
            valid_roles = [role.value for role in cls]
            raise BusinessRuleException(
                f"Rol inválido: '{role_str}'. Roles válidos: {valid_roles}",
                "invalid_role",
                {"provided_role": role_str, "valid_roles": valid_roles}
            )


@dataclass
class User:
    """
    Entidad Usuario con autenticación y autorización.
    Contiene lógica de negocio relacionada con usuarios y permisos.
    
    Atributos:
    - id: Identificador único
    - username: Nombre de usuario único
    - email: Email único
    - hashed_password: Contraseña hasheada
    - full_name: Nombre completo
    - role: Rol del usuario (determina permisos)
    - is_active: Estado activo/inactivo
    - created_at: Fecha de creación
    - updated_at: Fecha de última actualización
    """
    id: Optional[int] = None
    username: str = ""
    email: str = ""
    hashed_password: str = ""
    full_name: Optional[str] = None
    role: UserRole = UserRole.VIEWER
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Para auditoría
    _login_attempts: int = 0
    _last_login: Optional[datetime] = None
    
    def __post_init__(self):
        """Validaciones automáticas al crear la entidad"""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validar invariantes de la entidad usuario.
        
        Raises:
            BusinessRuleException: Si se viola algún invariante
        """
        # Username requerido
        if not self.username.strip():
            raise BusinessRuleException(
                "El nombre de usuario es requerido",
                "username_required"
            )
        
        # Email requerido
        if not self.email.strip():
            raise BusinessRuleException(
                "El email es requerido",
                "email_required"
            )
        
        # Validación básica de email
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise BusinessRuleException(
                "El email no tiene un formato válido",
                "email_format",
                {"email": self.email}
            )
        
        # Contraseña requerida
        if not self.hashed_password:
            raise BusinessRuleException(
                "La contraseña es requerida",
                "password_required"
            )
        
        # Validar que el rol sea válido
        try:
            UserRole(self.role)
        except ValueError:
            valid_roles = [role.value for role in UserRole]
            raise BusinessRuleException(
                f"Rol inválido. Roles válidos: {valid_roles}",
                "valid_role",
                {"valid_roles": valid_roles, "provided_role": self.role.value if isinstance(self.role, UserRole) else self.role}
            )
    
    def has_permission(self, required_role: UserRole) -> bool:
        """
        Verificar si el usuario tiene el rol requerido o superior.
        Esta es una regla de negocio fundamental.
        
        Args:
            required_role: Rol mínimo requerido
            
        Returns:
            bool: True si el usuario tiene permisos suficientes
        """
        if not self.is_active:
            raise UserInactiveError(self.id if self.id else 0)
        
        hierarchy = UserRole.get_hierarchy()
        user_level = hierarchy.get(self.role, 0)
        required_level = hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def check_permission(self, required_role: UserRole) -> None:
        """
        Verificar permisos y lanzar excepción si no tiene.
        
        Args:
            required_role: Rol mínimo requerido
            
        Raises:
            InsufficientPermissionsError: Si no tiene permisos
        """
        if not self.has_permission(required_role):
            raise InsufficientPermissionsError(
                user_role=self.role.value,
                required_role=required_role.value
            )
    
    def can_perform_action(self, action: str) -> bool:
        """
        Verificar si el usuario puede realizar una acción específica.
        Mapeo de acciones a roles requeridos.
        """
        # Mapeo de acciones a roles mínimos requeridos
        action_requirements = {
            # Productos
            "view_products": UserRole.VIEWER,
            "create_product": UserRole.MANAGER,
            "update_product": UserRole.MANAGER,
            "delete_product": UserRole.ADMIN,
            
            # Inventario
            "view_inventory": UserRole.VIEWER,
            "register_movement": UserRole.OPERATOR,
            "adjust_stock": UserRole.MANAGER,
            
            # Reportes
            "view_reports": UserRole.VIEWER,
            "generate_reports": UserRole.MANAGER,
            
            # Usuarios
            "view_users": UserRole.MANAGER,
            "create_user": UserRole.ADMIN,
            "update_user": UserRole.ADMIN,
            "delete_user": UserRole.ADMIN,
            
            # Auditoría
            "view_audit_logs": UserRole.MANAGER,
            "export_audit_logs": UserRole.ADMIN,
            
            # Sistema
            "view_system_settings": UserRole.ADMIN,
            "update_system_settings": UserRole.ADMIN,
        }
        
        required_role = action_requirements.get(action, UserRole.ADMIN)
        return self.has_permission(required_role)
    
    def authenticate(self, plain_password: str, password_verifier) -> bool:
        """
        Autenticar usuario con contraseña.
        
        Args:
            plain_password: Contraseña en texto plano
            password_verifier: Función que verifica contraseña
            
        Returns:
            bool: True si autenticación exitosa
            
        Raises:
            UserInactiveError: Si el usuario está inactivo
        """
        if not self.is_active:
            raise UserInactiveError(self.id if self.id else 0)
        
        is_authenticated = password_verifier(plain_password, self.hashed_password)
        
        if is_authenticated:
            self._login_attempts = 0
            self._last_login = datetime.utcnow()
        else:
            self._login_attempts += 1
        
        return is_authenticated
    
    def activate(self) -> None:
        """Activar usuario"""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Desactivar usuario"""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def change_role(self, new_role: UserRole) -> None:
        """Cambiar rol del usuario"""
        self.role = new_role
        self.updated_at = datetime.utcnow()
    
    def change_password(self, new_hashed_password: str) -> None:
        """Cambiar contraseña"""
        if not new_hashed_password:
            raise BusinessRuleException(
                "La nueva contraseña no puede estar vacía",
                "password_empty"
            )
        
        self.hashed_password = new_hashed_password
        self.updated_at = datetime.utcnow()
        self._login_attempts = 0  # Resetear intentos fallidos
    
    def get_login_info(self) -> Dict[str, Any]:
        """Obtener información de login para auditoría"""
        return {
            "login_attempts": self._login_attempts,
            "last_login": self._last_login.isoformat() if self._last_login else None,
            "is_active": self.is_active,
            "role": self.role.value,
        }
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convertir a diccionario para serialización"""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "permissions": {
                "can_manage_products": self.can_perform_action("create_product"),
                "can_manage_inventory": self.can_perform_action("register_movement"),
                "can_view_reports": self.can_perform_action("view_reports"),
                "can_manage_users": self.can_perform_action("create_user"),
            }
        }
        
        if include_sensitive:
            data["hashed_password"] = self.hashed_password
            data.update(self.get_login_info())
            
        return data
    
    @classmethod
    def create(
        cls,
        username: str,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        role: UserRole = UserRole.VIEWER,
        is_active: bool = True
    ) -> 'User':
        """
        Factory method para crear un nuevo usuario.
        """
        return cls(
            username=username,
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_active=is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )