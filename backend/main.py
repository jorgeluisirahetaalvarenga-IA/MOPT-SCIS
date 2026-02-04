"""
main.py - SCIS API con autenticación JWT completa
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uvicorn
from sqlalchemy.orm import Session

# Importar nuestros módulos
try:
    from infrastructure.database.session import get_db, SessionLocal, create_tables
    from infrastructure.database.models import User, Product, UserRole
    from infrastructure.auth.jwt_handler import JWTHandler, AuthenticationException
    DATABASE_AVAILABLE = True
    AUTH_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    AUTH_AVAILABLE = False
    print(f"  Advertencia: Error en imports - {e}")

# Crear la aplicación FastAPI
app = FastAPI(
    title="SCIS API - Sistema de Control de Inventario",
    description="API para gestión de inventario con autenticación JWT",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes (en producción, especifica los dominios)
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los headers
)

# Configurar OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# ==================== MODELOS PYDANTIC ====================

class HealthCheck(BaseModel):
    status: str
    message: str
    dependencies: dict

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None

class ProductCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    current_stock: int = 0
    min_stock: int = 0
    max_stock: int = 1000
    unit: str = "unidades"

class MovementCreate(BaseModel):
    product_id: int
    quantity: int
    movement_type: str  # "IN" o "OUT"
    reason: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    role: str
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None

# ==================== FUNCIONES DE AUTENTICACIÓN ====================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Obtener usuario actual desde token JWT"""
    try:
        payload = JWTHandler.verify_token(token)
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )
        
        return user
        
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error de autenticación: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}"
        )

def require_role(required_role: UserRole):
    """Decorador para verificar rol de usuario"""
    def role_checker(current_user: User = Depends(get_current_user)):
        if not current_user.has_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Requerido: {required_role.value}"
            )
        return current_user
    return role_checker

# ==================== ENDPOINTS PÚBLICOS ====================

@app.get("/", response_model=HealthCheck)
def read_root():
    """Endpoint raíz"""
    return {
        "status": "success",
        "message": "¡API SCIS funcionando correctamente! ",
        "dependencies": {
            "fastapi": "0.104.1",
            "database": "disponible" if DATABASE_AVAILABLE else "no disponible",
            "authentication": "JWT" if AUTH_AVAILABLE else "no disponible"
        }
    }

@app.get("/health")
def health_check():
    """Endpoint de salud"""
    if DATABASE_AVAILABLE:
        try:
            db = SessionLocal()
            user_count = db.query(User).count()
            product_count = db.query(Product).count()
            db.close()
            
            return {
                "status": "healthy",
                "service": "scis-api",
                "version": "1.0.0",
                "database": {
                    "connected": True,
                    "users": user_count,
                    "products": product_count
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "scis-api",
                "error": str(e)[:100]
            }
    else:
        return {
            "status": "healthy",
            "service": "scis-api",
            "version": "1.0.0",
            "database": "no configurado"
        }

# ==================== ENDPOINTS DE AUTENTICACIÓN ====================

@app.post("/token", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Obtener token JWT
    
    - **username**: admin, operator, viewer
    - **password**: Admin123!, Operator123!, Viewer123!
    """
    if not DATABASE_AVAILABLE or not AUTH_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de autenticación no disponible"
        )
    
    # Buscar usuario
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )
    
    # Verificar contraseña
    try:
        if not JWTHandler.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Contraseña incorrecta"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al verificar contraseña: {str(e)}"
        )
    
    # Verificar si usuario está activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    
    # Crear token
    try:
        token_data = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "email": user.email
        }
        
        access_token = JWTHandler.create_access_token(token_data)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "expires_in": 1800  # 30 minutos en segundos
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar token: {str(e)}"
        )

@app.get("/verify-token")
def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verificar si un token es válido
    """
    return {
        "valid": True,
        "user": current_user.username,
        "role": current_user.role.value,
        "email": current_user.email,
        "is_active": current_user.is_active
    }

@app.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Obtener información del usuario actual
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

# ==================== ENDPOINTS DE USUARIOS ====================

@app.get("/users/", dependencies=[Depends(require_role(UserRole.ADMIN))])
def get_users(db: Session = Depends(get_db)):
    """
    Obtener lista de usuarios (solo administradores)
    """
    try:
        users = db.query(User).all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener usuarios: {str(e)}"
        )

# ==================== ENDPOINTS DE PRODUCTOS ====================

@app.get("/products/")
def get_products(
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de productos (requiere autenticación)
    """
    try:
        products = db.query(Product).offset(skip).limit(limit).all()
        return [
            {
                "id": product.id,
                "code": product.code,
                "name": product.name,
                "description": product.description,
                "current_stock": product.current_stock,
                "min_stock": product.min_stock,
                "max_stock": product.max_stock,
                "unit": product.unit,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }
            for product in products
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener productos: {str(e)}"
        )

@app.post("/products/", dependencies=[Depends(require_role(UserRole.MANAGER))])
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """
    Crear nuevo producto (requiere rol MANAGER o ADMIN)
    """
    try:
        # Verificar si el código ya existe
        existing = db.query(Product).filter(Product.code == product.code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El código {product.code} ya existe"
            )
        
        # Crear producto
        db_product = Product(
            code=product.code,
            name=product.name,
            description=product.description,
            current_stock=product.current_stock,
            min_stock=product.min_stock,
            max_stock=product.max_stock,
            unit=product.unit
        )
        
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        
        return {
            "message": "Producto creado exitosamente",
            "product": {
                "id": db_product.id,
                "code": db_product.code,
                "name": db_product.name,
                "current_stock": db_product.current_stock
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear producto: {str(e)}"
        )

@app.get("/products/{product_id}")
def get_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener producto específico por ID
    """
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {product_id} no encontrado"
            )
        
        return product.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener producto: {str(e)}"
        )

