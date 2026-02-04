"""
Caso de uso: Registrar movimiento de inventario.
Coordinación de la lógica de aplicación para registrar un movimiento.

Responsabilidades:
1. Validar datos de entrada
2. Coordinar entidades de dominio
3. Gestionar transacciones
4. Manejar errores de negocio
"""
from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime

from ....app.core.exceptions import ValidationException, NotFoundException
from ....app.domain.entities.product import Product
from ....app.domain.entities.inventory_movement import InventoryMovement
from ....app.domain.entities.user import User
from ....app.domain.exceptions import (
    ProductNotFoundError,
    InsufficientStockError,
    StockExceedsMaximumError,
    InvalidMovementTypeError,
    UserNotFoundError
)
from ....app.application.ports.product_repository import ProductRepository
from ....app.application.ports.movement_repository import MovementRepository
from ....app.application.ports.user_repository import UserRepository


@dataclass
class RegisterMovementRequest:
    """
    DTO (Data Transfer Object) para entrada del caso de uso.
    Contiene todos los datos necesarios para registrar un movimiento.
    """
    product_id: int
    quantity: int
    movement_type: str  # "IN" o "OUT"
    reason: str
    user_id: int


@dataclass
class RegisterMovementResponse:
    """
    DTO para salida del caso de uso.
    Contiene todos los datos resultantes del movimiento.
    """
    success: bool
    movement_id: int
    product_id: int
    product_code: str
    product_name: str
    movement_type: str
    quantity: int
    previous_stock: int
    new_stock: int
    user_id: int
    username: str
    timestamp: str
    message: str


class RegisterMovementUseCase:
    """
    Caso de uso para registrar movimiento de inventario.
    Contiene toda la lógica de aplicación coordinando el dominio.
    
    Flujo:
    1. Validar request
    2. Verificar existencia de usuario
    3. Obtener y bloquear producto
    4. Aplicar movimiento (dominio puro)
    5. Crear registro de auditoría
    6. Persistir cambios
    7. Retornar respuesta
    """
    
    def __init__(
        self,
        product_repository: ProductRepository,
        movement_repository: MovementRepository,
        user_repository: UserRepository
    ):
        self.product_repo = product_repository
        self.movement_repo = movement_repository
        self.user_repo = user_repository
    
    def execute(self, request: RegisterMovementRequest) -> RegisterMovementResponse:
        """
        Ejecutar el caso de uso.
        
        Args:
            request: Datos del movimiento a registrar
            
        Returns:
            RegisterMovementResponse: Resultado del movimiento
            
        Raises:
            ValidationException: Si los datos son inválidos
            NotFoundException: Si no se encuentra recurso
            BusinessRuleException: Si se viola regla de negocio
        """
        # 1. Validar entrada a nivel de aplicación
        self._validate_request(request)
        
        # 2. Verificar que el usuario existe y está activo
        user = self.user_repo.find_by_id(request.user_id)
        if not user or not user.is_active:
            raise UserNotFoundError(user_id=request.user_id)
        
        # 3. Obtener producto con bloqueo para concurrencia
        product = self.product_repo.find_by_id_with_lock(request.product_id)
        if not product:
            raise ProductNotFoundError(request.product_id)
        
        # 4. Aplicar movimiento (esto es dominio puro)
        previous_stock = product.current_stock
        
        try:
            # La entidad Producto maneja toda la lógica de negocio
            product.apply_stock_movement(request.quantity, request.movement_type)
        except (InsufficientStockError, StockExceedsMaximumError, InvalidMovementTypeError) as e:
            # Re-lanzar excepciones de dominio
            raise e
        except Exception as e:
            # Mapear otras excepciones a ValidationException
            raise ValidationException(str(e))
        
        # 5. Crear movimiento de auditoría
        movement = InventoryMovement.create_from_movement(
            product_id=request.product_id,
            quantity=request.quantity,
            movement_type=request.movement_type,
            reason=request.reason,
            previous_stock=previous_stock,
            new_stock=product.current_stock,
            user_id=request.user_id
        )
        
        # 6. Persistir cambios (esto podría estar en una transacción)
        updated_product = self.product_repo.save(product)
        saved_movement = self.movement_repo.save(movement)
        
        # 7. Retornar respuesta
        return RegisterMovementResponse(
            success=True,
            movement_id=saved_movement.id if saved_movement.id else 0,
            product_id=updated_product.id if updated_product.id else 0,
            product_code=updated_product.code,
            product_name=updated_product.name,
            movement_type=request.movement_type,
            quantity=request.quantity,
            previous_stock=previous_stock,
            new_stock=updated_product.current_stock,
            user_id=request.user_id,
            username=user.username,
            timestamp=movement.created_at.isoformat() if movement.created_at else datetime.utcnow().isoformat(),
            message=f"Movimiento de {request.quantity} unidades registrado exitosamente"
        )
    
    def _validate_request(self, request: RegisterMovementRequest):
        """
        Validaciones a nivel de aplicación.
        Estas son validaciones de formato, no de reglas de negocio.
        
        Raises:
            ValidationException: Si alguna validación falla
        """
        errors = []
        
        # Validar cantidad
        if request.quantity <= 0:
            errors.append({
                "field": "quantity",
                "message": "La cantidad debe ser mayor a cero",
                "value": request.quantity
            })
        
        # Validar tipo de movimiento
        if request.movement_type not in ["IN", "OUT"]:
            errors.append({
                "field": "movement_type",
                "message": "Tipo de movimiento debe ser 'IN' o 'OUT'",
                "value": request.movement_type,
                "valid_values": ["IN", "OUT"]
            })
        
        # Validar razón
        if not request.reason or not request.reason.strip():
            errors.append({
                "field": "reason",
                "message": "La razón del movimiento es requerida",
                "value": request.reason
            })
        elif len(request.reason.strip()) < 3:
            errors.append({
                "field": "reason",
                "message": "La razón debe tener al menos 3 caracteres",
                "value": request.reason
            })
        
        # Validar IDs
        if request.product_id <= 0:
            errors.append({
                "field": "product_id",
                "message": "ID de producto inválido",
                "value": request.product_id
            })
        
        if request.user_id <= 0:
            errors.append({
                "field": "user_id",
                "message": "ID de usuario inválido",
                "value": request.user_id
            })
        
        # Si hay errores, lanzar excepción
        if errors:
            raise ValidationException(
                message="Errores de validación en la solicitud",
                details={"errors": errors}
            )