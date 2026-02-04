"""
Configuración de sesión de base de datos SQLAlchemy.
Maneja la conexión a la base de datos y provee sesiones para transacciones.

Responsabilidades:
- Crear engine de SQLAlchemy
- Configurar session factory
- Proveer dependencia para FastAPI
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# Configuración de base de datos
# En producción, usar variable de entorno DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database/scis.db")

# Crear engine de SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Necesario para SQLite
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",  # Mostrar queries SQL
    pool_pre_ping=True,  # Verificar conexión antes de usarla
    pool_recycle=3600,  # Reciclar conexiones cada hora
)

# Factory para crear sesiones
SessionLocal = sessionmaker(
    autocommit=False,  # No auto-commit, control manual
    autoflush=False,   # No auto-flush, control manual
    bind=engine,
    expire_on_commit=False,  # Mantener objetos después del commit
)

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia FastAPI para obtener sesión de base de datos.
    
    Yield Pattern:
    - Provee sesión a la ruta
    - Cierra sesión automáticamente al final
    - Maneja excepciones apropiadamente
    
    Uso:
    @app.get("/items")
    def read_items(db: Session = Depends(get_db)):
        # Usar db aquí
        pass
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # Rollback en caso de error
        db.rollback()
        raise
    finally:
        # Siempre cerrar la sesión
        db.close()

def create_tables():
    """
    Crear todas las tablas en la base de datos.
    Útil para desarrollo y testing.
    
    Nota: En producción usar migraciones (Alembic).
    """
    from .base import Base
    from . import models  # Importar todos los modelos
    
    print("📦 Creando tablas en la base de datos...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente")
    
def drop_tables():
    """
    Eliminar todas las tablas (SOLO PARA DESARROLLO/TESTING).
    
    ¡ADVERTENCIA! Esto elimina todos los datos.
    """
    from .base import Base
    
    print("⚠️  Eliminando todas las tablas...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tablas eliminadas")