"""
Modelos SQLAlchemy para persistencia en base de datos.
ESTA ES LA CAPA DE PERSISTENCIA, NO CONFUNDIR CON ENTIDADES DE DOMINIO.

Principios:
- Cada modelo representa una tabla en la base de datos
- Relaciones definidas con SQLAlchemy ORM
- Validaciones a nivel de base de datos con CheckConstraint
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint, Boolean, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base

# ==================== ENUMS ====================
class UserRole(str, enum.Enum):
    """
    Roles de usuario en el sistema.
    
    Jerarquía de permisos (de mayor a menor):
    1. ADMIN: Acceso completo al sistema
    2. MANAGER: Gestionar inventario y reportes
    3. OPERATOR: Realizar movimientos de inventario
    4. VIEWER: Solo consultas y visualización
    """
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"


# ==================== MODELO PRODUCTO ====================
class Product(Base):
    """
    Modelo de persistencia para productos.
    Representa un ítem en el inventario del sistema.
    
    Campos:
    - code: Código único del producto (SKU)
    - name: Nombre del producto
    - description: Descripción detallada
    - current_stock: Stock actual en inventario
    - min_stock: Stock mínimo permitido (para alertas)
    - max_stock: Stock máximo permitido (para optimización)
    - unit: Unidad de medida (unidades, kg, litros, etc.)
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    current_stock = Column(Integer, default=0, nullable=False)
    min_stock = Column(Integer, default=0, nullable=False)
    max_stock = Column(Integer, default=1000, nullable=False)
    unit = Column(String(20), default="unidades", nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relación uno-a-muchos con movimientos
    movements = relationship(
        "InventoryMovement",
        back_populates="product",
        cascade="all, delete-orphan",  # Eliminar movimientos si se elimina producto
        lazy="dynamic"  # Carga perezosa para mejor performance
    )
    
    # Constraints a nivel de base de datos
    __table_args__ = (
        # El stock no puede ser negativo
        CheckConstraint('current_stock >= 0', name='check_stock_non_negative'),
        # El stock mínimo no puede ser negativo
        CheckConstraint('min_stock >= 0', name='check_min_stock_non_negative'),
        # El máximo debe ser mayor o igual al mínimo
        CheckConstraint('max_stock >= min_stock', name='check_max_greater_than_min'),
        # El código debe ser único (ya cubierto por unique=True pero se documenta)
    )
    
    def __repr__(self) -> str:
        return f"<Product(id={self.id}, code='{self.code}', name='{self.name}', stock={self.current_stock})>"
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización"""
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "current_stock": self.current_stock,
            "min_stock": self.min_stock,
            "max_stock": self.max_stock,
            "unit": self.unit,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ==================== MODELO USUARIO ====================
class User(Base):
    """
    Modelo de persistencia para usuarios del sistema.
    Maneja autenticación, autorización y auditoría.
    
    Campos:
    - username: Nombre de usuario único
    - email: Email único
    - hashed_password: Contraseña hasheada con bcrypt
    - full_name: Nombre completo
    - role: Rol del usuario (determina permisos)
    - is_active: Estado del usuario (activo/inactivo)
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relación uno-a-muchos con movimientos
    movements = relationship(
        "InventoryMovement",
        back_populates="user",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"
    
    def has_permission(self, required_role: UserRole) -> bool:
        """
        Verificar si el usuario tiene el rol requerido o superior.
        
        Args:
            required_role: Rol mínimo requerido
            
        Returns:
            bool: True si el usuario tiene permisos suficientes
        """
        role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.MANAGER: 3,
            UserRole.OPERATOR: 2,
            UserRole.VIEWER: 1
        }
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
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
        }
        
        if include_sensitive:
            data["hashed_password"] = self.hashed_password
            
        return data


# ==================== MODELO MOVIMIENTO INVENTARIO ====================
class InventoryMovement(Base):
    """
    Modelo de persistencia para movimientos de inventario.
    Registra toda la auditoría de cambios en el stock.
    
    Campos:
    - product_id: Referencia al producto
    - quantity: Cantidad movida (positiva)
    - movement_type: Tipo de movimiento (IN/OUT)
    - reason: Razón del movimiento
    - previous_stock: Stock antes del movimiento
    - new_stock: Stock después del movimiento
    - user_id: Usuario que realizó el movimiento
    """
    __tablename__ = "inventory_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    movement_type = Column(String(10), nullable=False)  # "IN" o "OUT"
    reason = Column(String(255), nullable=False)
    previous_stock = Column(Integer, nullable=True)
    new_stock = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relaciones muchos-a-uno
    product = relationship("Product", back_populates="movements")
    user = relationship("User", back_populates="movements")
    
    # Constraints a nivel de base de datos
    __table_args__ = (
        # La cantidad no puede ser cero
        CheckConstraint('quantity != 0', name='check_quantity_not_zero'),
        # La cantidad debe ser positiva
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        # Solo tipos válidos
        CheckConstraint('movement_type IN ("IN", "OUT")', name='check_movement_type'),
    )
    
    def __repr__(self) -> str:
        return f"<InventoryMovement(id={self.id}, product_id={self.product_id}, type='{self.movement_type}', qty={self.quantity})>"
    
    def to_dict(self) -> dict:
        """Convertir a diccionario para serialización"""
        return {
            "id": self.id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "movement_type": self.movement_type,
            "reason": self.reason,
            "previous_stock": self.previous_stock,
            "new_stock": self.new_stock,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "product": self.product.to_dict() if self.product else None,
            "user": self.user.to_dict() if self.user else None,
        }