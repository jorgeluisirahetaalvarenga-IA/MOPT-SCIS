"""
DTOs y Schemas para la capa de aplicación.
Define los formatos de entrada/salida para la API.

Responsabilidades:
- Validación de datos de entrada
- Serialización de datos de salida
- Documentación automática para OpenAPI
"""
from pydantic import BaseModel, Field, validator, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from ....app.domain.entities.user import UserRole as DomainUserRole


# ==================== ENUMS PARA SCHEMAS ====================
class UserRole(str, Enum):
    """Roles de usuario para schemas (mapeo desde dominio)"""
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"
    
    @classmethod
    def from_domain(cls, domain_role: DomainUserRole) -> 'UserRole':
        """Convertir desde dominio"""
        return cls(domain_role.value)


class MovementType(str, Enum):
    """Tipos de movimiento para schemas"""
    IN = "IN"
    OUT = "OUT"


# ==================== PRODUCTOS ====================
class ProductBase(BaseModel):
    """Base para schemas de productos"""
    code: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Código único del producto (SKU)",
        example="PROD-001"
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Nombre del producto",
        example="Laptop Dell Inspiron 15"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Descripción detallada del producto",
        example="Laptop 15.6 pulgadas, Intel Core i5, 8GB RAM, 512GB SSD"
    )
    min_stock: int = Field(
        default=0,
        ge=0,
        description="Stock mínimo permitido (para alertas)",
        example=5
    )
    max_stock: int = Field(
        default=1000,
        ge=0,
        description="Stock máximo permitido",
        example=100
    )
    unit: str = Field(
        default="unidades",
        max_length=20,
        description="Unidad de medida",
        example="unidades"
    )
    
    @validator('max_stock')
    def validate_max_stock(cls, v, values):
        """Validar que max_stock sea mayor o igual a min_stock"""
        if 'min_stock' in values and v < values['min_stock']:
            raise ValueError('max_stock debe ser mayor o igual a min_stock')
        return v
    
    @validator('code')
    def validate_code_format(cls, v):
        """Validar formato del código"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('El código solo puede contener letras, números, guiones y guiones bajos')
        return v


class ProductCreate(ProductBase):
    """Schema para crear producto"""
    current_stock: int = Field(
        default=0,
        ge=0,
        description="Stock inicial del producto",
        example=25
    )


class ProductUpdate(BaseModel):
    """Schema para actualizar producto (campos opcionales)"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    min_stock: Optional[int] = Field(None, ge=0)
    max_stock: Optional[int] = Field(None, ge=0)
    unit: Optional[str] = Field(None, max_length=20)


class ProductResponse(BaseModel):
    """Schema para respuesta de producto"""
    id: int
    code: str
    name: str
    description: Optional[str]
    current_stock: int
    min_stock: int
    max_stock: int
    unit: str
    stock_percentage: float
    needs_reorder: bool
    is_stock_low: bool
    is_stock_high: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True  # Para compatibilidad con ORM


# ==================== MOVIMIENTOS ====================
class InventoryMovementCreate(BaseModel):
    """Schema para crear movimiento"""
    product_id: int = Field(..., gt=0, description="ID del producto")
    quantity: int = Field(..., gt=0, description="Cantidad a mover")
    movement_type: MovementType = Field(..., description="Tipo de movimiento")
    reason: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Razón del movimiento",
        example="Reposición de stock"
    )
    
    @validator('reason')
    def validate_reason(cls, v):
        """Validar que la razón no sea solo espacios"""
        if not v.strip():
            raise ValueError('La razón no puede estar vacía')
        return v


class InventoryMovementResponse(BaseModel):
    """Schema para respuesta de movimiento"""
    id: int
    product_id: int
    quantity: int
    movement_type: str
    reason: str
    previous_stock: Optional[int]
    new_stock: Optional[int]
    user_id: int
    created_at: datetime
    description: str
    stock_change: int
    
    class Config:
        from_attributes = True


# ==================== USUARIOS ====================
class UserBase(BaseModel):
    """Base para schemas de usuarios"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Nombre de usuario único",
        example="jperez"
    )
    email: EmailStr = Field(
        ...,
        description="Email único del usuario",
        example="juan.perez@empresa.com"
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Nombre completo",
        example="Juan Pérez"
    )
    
    @validator('username')
    def validate_username(cls, v):
        """Validar formato del username"""
        if not v.replace('_', '').isalnum():
            raise ValueError('El nombre de usuario solo puede contener letras, números y guiones bajos')
        return v.lower()


class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña (mínimo 8 caracteres)",
        example="SecurePass123!"
    )
    role: UserRole = Field(
        default=UserRole.VIEWER,
        description="Rol del usuario"
    )
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validar fortaleza de contraseña"""
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe tener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe tener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe tener al menos un número')
        return v


class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema para respuesta de usuario"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    permissions: Dict[str, bool]
    
    class Config:
        from_attributes = True


# ==================== AUTENTICACIÓN ====================
class LoginRequest(BaseModel):
    """Schema para login"""
    username: str = Field(..., description="Nombre de usuario")
    password: str = Field(..., description="Contraseña")


class Token(BaseModel):
    """Schema para token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: float
    user_role: str
    user_id: int


# ==================== RESPUESTAS GENÉRICAS ====================
class SuccessResponse(BaseModel):
    """Respuesta genérica de éxito"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Respuesta genérica de error"""
    success: bool = False
    error: str
    detail: str
    code: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PaginatedResponse(BaseModel):
    """Respuesta paginada genérica"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


# ==================== ESTADO DEL INVENTARIO ====================
class InventoryStatusResponse(BaseModel):
    """Schema para estado del inventario"""
    statistics: Dict[str, Any]
    alerts: Dict[str, List[Dict[str, Any]]]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())