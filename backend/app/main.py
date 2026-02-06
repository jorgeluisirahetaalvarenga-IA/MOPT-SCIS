from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from infrastructure.database.session import SessionLocal, get_db
from infrastructure.database.models import Product, InventoryMovement

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SCIS API - Sistema de Control de Inventario",
    description="API para prueba técnica LeaderTeam",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "message": "SCIS API - Prueba Técnica LeaderTeam",
        "version": "1.0.0",
        "endpoints": {
            "products": "/api/products",
            "inventory_movement": "/api/inventory/movement",
            "documentation": "/docs"
        }
    }

@app.get("/api/products")
def get_products(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

@app.post("/api/inventory/movement")
def inventory_movement(
    product_id: int,
    quantity: int,
    movement_type: str,
    reason: str = "Movimiento de inventario",
    user_id: str = "admin",
    db: Session = Depends(get_db)
):
    # Validaciones iniciales
    if movement_type not in ["IN", "OUT"]:
        raise HTTPException(status_code=400, detail="Tipo debe ser 'IN' o 'OUT'")
    
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Cantidad debe ser > 0")

    try:
        # Iniciar transacción
        db.begin()
        
        # Obtener producto con bloqueo para evitar condiciones de carrera
        product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado")
        
        previous_stock = product.current_stock
        
        # Calcular nuevo stock según el tipo de movimiento
        if movement_type == "IN":
            new_stock = previous_stock + quantity
        else:  # OUT
            new_stock = previous_stock - quantity
            if new_stock < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Stock insuficiente. Disponible: {previous_stock}, Requerido: {quantity}"
                )
        
        # Actualizar stock del producto
        product.current_stock = new_stock
        
        # Crear registro de movimiento
        movement = InventoryMovement(
            product_id=product_id,
            quantity=quantity,
            movement_type=movement_type,
            reason=reason,
            previous_stock=previous_stock,
            new_stock=new_stock,
            user_id=user_id
        )
        db.add(movement)
        db.add(product)  # Asegurar que el producto se actualice
        
        db.commit()
        
        logger.info(f"Movimiento registrado: Producto {product_id}, {movement_type}, Cantidad: {quantity}")
        
        return {
            "message": "Movimiento registrado exitosamente",
            "product_id": product_id,
            "product_code": product.code,
            "product_name": product.name,
            "movement_type": movement_type,
            "quantity": quantity,
            "previous_stock": previous_stock,
            "new_stock": new_stock,
            "movement_id": movement.id,
            "reason": reason,
            "user_id": user_id,
            "timestamp": movement.created_at.isoformat()
        }
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error de integridad en base de datos: {e}")
        raise HTTPException(status_code=400, detail="Error de integridad en la base de datos")
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
@app.get("/api/products/{product_id}")
def get_product_detail(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado")
    
    # Obtener últimos movimientos del producto
    movements = db.query(InventoryMovement)\
        .filter(InventoryMovement.product_id == product_id)\
        .order_by(InventoryMovement.created_at.desc())\
        .limit(10)\
        .all()
    
    return {
        "product": {
            "id": product.id,
            "code": product.code,
            "name": product.name,
            "description": product.description,
            "current_stock": product.current_stock,
            "min_stock": product.min_stock,
            "max_stock": product.max_stock,
            "unit": product.unit,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat()
        },
        "recent_movements": [
            {
                "id": m.id,
                "movement_type": m.movement_type,
                "quantity": m.quantity,
                "previous_stock": m.previous_stock,
                "new_stock": m.new_stock,
                "reason": m.reason,
                "user_id": m.user_id,
                "created_at": m.created_at.isoformat()
            }
            for m in movements
        ]
    }

@app.get("/api/inventory/status")
def inventory_status(
    db: Session = Depends(get_db)
):
    # Productos con stock bajo
    low_stock = db.query(Product).filter(
        Product.current_stock <= Product.min_stock
    ).all()
    
    # Productos con stock alto (cerca del máximo)
    high_stock = db.query(Product).filter(
        Product.current_stock >= (Product.max_stock * 0.9)
    ).all()
    
    # Estadísticas generales
    total_products = db.query(Product).count()
    total_stock = db.query(Product.current_stock).scalar() or 0
    
    return {
        "statistics": {
            "total_products": total_products,
            "total_stock": total_stock,
            "low_stock_count": len(low_stock),
            "high_stock_count": len(high_stock)
        },
        "alerts": {
            "low_stock": [
                {
                    "id": p.id,
                    "code": p.code,
                    "name": p.name,
                    "current_stock": p.current_stock,
                    "min_stock": p.min_stock
                }
                for p in low_stock
            ],
            "high_stock": [
                {
                    "id": p.id,
                    "code": p.code,
                    "name": p.name,
                    "current_stock": p.current_stock,
                    "max_stock": p.max_stock
                }
                for p in high_stock
            ]
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SCIS API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)