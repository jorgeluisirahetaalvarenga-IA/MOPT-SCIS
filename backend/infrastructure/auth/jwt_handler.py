"""
Manejador JWT para autenticación.
Responsable de crear, verificar y decodificar tokens JWT.

Tecnologías:
- python-jose para operaciones JWT
- passlib[bcrypt] para hashing de contraseñas
- PBKDF2 como alternativa cuando bcrypt falla
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any  # Si no está ya
from passlib.context import CryptContext
import hashlib
import base64
import secrets
import os

# ==================== EXCEPCIONES LOCALES ====================

class AuthenticationException(Exception):
    """Excepción para errores de autenticación"""
    def __init__(self, message: str = "Error de autenticación"):
        self.message = message
        super().__init__(self.message)

# ==================== CONFIGURACIÓN ====================

# Configuración (usar variables de entorno en producción)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "scis-secret-key-change-this-in-production-12345")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Contexto para hashing de contraseñas
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    BCRYPT_AVAILABLE = True
except Exception:
    # Si bcrypt no está disponible, usar solo PBKDF2
    pwd_context = None
    BCRYPT_AVAILABLE = False
    print("Advertencia: bcrypt no disponible, usando PBKDF2 para hashing")

# ==================== CLASE PRINCIPAL JWTHandler ====================

class JWTHandler:
    """
    Manejador de operaciones JWT para autenticación.
    
    Responsabilidades:
    1. Crear tokens JWT
    2. Verificar tokens JWT
    3. Decodificar tokens JWT
    4. Hashear y verificar contraseñas (soporta múltiples algoritmos)
    """
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Crear token JWT de acceso.
        
        Args:
            data: Datos a incluir en el token (sub, user_id, role, etc.)
            expires_delta: Tiempo de expiración personalizado
            
        Returns:
            str: Token JWT firmado
        """
        to_encode = data.copy()
        
        # Configurar expiración
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Agregar claims estándar
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),  # Issued at
            "iss": "scis-api",  # Issuer
            "aud": "scis-client"  # Audience
        })
        
        # Codificar token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        
        try:
            # Decodificar token
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                audience="scis-client"
            )
            
            # Verificar expiración
            if datetime.utcfromtimestamp(payload["exp"]) < datetime.utcnow():
                raise AuthenticationException("Token expirado")
            
            return payload
            
        except JWTError as e:
            raise AuthenticationException(f"Token inválido: {str(e)}")
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verificar contraseña contra hash.
        Soporta múltiples formatos: bcrypt, PBKDF2-SHA256
        
        Args:
            plain_password: Contraseña en texto plano
            hashed_password: Hash almacenado
            
        Returns:
            bool: True si coinciden
        """
        # Determinar el tipo de hash basado en el formato
        if hashed_password.startswith("pbkdf2_sha256$"):
            return JWTHandler._verify_pbkdf2_hash(plain_password, hashed_password)
        elif hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            # Formato bcrypt
            if not BCRYPT_AVAILABLE:
                raise AuthenticationException("Bcrypt no disponible para verificación")
            try:
                return pwd_context.verify(plain_password, hashed_password)
            except Exception:
                # Si bcrypt falla, intentar convertir a PBKDF2
                print("Advertencia: Falló verificación bcrypt, intentando métodos alternativos")
                return False
        else:
            # Intentar con bcrypt por defecto (para compatibilidad)
            if BCRYPT_AVAILABLE:
                try:
                    return pwd_context.verify(plain_password, hashed_password)
                except Exception:
                    pass
            
            # Si todo falla, intentar con PBKDF2
            return JWTHandler._verify_pbkdf2_hash(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Obtener hash de contraseña.
        Usa PBKDF2 como método principal por compatibilidad.
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            str: Hash de la contraseña en formato pbkdf2_sha256$...
        """
        # Usar PBKDF2 como método principal para evitar problemas con bcrypt
        return JWTHandler._create_pbkdf2_hash(password)
    
    @staticmethod
    def get_bcrypt_password_hash(password: str) -> str:
        """
        Obtener hash de contraseña usando bcrypt.
        Solo usar si bcrypt está funcionando correctamente.
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            str: Hash bcrypt
            
        Raises:
            AuthenticationException: Si bcrypt no está disponible
        """
        if not BCRYPT_AVAILABLE:
            raise AuthenticationException("Bcrypt no disponible")
        
        try:
            return pwd_context.hash(password)
        except Exception as e:
            raise AuthenticationException(f"Error al generar hash bcrypt: {str(e)}")
    
    @staticmethod
    def _create_pbkdf2_hash(password: str, iterations: int = 100000) -> str:
        """
        Crear hash PBKDF2 con SHA-256.
        
        Args:
            password: Contraseña en texto plano
            iterations: Número de iteraciones (default: 100,000)
            
        Returns:
            str: Hash en formato pbkdf2_sha256$<iterations>$<salt>$<hash>
        """
        # Generar salt aleatorio (32 bytes = 256 bits)
        salt = secrets.token_bytes(32)
        
        # Generar hash PBKDF2
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        )
        
        # Codificar en base64 para almacenamiento
        salt_b64 = base64.b64encode(salt).decode('ascii')
        hash_b64 = base64.b64encode(hashed).decode('ascii')
        
        return f"pbkdf2_sha256${iterations}${salt_b64}${hash_b64}"
    
    @staticmethod
    def _verify_pbkdf2_hash(password: str, hashed_password: str) -> bool:
        """
        Verificar hash PBKDF2.
        
        Args:
            password: Contraseña en texto plano
            hashed_password: Hash en formato pbkdf2_sha256$...
            
        Returns:
            bool: True si la contraseña coincide
        """
        try:
            # Parsear el hash almacenado
            parts = hashed_password.split('$')
            if len(parts) != 4:
                return False
                
            algorithm, iterations_str, salt_b64, hash_b64 = parts
            
            if algorithm != 'pbkdf2_sha256':
                return False
                
            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64)
            expected_hash = base64.b64decode(hash_b64)
            
            # Calcular hash de la contraseña proporcionada
            actual_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations
            )
            
            # Comparar hashes de forma segura (timing-safe)
            return secrets.compare_digest(actual_hash, expected_hash)
        except Exception:
            return False
    
    @staticmethod
    def extract_user_from_token(token: str) -> Dict[str, Any]:
        """
        Extraer información del usuario del token sin verificar expiración.
        Útil para debugging o auditoría.
        
        Args:
            token: Token JWT
            
        Returns:
            Dict[str, Any]: Información del usuario
        """
        try:
            # Decodificar sin verificar expiración
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                options={"verify_exp": False}
            )
            
            return {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "role": payload.get("role"),
                "email": payload.get("email"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp")
            }
            
        except JWTError:
            return {}
    
    @staticmethod
    def get_user_from_token(token: str, db: Session) -> Optional[Dict[str, Any]]:
        """
        Obtener información del usuario desde el token JWT.
        
        Args:
            token: Token JWT
            db: Sesión de base de datos
            
        Returns:
            dict: Información del usuario o None
        """
        try:
            # Decodificar token
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                options={"verify_exp": False}  # No verificar expiración aquí
            )
            
            username = payload.get("sub")
            if not username:
                return None
            
            # Importar aquí para evitar dependencias circulares
            from sqlalchemy.orm import Session
            
            # Buscar usuario en la base de datos
            from ...infrastructure.database.models import User
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                return None
            
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, 'value') else user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None
            }
            
        except JWTError:
            return None
        except Exception as e:
            print(f"Error en get_user_from_token: {str(e)}")
            return None

    @classmethod
    def create_token_for_user(cls, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crear token JWT para usuario.
        
        Args:
            user_data: Datos del usuario
            
        Returns:
            Dict con token y metadatos
        """
        # Datos para incluir en el token
        token_data = {
            "sub": user_data["username"],
            "user_id": user_data["id"],
            "role": user_data["role"],
            "email": user_data["email"]
        }
        
        # Crear token
        access_token = cls.create_access_token(token_data)
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # En segundos
            "expires_at": expires_at.isoformat(),
            "user_id": user_data["id"],
            "username": user_data["username"],
            "role": user_data["role"]
        }
    
    @staticmethod
    def get_password_hash_compatibility(password: str) -> str:
        """
        Obtener hash de contraseña con compatibilidad hacia atrás.
        Intenta usar bcrypt, si falla usa PBKDF2.
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            str: Hash de la contraseña
        """
        if BCRYPT_AVAILABLE:
            try:
                # Limitar contraseña a 72 bytes para bcrypt
                if len(password.encode('utf-8')) > 72:
                    password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
                
                return pwd_context.hash(password)
            except Exception as e:
                print(f"Advertencia: bcrypt falló, usando PBKDF2: {str(e)}")
        
        # Usar PBKDF2 como fallback
        return JWTHandler._create_pbkdf2_hash(password)

# ==================== FUNCIONES HELPER (para compatibilidad) ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Función helper para verificar contraseña"""
    return JWTHandler.verify_password(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any]) -> str:
    """Función helper para crear token"""
    return JWTHandler.create_access_token(data)

def get_password_hash(password: str) -> str:
    """Función helper para obtener hash de contraseña"""
    return JWTHandler.get_password_hash(password)