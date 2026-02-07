"""
Router para operaciones de inventario.
Endpoints para movimientos de stock y estado del inventario.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ...infrastructure.database.session import get_db
from ...app.application.dtos.schemas import (
    InventoryMovementCreate, InventoryMovementResponse,
    InventoryStatusResponse, SuccessResponse, ErrorResponse,
    PaginatedResponse
)
from ...api.dependencies import (
    get_current_user, require_operator, require_viewer,
    get_product_repository, get_movement_repository, get_user_repository,
    get_audit_logger
)
from ...infrastructure.database.models import User as UserModel, Product, InventoryMovement as MovementModel
from ...app.application.use_cases.register_movement import (
    RegisterMovementUseCase, RegisterMovementRequest
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/movement", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def register_movement(
    movement_data: InventoryMovementCreate,
    current_user: UserModel = Depends(require_operator),
    db: Session = Depends(get_db),
    audit_logger = Depends(get_audit_logger)
):
    
    try:
        # Crear caso de uso con repositorios concretos
        use_case = RegisterMovementUseCase(
            product_repository=get_product_repository(db),
            movement_repository=get_movement_repository(db),
            user_repository=get_user_repository(db)
        )
        
        # Crear request para caso de uso
        request = RegisterMovementRequest(
            product_id=movement_data.product_id,
            quantity=movement_data.quantity,
            movement_type=movement_data.movement_type.value,
            reason=movement_data.reason,
            user_id=current_user.id
        )
        
        # Ejecutar caso de uso
        response = use_case.execute(request)
        
        # Registrar en auditoría
        audit_logger.log_movement(
            movement_data={
                "product_id": response.product_id,
                "product_code": response.product_code,
                "movement_type": response.movement_type,
                "quantity": response.quantity,
                "previous_stock": response.previous_stock,
                "new_stock": response.new_stock,
                "reason": movement_data.reason
            },
            user_data={
                "user_id": current_user.id,
                "username": current_user.username,
                "role": current_user.role.value
            }
        )
        
        return SuccessResponse(
            message=response.message,
            data={
                "movement_id": response.movement_id,
                "product_id": response.product_id,
                "product_code": response.product_code,
                "product_name": response.product_name,
                "movement_type": response.movement_type,
                "quantity": response.quantity,
                "previous_stock": response.previous_stock,
                "new_stock": response.new_stock,
                "user_id": response.user_id,
                "username": response.username,
                "timestamp": response.timestamp
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.log_movement(
            movement_data={
                "product_id": movement_data.product_id,
                "quantity": movement_data.quantity,
                "movement_type": movement_data.movement_type.value,
                "reason": movement_data.reason,
                "error": str(e)
            },
            user_data={
                "user_id": current_user.id,
                "username": current_user.username
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar movimiento: {str(e)}"
        )


@router.get("/movements", response_model=List[InventoryMovementResponse])
async def get_movements(
    product_id: Optional[int] = Query(None, description="Filtrar por ID de producto"),
    user_id: Optional[int] = Query(None, description="Filtrar por ID de usuario"),
    start_date: Optional[datetime] = Query(None, description="Fecha inicial (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Fecha final (ISO 8601)"),
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros"),
    current_user: UserModel = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    
    try:
        movement_repo = get_movement_repository(db)
        
        # Aplicar filtros por fecha (si no se proporcionan, usar últimos 30 días)
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Obtener movimientos
        movements = movement_repo.find_by_date_range(
            start_date=start_date,
            end_date=end_date,
            product_id=product_id,
            user_id=user_id
        )
        
        # Aplicar paginación
        paginated_movements = movements[skip:skip + limit]
        
        # Convertir a respuesta
        return [
            InventoryMovementResponse(
                id=movement.id if movement.id else 0,
                product_id=movement.product_id,
                quantity=movement.quantity,
                movement_type=movement.movement_type,
                reason=movement.reason,
                previous_stock=movement.previous_stock,
                new_stock=movement.new_stock,
                user_id=movement.user_id,
                created_at=movement.created_at if movement.created_at else datetime.utcnow(),
                description=movement.get_movement_description() if hasattr(movement, 'get_movement_description') else "",
                stock_change=movement.get_stock_change() if hasattr(movement, 'get_stock_change') else 0
            )
            for movement in paginated_movements
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener movimientos: {str(e)}"
        )


@router.get("/movements/{movement_id}", response_model=InventoryMovementResponse)
async def get_movement_detail(
    movement_id: int,
    current_user: UserModel = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    
    try:
        movement_repo = get_movement_repository(db)
        movement = movement_repo.find_by_id(movement_id)
        
        if not movement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movimiento con ID {movement_id} no encontrado"
            )
        
        return InventoryMovementResponse(
            id=movement.id if movement.id else 0,
            product_id=movement.product_id,
            quantity=movement.quantity,
            movement_type=movement.movement_type,
            reason=movement.reason,
            previous_stock=movement.previous_stock,
            new_stock=movement.new_stock,
            user_id=movement.user_id,
            created_at=movement.created_at if movement.created_at else datetime.utcnow(),
            description=movement.get_movement_description() if hasattr(movement, 'get_movement_description') else "",
            stock_change=movement.get_stock_change() if hasattr(movement, 'get_stock_change') else 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener movimiento: {str(e)}"
        )


@router.get("/status", response_model=InventoryStatusResponse)
async def get_inventory_status(
    current_user: UserModel = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    
    try:
        product_repo = get_product_repository(db)
        movement_repo = get_movement_repository(db)
        
        # Obtener estadísticas de productos
        product_stats = product_repo.get_stock_summary()
        
        # Obtener estadísticas de movimientos (últimos 7 días)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        movement_stats = movement_repo.get_movement_stats(start_date=seven_days_ago)
        
        # Obtener alertas
        low_stock_products = product_repo.get_low_stock_products()
        high_stock_products = product_repo.get_high_stock_products()
        
        # Combinar estadísticas
        statistics = {
            **product_stats,
            "movements_last_7_days": movement_stats
        }
        
        # Preparar alertas
        alerts = {
            "low_stock": [
                {
                    "id": product.id if product.id else 0,
                    "code": product.code,
                    "name": product.name,
                    "current_stock": product.current_stock,
                    "min_stock": product.min_stock,
                    "unit": product.unit,
                    "stock_percentage": product.get_stock_percentage() if hasattr(product, 'get_stock_percentage') else 0
                }
                for product in low_stock_products
            ],
            "high_stock": [
                {
                    "id": product.id if product.id else 0,
                    "code": product.code,
                    "name": product.name,
                    "current_stock": product.current_stock,
                    "max_stock": product.max_stock,
                    "unit": product.unit,
                    "stock_percentage": product.get_stock_percentage() if hasattr(product, 'get_stock_percentage') else 0
                }
                for product in high_stock_products
            ],
            "needs_reorder": [
                {
                    "id": product.id if product.id else 0,
                    "code": product.code,
                    "name": product.name,
                    "current_stock": product.current_stock,
                    "min_stock": product.min_stock,
                    "reorder_quantity": product.calculate_reorder_quantity() if hasattr(product, 'calculate_reorder_quantity') else 0,
                    "unit": product.unit
                }
                for product in low_stock_products
                if hasattr(product, 'needs_reorder') and product.needs_reorder()
            ]
        }
        
        return InventoryStatusResponse(
            statistics=statistics,
            alerts=alerts
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estado del inventario: {str(e)}"
        )


@router.get("/movements/product/{product_id}", response_model=List[InventoryMovementResponse])
async def get_product_movements(
    product_id: int,
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(100, ge=1, le=500, description="Límite de registros"),
    current_user: UserModel = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    
    try:
        # Verificar que el producto existe
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        movement_repo = get_movement_repository(db)
        movements = movement_repo.find_by_product(product_id, skip=skip, limit=limit)
        
        return [
            InventoryMovementResponse(
                id=movement.id if movement.id else 0,
                product_id=movement.product_id,
                quantity=movement.quantity,
                movement_type=movement.movement_type,
                reason=movement.reason,
                previous_stock=movement.previous_stock,
                new_stock=movement.new_stock,
                user_id=movement.user_id,
                created_at=movement.created_at if movement.created_at else datetime.utcnow(),
                description=movement.get_movement_description() if hasattr(movement, 'get_movement_description') else "",
                stock_change=movement.get_stock_change() if hasattr(movement, 'get_stock_change') else 0
            )
            for movement in movements
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener movimientos del producto: {str(e)}"
        )


