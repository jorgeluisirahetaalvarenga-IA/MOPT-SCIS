"""
Router para autenticación y gestión de usuarios.
Endpoints para login, registro, perfil y gestión de usuarios.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

from ...infrastructure.database.session import get_db
from ...infrastructure.auth.jwt_handler import JWTHandler
from ...app.application.dtos.schemas import (
    LoginRequest, Token, UserCreate, UserResponse, UserUpdate,
    SuccessResponse, ErrorResponse, PaginatedResponse
)
from ...api.dependencies import (
    get_current_user, require_admin, require_viewer,
    get_user_repository, get_audit_logger
)
from ...infrastructure.database.models import User as UserModel, UserRole
from ...app.domain.entities.user import User as UserEntity, UserRole as DomainUserRole
from ...app.application.use_cases.authenticate_user import (
    AuthenticateUserUseCase, AuthenticateUserRequest
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    audit_logger = Depends(get_audit_logger)
):

    try:
        # Crear caso de uso
        use_case = AuthenticateUserUseCase(
            user_repository=get_user_repository(db),
            token_generator=lambda data: JWTHandler.create_access_token(data),
            password_verifier=JWTHandler.verify_password
        )
        
        # Ejecutar autenticación
        response = use_case.execute(
            AuthenticateUserRequest(
                username=form_data.username,
                password=form_data.password
            )
        )
        
        return {
            "access_token": response.access_token,
            "token_type": response.token_type,
            "expires_in": response.expires_in,
            "user_role": response.role,
            "user_id": response.user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log_auth_failure(form_data.username, str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    
    try:
        # Verificar que el usuario no exista
        user_repo = get_user_repository(db)
        
        if user_repo.exists_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya existe"
            )
        
        if user_repo.exists_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
        
        # Crear entidad de dominio
        user_entity = UserEntity.create(
            username=user_data.username,
            email=user_data.email,
            hashed_password=JWTHandler.get_password_hash(user_data.password),
            full_name=user_data.full_name,
            role=DomainUserRole(user_data.role),
            is_active=True
        )
        
        # Persistir usuario
        saved_user = user_repo.save(user_entity)
        
        # Convertir a respuesta
        return UserResponse(
            id=saved_user.id if saved_user.id else 0,
            username=saved_user.username,
            email=saved_user.email,
            full_name=saved_user.full_name,
            role=saved_user.role.value,
            is_active=saved_user.is_active,
            created_at=saved_user.created_at if saved_user.created_at else None,
            updated_at=saved_user.updated_at,
            permissions={
                "can_manage_products": saved_user.can_perform_action("create_product"),
                "can_manage_inventory": saved_user.can_perform_action("register_movement"),
                "can_view_reports": saved_user.can_perform_action("view_reports"),
                "can_manage_users": saved_user.can_perform_action("create_user"),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar usuario: {str(e)}"
        )

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    
    try:
        user_repo = get_user_repository(db)
        users = user_repo.find_all(skip=skip, limit=limit)
        
        return [
            UserResponse(
                id=user.id if user.id else 0,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at if user.created_at else None,
                updated_at=user.updated_at,
                permissions={
                    "can_manage_products": user.can_perform_action("create_product"),
                    "can_manage_inventory": user.can_perform_action("register_movement"),
                    "can_view_reports": user.can_perform_action("view_reports"),
                    "can_manage_users": user.can_perform_action("create_user"),
                }
            )
            for user in users
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar usuarios: {str(e)}"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    
    try:
        user_repo = get_user_repository(db)
        
        # Buscar usuario
        user = user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # Actualizar campos proporcionados
        if user_data.email is not None:
            # Verificar que el email no esté en uso por otro usuario
            existing = user_repo.find_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está en uso por otro usuario"
                )
            user.email = user_data.email
        
        if user_data.full_name is not None:
            user.full_name = user_data.full_name
        
        if user_data.role is not None:
            user.role = DomainUserRole(user_data.role)
        
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        # Guardar cambios
        updated_user = user_repo.save(user)
        
        return UserResponse(
            id=updated_user.id if updated_user.id else 0,
            username=updated_user.username,
            email=updated_user.email,
            full_name=updated_user.full_name,
            role=updated_user.role.value,
            is_active=updated_user.is_active,
            created_at=updated_user.created_at if updated_user.created_at else None,
            updated_at=updated_user.updated_at,
            permissions={
                "can_manage_products": updated_user.can_perform_action("create_product"),
                "can_manage_inventory": updated_user.can_perform_action("register_movement"),
                "can_view_reports": updated_user.can_perform_action("view_reports"),
                "can_manage_users": updated_user.can_perform_action("create_user"),
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar usuario: {str(e)}"
        )


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_admin)
):
    """
    Eliminar usuario (solo administradores).
    
    - **user_id**: ID del usuario a eliminar
    
    Nota: No se puede eliminar a sí mismo
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminarse a sí mismo"
        )
    
    try:
        user_repo = get_user_repository(db)
        
        # Buscar usuario
        user = user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # Desactivar usuario en lugar de eliminar (soft delete)
        user.is_active = False
        user_repo.save(user)
        
        return SuccessResponse(
            message=f"Usuario {user.username} desactivado exitosamente",
            data={"user_id": user_id, "username": user.username}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al desactivar usuario: {str(e)}"
        )