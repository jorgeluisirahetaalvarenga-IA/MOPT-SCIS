"""
Entidad Producto - Pura lógica de negocio sin dependencias externas
Representa el concepto central del dominio: un producto en inventario

Características de una Entidad en Clean Architecture:
1. Tiene identidad (id)
2. Tiene estado que cambia en el tiempo
3. Tiene métodos que definen su comportamiento
4. Es independiente de frameworks y bases de datos
5. Implementa reglas de negocio
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

from ....app.core.exceptions import BusinessRuleException
from ....app.domain.exceptions import (
    InsufficientStockError,
    StockExceedsMaximumError,
    InvalidMovementTypeError
)


@dataclass
class Product:
    """
    Entidad Producto que representa un ítem en inventario.
    Contiene toda la lógica de negocio relacionada con productos.
    
    """
    id: Optional[int] = None
    code: str = ""
    name: str = ""
    description: Optional[str] = None
    current_stock: int = 0
    min_stock: int = 0
    max_stock: int = 1000
    unit: str = "unidades"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Para auditoría y trazabilidad
    _version: int = 0  # Para control de concurrencia optimista
    _domain_events: list = None  # Para Domain Events (Event Sourcing)
    
    def __post_init__(self):
        """
        Validaciones automáticas al crear la entidad.
        Garantiza que la entidad siempre esté en estado válido.
        """
        self._validate()
        if self._domain_events is None:
            self._domain_events = []
    
    def _validate(self) -> None:
        """
        Validar invariantes de la entidad.
        Un invariante es una condición que siempre debe ser verdadera.
        
        Raises:
            BusinessRuleException: Si se viola algún invariante
        """
        # Stock no puede ser negativo
        if self.current_stock < 0:
            raise BusinessRuleException(
                "El stock no puede ser negativo",
                "stock_non_negative",
                {"current_stock": self.current_stock}
            )
        
        # Stock mínimo no puede ser negativo
        if self.min_stock < 0:
            raise BusinessRuleException(
                "El stock mínimo no puede ser negativo",
                "min_stock_non_negative",
                {"min_stock": self.min_stock}
            )
        
        # Stock máximo debe ser mayor o igual al mínimo
        if self.max_stock < self.min_stock:
            raise BusinessRuleException(
                "El stock máximo debe ser mayor o igual al mínimo",
                "max_greater_than_min",
                {
                    "min_stock": self.min_stock,
                    "max_stock": self.max_stock,
                    "difference": self.max_stock - self.min_stock
                }
            )
        
        # Código es requerido
        if not self.code.strip():
            raise BusinessRuleException(
                "El código del producto es requerido",
                "code_required"
            )
        
        # Nombre es requerido
        if not self.name.strip():
            raise BusinessRuleException(
                "El nombre del producto es requerido",
                "name_required"
            )
        
        # Unidad es requerida
        if not self.unit.strip():
            raise BusinessRuleException(
                "La unidad de medida es requerida",
                "unit_required"
            )
    
    def apply_stock_movement(self, quantity: int, movement_type: str) -> int:
       
        # Validar cantidad positiva
        if quantity <= 0:
            raise BusinessRuleException(
                "La cantidad debe ser positiva",
                "quantity_positive",
                {"quantity": quantity}
            )
        
        # Validar tipo de movimiento
        if movement_type not in ["IN", "OUT"]:
            raise InvalidMovementTypeError(movement_type)
        
        old_stock = self.current_stock
        
        if movement_type == "IN":
            # ENTRADA de stock
            new_stock = old_stock + quantity
            
            # Regla de negocio: No exceder el stock máximo
            if self.max_stock > 0 and new_stock > self.max_stock:
                raise StockExceedsMaximumError(
                    product_id=self.id if self.id else 0,
                    current=new_stock,
                    max_allowed=self.max_stock
                )
            
            self.current_stock = new_stock
            
        else:  # OUT
            # SALIDA de stock
            new_stock = old_stock - quantity
            
            # Regla de negocio fundamental: Stock no puede ser negativo
            if new_stock < 0:
                raise InsufficientStockError(
                    product_id=self.id if self.id else 0,
                    available=old_stock,
                    required=quantity
                )
            
            self.current_stock = new_stock
        
        # Actualizar timestamp y versión
        self.updated_at = datetime.utcnow()
        self._version += 1
        
        # Registrar evento de dominio (para Event Sourcing)
        self._record_domain_event({
            "event_type": "StockMovementApplied",
            "product_id": self.id,
            "old_stock": old_stock,
            "new_stock": self.current_stock,
            "quantity": quantity,
            "movement_type": movement_type,
            "timestamp": self.updated_at,
            "version": self._version
        })
        
        return old_stock
    
    def needs_reorder(self, buffer_percentage: float = 0.1) -> bool:
        """
        Determina si el producto necesita reorden.
        
        Args:
            buffer_percentage: Porcentaje de buffer para alerta temprana (0-1)
            
        Returns:
            bool: True si el stock está por debajo del mínimo + buffer
        """
        buffer_amount = self.min_stock * buffer_percentage
        threshold = self.min_stock + buffer_amount
        return self.current_stock <= threshold
    
    def get_stock_percentage(self) -> float:
        """
        Obtiene el porcentaje de stock relativo al máximo.
        
        Returns:
            float: Porcentaje (0-100) o 0 si max_stock es 0
        """
        if self.max_stock <= 0:
            return 0.0
        return (self.current_stock / self.max_stock) * 100
    
    def is_stock_low(self) -> bool:
        """Determina si el stock está por debajo del mínimo"""
        return self.current_stock < self.min_stock
    
    def is_stock_high(self, threshold_percentage: float = 90.0) -> bool:
        """
        Determina si el stock está cerca del máximo.
        
        Args:
            threshold_percentage: Porcentaje umbral (default 90%)
            
        Returns:
            bool: True si el stock está por encima del umbral
        """
        if self.max_stock <= 0:
            return False
        percentage = (self.current_stock / self.max_stock) * 100
        return percentage >= threshold_percentage
    
    def calculate_reorder_quantity(self, target_percentage: float = 80.0) -> int:
        """
        Calcula la cantidad a reordenar para alcanzar el porcentaje objetivo.
        
        Args:
            target_percentage: Porcentaje objetivo del máximo (default 80%)
            
        Returns:
            int: Cantidad a ordenar
        """
        if self.max_stock <= 0:
            return 0
        
        target_stock = (target_percentage / 100) * self.max_stock
        reorder_quantity = max(0, int(target_stock - self.current_stock))
        
        return reorder_quantity
    
    def _record_domain_event(self, event_data: dict) -> None:
        """Registrar evento de dominio para Event Sourcing"""
        self._domain_events.append(event_data)
    
    def get_domain_events(self) -> list:
        """Obtener eventos de dominio pendientes"""
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Limpiar eventos de dominio después de persistir"""
        self._domain_events.clear()
    
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
            "stock_percentage": self.get_stock_percentage(),
            "needs_reorder": self.needs_reorder(),
            "is_stock_low": self.is_stock_low(),
            "is_stock_high": self.is_stock_high(),
        }
    
    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        description: str = None,
        current_stock: int = 0,
        min_stock: int = 0,
        max_stock: int = 1000,
        unit: str = "unidades"
    ) -> 'Product':
        """
        Factory method para crear un nuevo producto.
        Centraliza la lógica de creación.
        """
        return cls(
            code=code,
            name=name,
            description=description,
            current_stock=current_stock,
            min_stock=min_stock,
            max_stock=max_stock,
            unit=unit,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )