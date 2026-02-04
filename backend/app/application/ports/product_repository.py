"""
Puerto/Interfaz para repositorio de productos.
Define el contrato que debe cumplir cualquier implementación.

PRINCIPIO: Dependency Inversion (SOLID - D)
- El dominio define el contrato
- La infraestructura implementa el contrato
- La aplicación depende de abstracciones, no de implementaciones
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from datetime import datetime

from ....app.domain.entities.product import Product


class ProductRepository(ABC):
    """
    Puerto para operaciones de productos.
    
    SOLID - Interface Segregation:
    - Interfaz específica para productos
    - No incluye operaciones de otros agregados
    """
    
    @abstractmethod
    def save(self, product: Product) -> Product:
        """
        Guardar o actualizar un producto.
        
        Args:
            product: Entidad Product a persistir
            
        Returns:
            Product: Producto persistido (con ID si era nuevo)
            
        Raises:
            Exception: Si hay error de persistencia
        """
        pass
    
    @abstractmethod
    def find_by_id(self, product_id: int) -> Optional[Product]:
        """
        Buscar producto por ID.
        
        Args:
            product_id: ID del producto
            
        Returns:
            Optional[Product]: Producto encontrado o None
        """
        pass
    
    @abstractmethod
    def find_by_id_with_lock(self, product_id: int) -> Optional[Product]:
        """
        Buscar producto por ID con bloqueo para concurrencia.
        Usa SELECT ... FOR UPDATE en SQL.
        
        Args:
            product_id: ID del producto
            
        Returns:
            Optional[Product]: Producto bloqueado o None
        """
        pass
    
    @abstractmethod
    def find_by_code(self, code: str) -> Optional[Product]:
        """
        Buscar producto por código único.
        
        Args:
            code: Código del producto
            
        Returns:
            Optional[Product]: Producto encontrado o None
        """
        pass
    
    @abstractmethod
    def find_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        min_stock: Optional[int] = None,
        max_stock: Optional[int] = None,
        search: Optional[str] = None
    ) -> List[Product]:
        """
        Listar productos con paginación y filtros.
        
        Args:
            skip: Número de registros a saltar (paginación)
            limit: Límite de registros por página
            min_stock: Filtro mínimo de stock
            max_stock: Filtro máximo de stock
            search: Búsqueda en nombre o código
            
        Returns:
            List[Product]: Lista de productos
        """
        pass
    
    @abstractmethod
    def delete(self, product_id: int) -> bool:
        """
        Eliminar producto por ID.
        
        Args:
            product_id: ID del producto
            
        Returns:
            bool: True si se eliminó, False si no existía
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Contar total de productos.
        
        Returns:
            int: Número total de productos
        """
        pass
    
    @abstractmethod
    def get_low_stock_products(self, threshold_percentage: float = 0.3) -> List[Product]:
        """
        Obtener productos con stock bajo.
        
        Args:
            threshold_percentage: Porcentaje umbral para stock bajo
            
        Returns:
            List[Product]: Productos con stock bajo
        """
        pass
    
    @abstractmethod
    def get_high_stock_products(self, threshold_percentage: float = 0.9) -> List[Product]:
        """
        Obtener productos con stock alto (cerca del máximo).
        
        Args:
            threshold_percentage: Porcentaje umbral para stock alto
            
        Returns:
            List[Product]: Productos con stock alto
        """
        pass
    
    @abstractmethod
    def get_stock_summary(self) -> dict:
        """
        Obtener resumen estadístico del inventario.
        
        Returns:
            dict: Estadísticas del inventario
        """
        pass