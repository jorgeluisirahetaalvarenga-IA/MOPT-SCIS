# Reemplaza el contenido de scripts/init_database.py con esto:
"""
Script de inicialización de base de datos.
Versión corregida con imports simples.
"""
import sys
import os

# Configurar path correctamente
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Sube a 'backend'

# Agregar el path al sistema
sys.path.insert(0, backend_dir)

print(f"Current dir: {current_dir}")
print(f"Backend dir: {backend_dir}")

try:
    from infrastructure.database.session import create_tables, SessionLocal
    from infrastructure.database.models import Product, User
    print(" Imports exitosos")
except ImportError as e:
    print(f" Error en imports: {e}")
    print("Contenido de sys.path:")
    for p in sys.path:
        print(f"   - {p}")
    sys.exit(1)

from sqlalchemy.orm import Session
from sqlalchemy import func


def init_database():
    """Inicializar base de datos con datos de prueba"""
    print("=" * 70)
    print("INICIALIZACIÓN DE BASE DE DATOS - SCIS")
    print("=" * 70)
    
    # Crear tablas
    print("Creando tablas de base de datos...")
    create_tables()
    print("Tablas creadas exitosamente")
    
    # Insertar datos de prueba
    db = SessionLocal()
    try:
        # Verificar si ya existen productos
        existing_products = db.query(Product).count()
        
        if existing_products == 0:
            print("Insertando productos de prueba...")
            
            # Productos de prueba
            products = [
                Product(
                    code="LAP-001",
                    name="Laptop Dell Inspiron 15",
                    description="Laptop 15.6 pulgadas, Intel Core i5, 8GB RAM, 512GB SSD",
                    current_stock=25,
                    min_stock=3,
                    max_stock=50,
                    unit="unidades"
                ),
                Product(
                    code="LAP-002",
                    name="MacBook Air M2",
                    description="Laptop Apple 13.6 pulgadas, chip M2, 8GB RAM, 256GB SSD",
                    current_stock=15,
                    min_stock=2,
                    max_stock=30,
                    unit="unidades"
                ),
                Product(
                    code="MON-001",
                    name="Monitor HP 24'' FHD",
                    description="Monitor LED 24 pulgadas Full HD, 75Hz, HDMI/VGA",
                    current_stock=40,
                    min_stock=5,
                    max_stock=80,
                    unit="unidades"
                ),
            ]
            
            for product in products:
                db.add(product)
            
            db.commit()
            print(f" {len(products)} productos de prueba creados")
            
            # Mostrar resumen
            print("\nRESUMEN DE PRODUCTOS:")
            print("-" * 60)
            for i, product in enumerate(products, 1):
                print(f"{i:2}. {product.code:8} | {product.name[:25]:25} | Stock: {product.current_stock:3}")
            print("=" * 60)
            
        else:
            print(f" Ya existen {existing_products} productos en la base de datos")
            
            # Mostrar algunos productos existentes
            sample_products = db.query(Product).limit(3).all()
            print("\nMuestra de productos existentes:")
            for prod in sample_products:
                print(f"  - {prod.code}: {prod.name} - Stock: {prod.current_stock} {prod.unit}")
        
        # Verificación final
        product_count = db.query(Product).count()
        
        print(f"\n ESTADO DE LA BASE DE DATOS:")
        print(f"  Productos registrados: {product_count}")
        
        # Estadísticas
        total_stock = db.query(func.sum(Product.current_stock)).scalar() or 0
        avg_stock = db.query(func.avg(Product.current_stock)).scalar() or 0
        
        print(f"  Stock total en inventario: {total_stock} unidades")
        print(f"  Stock promedio por producto: {avg_stock:.1f} unidades")
        
    except Exception as e:
        print(f" Error al inicializar base de datos: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()
    
    print("\n" + "=" * 70)
    print(" BASE DE DATOS INICIALIZADA EXITOSAMENTE")
    print("=" * 70)


if __name__ == "__main__":
    init_database()