"""
Puerto para repositorio de movimientos.
Define operaciones específicas para movimientos de inventario.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from datetime import datetime


from ....app.domain.entities.inventory_movement import InventoryMovement


class MovementRepository(ABC):
    """Puerto para operaciones de movimientos"""
    
    @abstractmethod
    def save(self, movement: InventoryMovement) -> InventoryMovement:
        """
        Guardar un movimiento.
        
        Args:
            movement: Movimiento a persistir
            
        Returns:
            InventoryMovement: Movimiento persistido
        """
        pass
    
    @abstractmethod
    def find_by_id(self, movement_id: int) -> Optional[InventoryMovement]:
        """
        Buscar movimiento por ID.
        
        Args:
            movement_id: ID del movimiento
            
        Returns:
            Optional[InventoryMovement]: Movimiento encontrado o None
        """
        pass
    
    @abstractmethod
    def find_by_product(
        self, 
        product_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[InventoryMovement]:
        """
        Buscar movimientos por producto.
        
        Args:
            product_id: ID del producto
            skip: Saltar registros
            limit: Límite de registros
            
        Returns:
            List[InventoryMovement]: Lista de movimientos
        """
        pass
    
    @abstractmethod
    def find_by_user(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[InventoryMovement]:
        """
        Buscar movimientos por usuario.
        
        Args:
            user_id: ID del usuario
            skip: Saltar registros
            limit: Límite de registros
            
        Returns:
            List[InventoryMovement]: Lista de movimientos
        """
        pass
    
    @abstractmethod
    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        product_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[InventoryMovement]:
        """
        Buscar movimientos por rango de fechas.
        
        Args:
            start_date: Fecha inicial
            end_date: Fecha final
            product_id: Filtrar por producto (opcional)
            user_id: Filtrar por usuario (opcional)
            
        Returns:
            List[InventoryMovement]: Lista de movimientos
        """
        pass
    
    @abstractmethod
    def count_movements(
        self,
        product_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Contar movimientos con filtros.
        
        Args:
            product_id: Filtrar por producto
            user_id: Filtrar por usuario
            start_date: Fecha inicial
            end_date: Fecha final
            
        Returns:
            int: Número de movimientos
        """
        pass
    
    @abstractmethod
    def get_movement_stats(
        self,
        product_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """
        Obtener estadísticas de movimientos.
        
        Args:
            product_id: Filtrar por producto
            start_date: Fecha inicial
            end_date: Fecha final
            
        Returns:
            dict: Estadísticas de movimientos
        """
        pass