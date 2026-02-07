"""
Router para operaciones de productos.
Endpoints para CRUD de productos y consultas.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ...infrastructure.database.session import get_db
from ...app.application.dtos.schemas import (
    ProductCreate, ProductUpdate, ProductResponse,
    SuccessResponse, PaginatedResponse
)
from ...api.dependencies import (
    get_current_user, require_manager, require_viewer,
    get_product_repository, get_audit_logger
)
from ...infrastructure.database.models import User as UserModel, Product as ProductModel
from ...app.domain.entities.product import Product as ProductEntity

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: UserModel = Depends(require_manager),
    db: Session = Depends(get_db),
    audit_logger = Depends(get_audit_logger)
):
    
    try:
        product_repo = get_product_repository(db)
        
        # Verificar que el código no exista
        existing = product_repo.find_by_code(product_data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un producto con código: {product_data.code}"
            )
        
        # Crear entidad de dominio
        product_entity = ProductEntity.create(
            code=product_data.code,
            name=product_data.name,
            description=product_data.description,
            current_stock=product_data.current_stock,
            min_stock=product_data.min_stock,
            max_stock=product_data.max_stock,
            unit=product_data.unit
        )
        
        # Persistir producto
        saved_product = product_repo.save(product_entity)
        
        # Registrar en auditoría
        audit_logger.log_user_action(
            user_id=current_user.id,
            action="create_product",
            details={
                "product_id": saved_product.id if saved_product.id else 0,
                "product_code": saved_product.code,
                "product_name": saved_product.name
            }
        )
        
        return ProductResponse(
            id=saved_product.id if saved_product.id else 0,
            code=saved_product.code,
            name=saved_product.name,
            description=saved_product.description,
            current_stock=saved_product.current_stock,
            min_stock=saved_product.min_stock,
            max_stock=saved_product.max_stock,
            unit=saved_product.unit,
            stock_percentage=saved_product.get_stock_percentage() if hasattr(saved_product, 'get_stock_percentage') else 0,
            needs_reorder=saved_product.needs_reorder() if hasattr(saved_product, 'needs_reorder') else False,
            is_stock_low=saved_product.is_stock_low() if hasattr(saved_product, 'is_stock_low') else False,
            is_stock_high=saved_product.is_stock_high() if hasattr(saved_product, 'is_stock_high') else False,
            created_at=saved_product.created_at if saved_product.created_at else None,
            updated_at=saved_product.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear producto: {str(e)}"
        )


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0, description="Saltar registros"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros"), # paginacion po 1000 
    min_stock: Optional[int] = Query(None, ge=0, description="Filtrar por stock mínimo"),
    max_stock: Optional[int] = Query(None, ge=0, description="Filtrar por stock máximo"),
    search: Optional[str] = Query(None, description="Buscar en código, nombre o descripción"),
    current_user: UserModel = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    
    try:
        product_repo = get_product_repository(db)
        products = product_repo.find_all(
            skip=skip,
            limit=limit,
            min_stock=min_stock,
            max_stock=max_stock,
            search=search
        )
        
        return [
            ProductResponse(
                id=product.id if product.id else 0,
                code=product.code,
                name=product.name,
                description=product.description,
                current_stock=product.current_stock,
                min_stock=product.min_stock,
                max_stock=product.max_stock,
                unit=product.unit,
                stock_percentage=product.get_stock_percentage() if hasattr(product, 'get_stock_percentage') else 0,
                needs_reorder=product.needs_reorder() if hasattr(product, 'needs_reorder') else False,
                is_stock_low=product.is_stock_low() if hasattr(product, 'is_stock_low') else False,
                is_stock_high=product.is_stock_high() if hasattr(product, 'is_stock_high') else False,
                created_at=product.created_at if product.created_at else None,
                updated_at=product.updated_at
            )
            for product in products
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product_detail(
    product_id: int,
    current_user: UserModel = Depends(require_viewer),
    db: Session = Depends(get_db)
):
    
    try:
        product_repo = get_product_repository(db)
        product = product_repo.find_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        return ProductResponse(
            id=product.id if product.id else 0,
            code=product.code,
            name=product.name,
            description=product.description,
            current_stock=product.current_stock,
            min_stock=product.min_stock,
            max_stock=product.max_stock,
            unit=product.unit,
            stock_percentage=product.get_stock_percentage() if hasattr(product, 'get_stock_percentage') else 0,
            needs_reorder=product.needs_reorder() if hasattr(product, 'needs_reorder') else False,
            is_stock_low=product.is_stock_low() if hasattr(product, 'is_stock_low') else False,
            is_stock_high=product.is_stock_high() if hasattr(product, 'is_stock_high') else False,
            created_at=product.created_at if product.created_at else None,
            updated_at=product.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener producto: {str(e)}"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: UserModel = Depends(require_manager),
    db: Session = Depends(get_db),
    audit_logger = Depends(get_audit_logger)
):
    
    try:
        product_repo = get_product_repository(db)
        
        # Buscar producto
        product = product_repo.find_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Guardar datos originales para auditoría
        original_data = {
            "name": product.name,
            "description": product.description,
            "min_stock": product.min_stock,
            "max_stock": product.max_stock,
            "unit": product.unit
        }
        
        # Actualizar campos proporcionados
        if product_data.name is not None:
            product.name = product_data.name
        
        if product_data.description is not None:
            product.description = product_data.description
        
        if product_data.min_stock is not None:
            product.min_stock = product_data.min_stock
        
        if product_data.max_stock is not None:
            product.max_stock = product_data.max_stock
        
        if product_data.unit is not None:
            product.unit = product_data.unit
        
        # Validar entidad actualizada
        product._validate()
        
        # Persistir cambios
        updated_product = product_repo.save(product)
        
        # Registrar en auditoría
        audit_logger.log_user_action(
            user_id=current_user.id,
            action="update_product",
            details={
                "product_id": product_id,
                "product_code": product.code,
                "original_data": original_data,
                "updated_data": {
                    "name": updated_product.name,
                    "description": updated_product.description,
                    "min_stock": updated_product.min_stock,
                    "max_stock": updated_product.max_stock,
                    "unit": updated_product.unit
                }
            }
        )
        
        return ProductResponse(
            id=updated_product.id if updated_product.id else 0,
            code=updated_product.code,
            name=updated_product.name,
            description=updated_product.description,
            current_stock=updated_product.current_stock,
            min_stock=updated_product.min_stock,
            max_stock=updated_product.max_stock,
            unit=updated_product.unit,
            stock_percentage=updated_product.get_stock_percentage() if hasattr(updated_product, 'get_stock_percentage') else 0,
            needs_reorder=updated_product.needs_reorder() if hasattr(updated_product, 'needs_reorder') else False,
            is_stock_low=updated_product.is_stock_low() if hasattr(updated_product, 'is_stock_low') else False,
            is_stock_high=updated_product.is_stock_high() if hasattr(updated_product, 'is_stock_high') else False,
            created_at=updated_product.created_at if updated_product.created_at else None,
            updated_at=updated_product.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar producto: {str(e)}"
        )


@router.delete("/{product_id}", response_model=SuccessResponse)
async def delete_product(
    product_id: int,
    current_user: UserModel = Depends(require_manager),
    db: Session = Depends(get_db),
    audit_logger = Depends(get_audit_logger)
):
    
    try:
        product_repo = get_product_repository(db)
        
        # Buscar producto
        product = product_repo.find_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        # Verificar si tiene movimientos
        movement_repo = get_movement_repository(db)
        movements = movement_repo.find_by_product(product_id, limit=1)
        
        if movements:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar producto con movimientos registrados"
            )
        
        # Eliminar producto
        deleted = product_repo.delete(product_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al eliminar producto"
            )
        
        # Registrar en auditoría
        audit_logger.log_user_action(
            user_id=current_user.id,
            action="delete_product",
            details={
                "product_id": product_id,
                "product_code": product.code,
                "product_name": product.name
            }
        )
        
        return SuccessResponse(
            message=f"Producto {product.code} eliminado exitosamente",
            data={"product_id": product_id, "product_code": product.code}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar producto: {str(e)}"
        )



