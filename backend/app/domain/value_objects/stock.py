"""
Value Object para Stock - Inmutable y con validaciones.
Un Value Object representa un concepto del dominio que no tiene identidad,
solo se define por sus atributos y es inmutable.

Características:
- Inmutable (frozen=True)
- Sin identidad (no tiene ID)
- Auto-validado
- Solo se define por sus atributos
"""
from dataclasses import dataclass
from typing import Optional

from ....app.core.exceptions import BusinessRuleException
from ....app.domain.exceptions import InsufficientStockError


@dataclass(frozen=True)  # Inmutable
class Stock:
    """
    Value Object que representa una cantidad de stock.
    Es inmutable y siempre válido.
    
    Atributos:
    - quantity: Cantidad (siempre no-negativa)
    - unit: Unidad de medida (ej: "unidades", "kg", "litros")
    """
    quantity: int
    unit: str = "unidades"
    
    def __post_init__(self):
        """Validar que el stock sea válido"""
        # Validar cantidad no negativa
        if self.quantity < 0:
            raise BusinessRuleException(
                "La cantidad de stock no puede ser negativa",
                "stock_negative",
                {"quantity": self.quantity}
            )
        
        # Validar unidad no vacía
        if not self.unit.strip():
            raise BusinessRuleException(
                "La unidad es requerida",
                "unit_required"
            )
    
    def add(self, other: 'Stock') -> 'Stock':
        """
        Sumar dos stocks (deben tener misma unidad).
        
        Args:
            other: Otro stock a sumar
            
        Returns:
            Stock: Nuevo stock con la suma
            
        Raises:
            BusinessRuleException: Si las unidades no coinciden
        """
        if self.unit != other.unit:
            raise BusinessRuleException(
                f"No se pueden sumar stocks con unidades diferentes: {self.unit} vs {other.unit}",
                "unit_mismatch"
            )
        
        return Stock(self.quantity + other.quantity, self.unit)
    
    def subtract(self, other: 'Stock') -> 'Stock':
        """
        Restar dos stocks (deben tener misma unidad).
        
        Args:
            other: Otro stock a restar
            
        Returns:
            Stock: Nuevo stock con la resta
            
        Raises:
            BusinessRuleException: Si las unidades no coinciden
            InsufficientStockError: Si el resultado sería negativo
        """
        if self.unit != other.unit:
            raise BusinessRuleException(
                f"No se pueden restar stocks con unidades diferentes: {self.unit} vs {other.unit}",
                "unit_mismatch"
            )
        
        new_quantity = self.quantity - other.quantity
        if new_quantity < 0:
            raise InsufficientStockError(
                product_id=0,  # No aplica para Value Object puro
                available=self.quantity,
                required=other.quantity
            )
        
        return Stock(new_quantity, self.unit)
    
    def multiply(self, factor: float) -> 'Stock':
        """
        Multiplicar stock por un factor.
        
        Args:
            factor: Factor de multiplicación
            
        Returns:
            Stock: Nuevo stock multiplicado
        """
        if factor < 0:
            raise BusinessRuleException(
                "El factor de multiplicación no puede ser negativo",
                "negative_factor",
                {"factor": factor}
            )
        
        new_quantity = int(self.quantity * factor)
        return Stock(new_quantity, self.unit)
    
    def is_positive(self) -> bool:
        """Verificar si el stock es positivo"""
        return self.quantity > 0
    
    def is_zero(self) -> bool:
        """Verificar si el stock es cero"""
        return self.quantity == 0
    
    def is_greater_than(self, other: 'Stock') -> bool:
        """Comparar si es mayor que otro stock"""
        if self.unit != other.unit:
            raise BusinessRuleException(
                "No se pueden comparar stocks con unidades diferentes",
                "unit_mismatch_comparison"
            )
        return self.quantity > other.quantity
    
    def is_less_than(self, other: 'Stock') -> bool:
        """Comparar si es menor que otro stock"""
        if self.unit != other.unit:
            raise BusinessRuleException(
                "No se pueden comparar stocks con unidades diferentes",
                "unit_mismatch_comparison"
            )
        return self.quantity < other.quantity
    
    def equals(self, other: 'Stock') -> bool:
        """Verificar igualdad con otro stock"""
        if self.unit != other.unit:
            return False
        return self.quantity == other.quantity
    
    def to_dict(self) -> dict:
        """Convertir a diccionario"""
        return {
            "quantity": self.quantity,
            "unit": self.unit,
            "is_positive": self.is_positive(),
            "is_zero": self.is_zero(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Stock':
        """Crear Stock a partir de diccionario"""
        return cls(
            quantity=data.get("quantity", 0),
            unit=data.get("unit", "unidades")
        )
    
    @classmethod
    def zero(cls, unit: str = "unidades") -> 'Stock':
        """Crear stock cero"""
        return cls(quantity=0, unit=unit)
    
    def __str__(self) -> str:
        """Representación legible"""
        return f"{self.quantity} {self.unit}"
    
    def __repr__(self) -> str:
        """Representación para debugging"""
        return f"Stock(quantity={self.quantity}, unit='{self.unit}')"