# ==================== ENDPOINTS DE MOVIMIENTOS ====================

@app.post("/movements/", dependencies=[Depends(require_role(UserRole.OPERATOR))])
def create_movement(
    movement: MovementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crear movimiento de inventario (requiere rol OPERATOR, MANAGER o ADMIN)
    """
    try:
        # Validar tipo de movimiento
        if movement.movement_type not in ["IN", "OUT"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de movimiento debe ser 'IN' o 'OUT'"
            )
        
        # Verificar que la cantidad sea positiva
        if movement.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La cantidad debe ser mayor a 0"
            )
        
        # Buscar producto
        product = db.query(Product).filter(Product.id == movement.product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Producto con ID {movement.product_id} no encontrado"
            )
        
        # Guardar stock anterior
        previous_stock = product.current_stock
        
        # Actualizar stock según el tipo de movimiento
        if movement.movement_type == "IN":
            new_stock = previous_stock + movement.quantity
        else:  # OUT
            if previous_stock < movement.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Stock insuficiente. Disponible: {previous_stock}, Requerido: {movement.quantity}"
                )
            new_stock = previous_stock - movement.quantity
        
        # Actualizar producto
        product.current_stock = new_stock
        
        # Crear registro de movimiento (necesitarías el modelo InventoryMovement)
        # Por ahora solo actualizamos el producto
        
        db.commit()
        
        return {
            "message": "Movimiento registrado exitosamente",
            "product_id": product.id,
            "product_name": product.name,
            "movement_type": movement.movement_type,
            "quantity": movement.quantity,
            "reason": movement.reason,
            "previous_stock": previous_stock,
            "new_stock": new_stock,
            "user_id": current_user.id,
            "user_name": current_user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar movimiento: {str(e)}"
        )

# ==================== ENDPOINTS PÚBLICOS DE DEMOSTRACIÓN ====================

@app.get("/public/info")
def public_info():
    """Información pública (sin autenticación)"""
    return {
        "message": "Bienvenido al Sistema de Control de Inventario (SCIS)",
        "version": "1.0.0",
        "status": "operacional",
        "authentication": "JWT Token en /token"
    }

# ==================== INICIALIZACIÓN ====================

@app.on_event("startup")
async def startup_event():
    """Evento de inicio de la aplicación"""
    if DATABASE_AVAILABLE:
        try:
            # Crear tablas si no existen
            create_tables()
            print("✅ Tablas de base de datos verificadas/creadas")
            
            # Verificar datos iniciales
            db = SessionLocal()
            user_count = db.query(User).count()
            product_count = db.query(Product).count()
            db.close()
            
            print(f"   📊 Usuarios: {user_count}")
            print(f"   📦 Productos: {product_count}")
            
            if user_count == 0:
                print("⚠️  No hay usuarios. Ejecuta: python scripts/create_users.py")
            
        except Exception as e:
            print(f"⚠️  Error en inicialización: {e}")

# ==================== PUNTO DE ENTRADA ====================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 SCIS API - SISTEMA DE CONTROL DE INVENTARIO")
    print("=" * 60)
    print("📄 Swagger UI: http://localhost:8000/docs")
    print("🌐 API principal: http://localhost:8000/")
    print("🔐 Autenticación: POST http://localhost:8000/token")
    print("=" * 60)
    
    if DATABASE_AVAILABLE:
        print("✅ Base de datos: CONECTADA")
        try:
            db = SessionLocal()
            user_count = db.query(User).count()
            product_count = db.query(Product).count()
            db.close()
            print(f"   👥 Usuarios: {user_count}")
            print(f"   📦 Productos: {product_count}")
        except Exception as e:
            print(f"   ⚠️  Error al conectar con la base de datos: {e}")
    else:
        print("⚠️  Base de datos: NO DISPONIBLE")
    
    if AUTH_AVAILABLE:
        print("✅ Autenticación: JWT HABILITADA")
    else:
        print("⚠️  Autenticación: NO DISPONIBLE")
    
    print("=" * 60)
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )