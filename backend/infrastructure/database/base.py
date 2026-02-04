"""
Modelo base para todos los modelos SQLAlchemy.
Define campos comunes que todas las entidades de persistencia deben tener.

Principios:
- DRY (Don't Repeat Yourself): Campos comunes en una clase base
- Template Method Pattern: Patrón para modelos base
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func

# Crear Base declarativa para SQLAlchemy
Base = declarative_base()

class BaseModel(Base):
    """
    Modelo base abstracto para todas las entidades de persistencia.
    
    Atributos comunes:
    - id: Identificador único autoincremental
    - created_at: Fecha de creación automática
    - updated_at: Fecha de última actualización automática
    """
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

  #esto no estaba antes se puede quitar   
    def __repr__(self) -> str:
        """Representación legible del modelo"""
        return f"<{self.__class__.__name__}(id={self.id})>"