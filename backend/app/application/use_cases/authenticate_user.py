"""
Caso de uso: Autenticar usuario.
Maneja la lógica de autenticación y generación de tokens.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ....app.core.exceptions import ValidationException, AuthenticationException
from ....app.domain.entities.user import User
from ....app.domain.exceptions import InvalidCredentialsError, UserInactiveError
from ....app.application.ports.user_repository import UserRepository


@dataclass
class AuthenticateUserRequest:
    """DTO para autenticación de usuario"""
    username: str
    password: str


@dataclass
class AuthenticateUserResponse:
    """DTO para respuesta de autenticación"""
    success: bool
    user_id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    access_token: str
    token_type: str
    expires_in: int
    expires_at: str


class AuthenticateUserUseCase:
    """
    Caso de uso para autenticación de usuarios.
    """
    
    def __init__(
        self,
        user_repository: UserRepository,
        token_generator,  # Dependencia para generar tokens
        password_verifier  # Dependencia para verificar passwords
    ):
        self.user_repo = user_repository
        self.token_generator = token_generator
        self.password_verifier = password_verifier
    
    def execute(self, request: AuthenticateUserRequest) -> AuthenticateUserResponse:
        
        # 1. Validar entrada
        self._validate_request(request)
        
        # 2. Buscar usuario
        user = self.user_repo.find_by_username(request.username)
        if not user:
            raise InvalidCredentialsError(request.username)
        
        # 3. Verificar estado del usuario
        if not user.is_active:
            raise UserInactiveError(user.id if user.id else 0)
        
        # 4. Autenticar (la entidad User maneja la lógica)
        try:
            is_authenticated = user.authenticate(
                request.password,
                self.password_verifier
            )
        except Exception as e:
            raise AuthenticationException(f"Error en autenticación: {str(e)}")
        
        if not is_authenticated:
            raise InvalidCredentialsError(request.username)
        
        # 5. Generar token JWT
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "email": user.email
        }
        
        access_token = self.token_generator(token_data)
        expires_in = 1800  # 30 minutos en segundos
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # 6. Retornar respuesta
        return AuthenticateUserResponse(
            success=True,
            user_id=user.id if user.id else 0,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            expires_at=expires_at.isoformat()
        )
    
    def _validate_request(self, request: AuthenticateUserRequest):
        """Validaciones de entrada"""
        errors = []
        
        if not request.username or not request.username.strip():
            errors.append({
                "field": "username",
                "message": "El nombre de usuario es requerido"
            })
        
        if not request.password:
            errors.append({
                "field": "password",
                "message": "La contraseña es requerida"
            })
        
        if errors:
            raise ValidationException(
                message="Errores de validación en credenciales",
                details={"errors": errors}
            )