"""
Entidad Movimiento de Inventario.
Representa un cambio en el stock de un producto para auditoría y trazabilidad.

Características:
- Entity con identidad
- Inmutable después de creado (Value Object-like)
- Para auditoría y trazabilidad completa
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

from ....app.core.exceptions import BusinessRuleException
from ....app.domain.exceptions import InvalidMovementTypeError


@dataclass(frozen=False)  # No frozen porque necesitamos asignar id después de persistir
class InventoryMovement:
    """
    Representa un movimiento de inventario (entrada o salida).
    Es una entidad de auditoría que registra todos los cambios.
    
    Atributos:
    - id: Identificador único (asignado por persistencia)
    - product_id: ID del producto afectado
    - quantity: Cantidad movida (siempre positiva)
    - movement_type: "IN" para entrada, "OUT" para salida
    - reason: Razón del movimiento (auditoría)
    - previous_stock: Stock antes del movimiento
    - new_stock: Stock después del movimiento
    - user_id: ID del usuario que realizó el movimiento
    - created_at: Timestamp del movimiento
    """
    id: Optional[int] = None
    product_id: int = 0
    quantity: int = 0
    movement_type: str = ""
    reason: str = ""
    previous_stock: Optional[int] = None
    new_stock: Optional[int] = None
    user_id: int = 0
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validaciones automáticas al crear la entidad"""
        self._validate()
    
    def _validate(self) -> None:
        """
        Validar invariantes de la entidad de movimiento.
        
        Raises:
            BusinessRuleException: Si se viola algún invariante
        """
        # Cantidad debe ser positiva
        if self.quantity <= 0:
            raise BusinessRuleException(
                "La cantidad del movimiento debe ser positiva",
                "movement_quantity_positive",
                {"quantity": self.quantity}
            )
        
        # Tipo de movimiento válido
        if self.movement_type not in ["IN", "OUT"]:
            raise InvalidMovementTypeError(self.movement_type)
        
        # Razón es requerida para auditoría
        if not self.reason.strip():
            raise BusinessRuleException(
                "La razón del movimiento es requerida para auditoría",
                "reason_required"
            )
        
        # Product ID válido
        if self.product_id <= 0:
            raise BusinessRuleException(
                "ID de producto inválido",
                "valid_product_id",
                {"product_id": self.product_id}
            )
        
        # User ID válido
        if self.user_id <= 0:
            raise BusinessRuleException(
                "ID de usuario inválido",
                "valid_user_id",
                {"user_id": self.user_id}
            )
        
        # Validar consistencia de stocks si ambos están presentes
        if self.previous_stock is not None and self.new_stock is not None:
            if self.movement_type == "IN":
                expected_new = self.previous_stock + self.quantity
            else:  # OUT
                expected_new = self.previous_stock - self.quantity
            
            if self.new_stock != expected_new:
                raise BusinessRuleException(
                    "Inconsistencia en cálculos de stock",
                    "stock_calculation_inconsistent",
                    {
                        "previous": self.previous_stock,
                        "quantity": self.quantity,
                        "expected_new": expected_new,
                        "actual_new": self.new_stock,
                        "movement_type": self.movement_type
                    }
                )
    
    @classmethod
    def create_from_movement(
        cls,
        product_id: int,
        quantity: int,
        movement_type: str,
        reason: str,
        previous_stock: int,
        new_stock: int,
        user_id: int
    ) -> 'InventoryMovement':
        """
        Factory method para crear movimiento con datos completos.
        
        Args:
            product_id: ID del producto
            quantity: Cantidad movida
            movement_type: "IN" o "OUT"
            reason: Razón del movimiento
            previous_stock: Stock antes del movimiento
            new_stock: Stock después del movimiento
            user_id: ID del usuario
            
        Returns:
            InventoryMovement: Instancia validada
        """
        return cls(
            product_id=product_id,
            quantity=quantity,
            movement_type=movement_type,
            reason=reason,
            previous_stock=previous_stock,
            new_stock=new_stock,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
    
    @classmethod
    def create_in_movement(
        cls,
        product_id: int,
        quantity: int,
        reason: str,
        previous_stock: int,
        user_id: int
    ) -> 'InventoryMovement':
        """
        Factory method específico para movimiento de ENTRADA.
        Calcula automáticamente el nuevo stock.
        """
        new_stock = previous_stock + quantity
        return cls.create_from_movement(
            product_id=product_id,
            quantity=quantity,
            movement_type="IN",
            reason=reason,
            previous_stock=previous_stock,
            new_stock=new_stock,
            user_id=user_id
        )
    
    @classmethod
    def create_out_movement(
        cls,
        product_id: int,
        quantity: int,
        reason: str,
        previous_stock: int,
        user_id: int
    ) -> 'InventoryMovement':
        """
        Factory method específico para movimiento de SALIDA.
        Calcula automáticamente el nuevo stock.
        """
        new_stock = previous_stock - quantity
        return cls.create_from_movement(
            product_id=product_id,
            quantity=quantity,
            movement_type="OUT",
            reason=reason,
            previous_stock=previous_stock,
            new_stock=new_stock,
            user_id=user_id
        )
    
    def get_movement_description(self) -> str:
        """Obtener descripción legible del movimiento"""
        action = "entrada" if self.movement_type == "IN" else "salida"
        return f"{action} de {self.quantity} unidades - {self.reason}"
    
    def get_stock_change(self) -> int:
        """Obtener el cambio neto de stock"""
        if self.movement_type == "IN":
            return self.quantity
        else:
            return -self.quantity
    
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
            "description": self.get_movement_description(),
            "stock_change": self.get_stock_change(),
        }
    
    def is_in_movement(self) -> bool:
        """Verificar si es movimiento de entrada"""
        return self.movement_type == "IN"
    
    def is_out_movement(self) -> bool:
        """Verificar si es movimiento de salida"""
        return self.movement_type == "OUT"