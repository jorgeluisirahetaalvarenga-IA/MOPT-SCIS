"""
Implementación concreta del repositorio de productos usando SQLAlchemy.
Este es un Adaptador que implementa el Puerto definido por el dominio.

Patrones:
- Adapter Pattern: Adapta SQLAlchemy a la interfaz del dominio
- Data Mapper Pattern: Mapea entidades de dominio a modelos de persistencia
"""
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ....app.domain.entities.product import Product
from ....app.application.ports.product_repository import ProductRepository
from ....infrastructure.database.models import Product as ProductModel


class SQLAlchemyProductRepository(ProductRepository):
    """
    Implementación concreta con SQLAlchemy.
    Mapea operaciones del dominio a operaciones de SQLAlchemy.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def save(self, product: Product) -> Product:
        """
        Guardar o actualizar un producto.
        
        Implementa el patrón Unit of Work:
        - Si tiene ID: actualizar existente
        - Si no tiene ID: crear nuevo
        """
        try:
            if product.id:
                # ACTUALIZAR producto existente
                db_product = self.session.query(ProductModel)\
                    .filter(ProductModel.id == product.id)\
                    .first()
                
                if not db_product:
                    raise ValueError(f"Producto con id {product.id} no encontrado")
                
                # Mapear de dominio a persistencia
                db_product.code = product.code
                db_product.name = product.name
                db_product.description = product.description
                db_product.current_stock = product.current_stock
                db_product.min_stock = product.min_stock
                db_product.max_stock = product.max_stock
                db_product.unit = product.unit
                
            else:
                # CREAR nuevo producto
                db_product = ProductModel(
                    code=product.code,
                    name=product.name,
                    description=product.description,
                    current_stock=product.current_stock,
                    min_stock=product.min_stock,
                    max_stock=product.max_stock,
                    unit=product.unit
                )
                self.session.add(db_product)
            
            # Commit de la transacción
            #self.session.commit()   ---Para solucionar el tema de concurrencia se cammbia flush por commit 
            self.session.flush()  
            self.session.refresh(db_product)
            
            # Convertir de vuelta a dominio
            return self._to_domain(db_product)
            
        except Exception as e:
            self.session.rollback()
            raise e
    
    def find_by_id(self, product_id: int) -> Optional[Product]:
        """Buscar producto por ID"""
        db_product = self.session.query(ProductModel)\
            .filter(ProductModel.id == product_id)\
            .first()
        
        return self._to_domain(db_product) if db_product else None
    
    def find_by_id_with_lock(self, product_id: int) -> Optional[Product]:
        """Buscar producto por ID con bloqueo para concurrencia"""
        db_product = self.session.query(ProductModel)\
            .filter(ProductModel.id == product_id)\
            .with_for_update()\
            .first()
        
        return self._to_domain(db_product) if db_product else None
    
    def find_by_code(self, code: str) -> Optional[Product]:
        """Buscar producto por código"""
        db_product = self.session.query(ProductModel)\
            .filter(ProductModel.code == code)\
            .first()
        
        return self._to_domain(db_product) if db_product else None
    
    def find_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        min_stock: Optional[int] = None,
        max_stock: Optional[int] = None,
        search: Optional[str] = None
    ) -> List[Product]:
        """Listar productos con paginación y filtros"""
        query = self.session.query(ProductModel)
        
        # Aplicar filtros
        if min_stock is not None:
            query = query.filter(ProductModel.current_stock >= min_stock)
        
        if max_stock is not None:
            query = query.filter(ProductModel.current_stock <= max_stock)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ProductModel.code.ilike(search_term),
                    ProductModel.name.ilike(search_term),
                    ProductModel.description.ilike(search_term)
                )
            )
        
        # Aplicar paginación
        db_products = query.order_by(ProductModel.code)\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [self._to_domain(p) for p in db_products]
    
    def delete(self, product_id: int) -> bool:
        """Eliminar producto por ID"""
        db_product = self.session.query(ProductModel)\
            .filter(ProductModel.id == product_id)\
            .first()
        
        if db_product:
            self.session.delete(db_product)
            self.session.commit()
            return True
        
        return False
    
    def count(self) -> int:
        """Contar total de productos"""
        return self.session.query(ProductModel).count()
    
    def get_low_stock_products(self, threshold_percentage: float = 0.3) -> List[Product]:
        """Obtener productos con stock bajo"""
        # Calcular threshold
        query = self.session.query(ProductModel)\
            .filter(
                ProductModel.current_stock <= 
                (ProductModel.min_stock * (1 + threshold_percentage))
            )\
            .order_by(ProductModel.current_stock)
        
        db_products = query.all()
        return [self._to_domain(p) for p in db_products]
    
    def get_high_stock_products(self, threshold_percentage: float = 0.9) -> List[Product]:
        """Obtener productos con stock alto"""
        query = self.session.query(ProductModel)\
            .filter(
                and_(
                    ProductModel.max_stock > 0,
                    ProductModel.current_stock >= 
                    (ProductModel.max_stock * threshold_percentage)
                )
            )\
            .order_by(ProductModel.current_stock.desc())
        
        db_products = query.all()
        return [self._to_domain(p) for p in db_products]
    
    def get_stock_summary(self) -> dict:
        """Obtener resumen estadístico del inventario"""
        from sqlalchemy import func
        
        result = self.session.query(
            func.count(ProductModel.id).label('total_products'),
            func.sum(ProductModel.current_stock).label('total_stock'),
            func.avg(ProductModel.current_stock).label('average_stock'),
            func.min(ProductModel.current_stock).label('min_stock'),
            func.max(ProductModel.current_stock).label('max_stock')
        ).first()
        
        return {
            'total_products': result.total_products or 0,
            'total_stock': result.total_stock or 0,
            'average_stock': float(result.average_stock or 0),
            'min_stock': result.min_stock or 0,
            'max_stock': result.max_stock or 0,
            'low_stock_count': len(self.get_low_stock_products()),
            'high_stock_count': len(self.get_high_stock_products())
        }
    
    def _to_domain(self, db_product: ProductModel) -> Optional[Product]:
        
        if not db_product:
            return None
        
        return Product(
            id=db_product.id,
            code=db_product.code,
            name=db_product.name,
            description=db_product.description,
            current_stock=db_product.current_stock,
            min_stock=db_product.min_stock,
            max_stock=db_product.max_stock,
            unit=db_product.unit,
            created_at=db_product.created_at,
            updated_at=db_product.updated_at
        )