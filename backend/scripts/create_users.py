# Reemplaza el contenido de scripts/create_users.py con esto:
"""
Script para crear usuarios iniciales en la base de datos
Versión corregida con imports simplificados
"""
import sys
import os
import hashlib
import secrets
import base64

# Configurar path correctamente
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)  # Sube a 'backend'

# Agregar el path al sistema
sys.path.insert(0, backend_dir)

print(f"Current dir: {current_dir}")
print(f"Backend dir: {backend_dir}")

try:
    from infrastructure.database.session import SessionLocal
    from infrastructure.database.models import User, UserRole
    print(" Imports exitosos")
except ImportError as e:
    print(f" Error en imports: {e}")
    print("Contenido de sys.path:")
    for p in sys.path:
        print(f"   - {p}")
    sys.exit(1)


def create_password_hash(password: str) -> str:
    """
    Crea un hash seguro de contraseña usando PBKDF2 con SHA-256.
    """
    # Generar salt aleatorio
    salt = secrets.token_bytes(32)
    
    # Usar PBKDF2 con 100,000 iteraciones
    iterations = 100000
    
    # Generar hash
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations
    )
    
    # Convertir a formato almacenable
    salt_b64 = base64.b64encode(salt).decode('ascii')
    hash_b64 = base64.b64encode(hashed).decode('ascii')
    
    return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"


def create_initial_users():
    """Crear usuarios iniciales del sistema"""
    print("=" * 50)
    print("CREACIÓN DE USUARIOS INICIALES - SCIS")
    print("=" * 50)
    
    db = SessionLocal()
    try:
        # Verificar si ya existen usuarios
        existing_users = db.query(User).count()
        
        if existing_users > 0:
            print(f" Ya existen {existing_users} usuarios en la base de datos")
            
            # Mostrar usuarios existentes
            users = db.query(User).all()
            print("\nUSUARIOS EXISTENTES:")
            print("-" * 50)
            for user in users:
                status = "ACTIVO" if user.is_active else "INACTIVO"
                print(f"{user.username:10} - {user.role.value:10} - {user.email} - {status}")
            print("=" * 50)
            return
        
        # Crear usuarios iniciales
        users_data = [
            {
                "username": "admin",
                "email": "admin@scis.com",
                "password": "Admin123!",
                "full_name": "Administrador del Sistema",
                "role": UserRole.ADMIN,
                "is_active": True
            },
            {
                "username": "operator",
                "email": "operator@scis.com",
                "password": "Operator123!",
                "full_name": "Operador de Inventario",
                "role": UserRole.OPERATOR,
                "is_active": True
            },
            {
                "username": "viewer",
                "email": "viewer@scis.com",
                "password": "Viewer123!",
                "full_name": "Visualizador de Reportes",
                "role": UserRole.VIEWER,
                "is_active": True
            }
        ]
        
        created_count = 0
        for user_data in users_data:
            # Verificar si el usuario ya existe
            existing_user = db.query(User).filter_by(username=user_data["username"]).first()
            if existing_user:
                print(f"  El usuario '{user_data['username']}' ya existe, omitiendo...")
                continue
            
            # Crear hash de la contraseña
            hashed_password = create_password_hash(user_data["password"])
            
            # Crear usuario
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=hashed_password,
                full_name=user_data["full_name"],
                role=user_data["role"],
                is_active=user_data["is_active"]
            )
            
            db.add(user)
            created_count += 1
            
            print(f" Usuario creado: {user_data['username']}")
        
        if created_count > 0:
            db.commit()
            print(f"\n {created_count} usuarios creados exitosamente")
            
            # Mostrar credenciales de acceso
            print("\n" + "=" * 50)
            print("CREDENCIALES DE ACCESO:")
            print("=" * 50)
            print("Usuario    | Contraseña    | Rol")
            print("-" * 40)
            for user_data in users_data:
                print(f"{user_data['username']:10} | {user_data['password']:14} | {user_data['role'].value}")
            print("=" * 50)
            print("\n IMPORTANTE: Cambiar las contraseñas después del primer inicio de sesión")
        else:
            print("\nℹ No se crearon nuevos usuarios (ya existían todos)")
        
    except Exception as e:
        print(f"Error al crear usuarios: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("GESTIÓN DE USUARIOS - SCIS")
    print("=" * 50)
    print("1. Crear usuarios iniciales (admin, operator, viewer)")
    print("2. Verificar base de datos")
    print("=" * 50)
    
    choice = input("Seleccione opción (1-2): ").strip()
    
    if choice == "1":
        success = create_initial_users()
        if success:
            print("\n Proceso completado exitosamente")
        else:
            print("\n Hubo errores en el proceso")
    elif choice == "2":
        db = SessionLocal()
        try:
            user_count = db.query(User).count()
            print(f"\n📊 Total de usuarios en la base de datos: {user_count}")
            
            if user_count > 0:
                users = db.query(User).all()
                print("\n👥 Lista de usuarios:")
                print("-" * 60)
                print(f"{'Username':10} {'Rol':10} {'Email':25} {'Estado':8}")
                print("-" * 60)
                for user in users:
                    status = "ACTIVO" if user.is_active else "INACTIVO"
                    print(f"{user.username:10} {user.role.value:10} {user.email:25} {status:8}")
        except Exception as e:
            print(f" Error al verificar base de datos: {str(e)}")
        finally:
            db.close()
    else:
        print(" Opción no válida")
    
    print("\n" + "=" * 50)