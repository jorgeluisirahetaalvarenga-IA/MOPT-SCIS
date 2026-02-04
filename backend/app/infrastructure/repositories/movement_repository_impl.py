"""
Implementación concreta del repositorio de movimientos con SQLAlchemy.
Adaptador para operaciones de persistencia de movimientos de inventario.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from ....app.domain.entities.inventory_movement import InventoryMovement
from ....app.application.ports.movement_repository import MovementRepository
from ....infrastructure.database.models import InventoryMovement as MovementModel


class SQLAlchemyMovementRepository(MovementRepository):
    """Implementación concreta con SQLAlchemy para movimientos"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def save(self, movement: InventoryMovement) -> InventoryMovement:
        """Guardar un movimiento"""
        try:
            # Mapear entidad de dominio a modelo de persistencia
            db_movement = MovementModel(
                product_id=movement.product_id,
                quantity=movement.quantity,
                movement_type=movement.movement_type,
                reason=movement.reason,
                previous_stock=movement.previous_stock,
                new_stock=movement.new_stock,
                user_id=movement.user_id,
                created_at=movement.created_at or datetime.utcnow()
            )
            
            self.session.add(db_movement)
            self.session.commit()
            self.session.refresh(db_movement)
            
            # Convertir de vuelta a dominio
            return self._to_domain(db_movement)
            
        except Exception as e:
            self.session.rollback()
            raise e
    
    def find_by_id(self, movement_id: int) -> Optional[InventoryMovement]:
        """Buscar movimiento por ID"""
        db_movement = self.session.query(MovementModel)\
            .filter(MovementModel.id == movement_id)\
            .first()
        
        return self._to_domain(db_movement) if db_movement else None
    
    def find_by_product(
        self, 
        product_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[InventoryMovement]:
        """Buscar movimientos por producto"""
        db_movements = self.session.query(MovementModel)\
            .filter(MovementModel.product_id == product_id)\
            .order_by(desc(MovementModel.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [self._to_domain(m) for m in db_movements]
    
    def find_by_user(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[InventoryMovement]:
        """Buscar movimientos por usuario"""
        db_movements = self.session.query(MovementModel)\
            .filter(MovementModel.user_id == user_id)\
            .order_by(desc(MovementModel.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [self._to_domain(m) for m in db_movements]
    
    def find_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        product_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[InventoryMovement]:
        """Buscar movimientos por rango de fechas"""
        query = self.session.query(MovementModel)\
            .filter(
                and_(
                    MovementModel.created_at >= start_date,
                    MovementModel.created_at <= end_date
                )
            )
        
        # Aplicar filtros adicionales
        if product_id:
            query = query.filter(MovementModel.product_id == product_id)
        
        if user_id:
            query = query.filter(MovementModel.user_id == user_id)
        
        db_movements = query.order_by(desc(MovementModel.created_at)).all()
        return [self._to_domain(m) for m in db_movements]
    
    def count_movements(
        self,
        product_id: Optional[int] = None,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """Contar movimientos con filtros"""
        query = self.session.query(func.count(MovementModel.id))
        
        # Aplicar filtros
        if product_id:
            query = query.filter(MovementModel.product_id == product_id)
        
        if user_id:
            query = query.filter(MovementModel.user_id == user_id)
        
        if start_date:
            query = query.filter(MovementModel.created_at >= start_date)
        
        if end_date:
            query = query.filter(MovementModel.created_at <= end_date)
        
        return query.scalar() or 0
    
    def get_movement_stats(
        self,
        product_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Obtener estadísticas de movimientos"""
        query = self.session.query(
            func.count(MovementModel.id).label('total_movements'),
            func.sum(MovementModel.quantity).label('total_quantity'),
            func.sum(
                func.case(
                    (MovementModel.movement_type == 'IN', MovementModel.quantity),
                    else_=0
                )
            ).label('total_in'),
            func.sum(
                func.case(
                    (MovementModel.movement_type == 'OUT', MovementModel.quantity),
                    else_=0
                )
            ).label('total_out')
        )
        
        # Aplicar filtros
        if product_id:
            query = query.filter(MovementModel.product_id == product_id)
        
        if start_date:
            query = query.filter(MovementModel.created_at >= start_date)
        
        if end_date:
            query = query.filter(MovementModel.created_at <= end_date)
        
        result = query.first()
        
        return {
            'total_movements': result.total_movements or 0,
            'total_quantity': result.total_quantity or 0,
            'total_in': result.total_in or 0,
            'total_out': result.total_out or 0,
            'net_movement': (result.total_in or 0) - (result.total_out or 0)
        }
    
    def _to_domain(self, db_movement: MovementModel) -> Optional[InventoryMovement]:
        """Convertir de modelo de persistencia a entidad de dominio"""
        if not db_movement:
            return None
        
        return InventoryMovement(
            id=db_movement.id,
            product_id=db_movement.product_id,
            quantity=db_movement.quantity,
            movement_type=db_movement.movement_type,
            reason=db_movement.reason,
            previous_stock=db_movement.previous_stock,
            new_stock=db_movement.new_stock,
            user_id=db_movement.user_id,
            created_at=db_movement.created_at
        )