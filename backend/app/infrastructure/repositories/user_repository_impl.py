"""
Implementación concreta del repositorio de usuarios con SQLAlchemy.
Adaptador para operaciones de autenticación y gestión de usuarios.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from ....app.domain.entities.user import User
from ....app.application.ports.user_repository import UserRepository
from ....infrastructure.database.models import User as UserModel
from ....infrastructure.database.models import UserRole as UserRoleModel


class SQLAlchemyUserRepository(UserRepository):
    """Implementación concreta con SQLAlchemy para usuarios"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def save(self, user: User) -> User:
        """Guardar o actualizar un usuario"""
        try:
            if user.id:
                # Actualizar usuario existente
                db_user = self.session.query(UserModel)\
                    .filter(UserModel.id == user.id)\
                    .first()
                
                if not db_user:
                    raise ValueError(f"Usuario con id {user.id} no encontrado")
                
                # Mapear de dominio a persistencia
                db_user.username = user.username
                db_user.email = user.email
                db_user.hashed_password = user.hashed_password
                db_user.full_name = user.full_name
                db_user.role = UserRoleModel(user.role.value)
                db_user.is_active = user.is_active
                
            else:
                # Crear nuevo usuario
                db_user = UserModel(
                    username=user.username,
                    email=user.email,
                    hashed_password=user.hashed_password,
                    full_name=user.full_name,
                    role=UserRoleModel(user.role.value),
                    is_active=user.is_active
                )
                self.session.add(db_user)
            
            self.session.commit()
            self.session.refresh(db_user)
            
            return self._to_domain(db_user)
            
        except Exception as e:
            self.session.rollback()
            raise e
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """Buscar usuario por ID"""
        db_user = self.session.query(UserModel)\
            .filter(UserModel.id == user_id)\
            .first()
        
        return self._to_domain(db_user) if db_user else None
    
    def find_by_username(self, username: str) -> Optional[User]:
        """Buscar usuario por nombre de usuario"""
        db_user = self.session.query(UserModel)\
            .filter(UserModel.username == username)\
            .first()
        
        return self._to_domain(db_user) if db_user else None
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Buscar usuario por email"""
        db_user = self.session.query(UserModel)\
            .filter(UserModel.email == email)\
            .first()
        
        return self._to_domain(db_user) if db_user else None
    
    def find_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ) -> List[User]:
        """Listar usuarios con paginación y filtros"""
        query = self.session.query(UserModel)
        
        # Aplicar filtros
        if is_active is not None:
            query = query.filter(UserModel.is_active == is_active)
        
        if role:
            query = query.filter(UserModel.role == UserRoleModel(role))
        
        # Ordenar y paginar
        db_users = query.order_by(UserModel.username)\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [self._to_domain(u) for u in db_users]
    
    def authenticate(self, username: str, password_verifier) -> Optional[User]:
        """
        Autenticar usuario con credenciales.
        
        Args:
            username: Nombre de usuario
            password_verifier: Función que verifica contraseña
        """
        db_user = self.session.query(UserModel)\
            .filter(UserModel.username == username)\
            .first()
        
        if not db_user:
            return None
        
        # Convertir a dominio para usar método authenticate
        user = self._to_domain(db_user)
        if not user:
            return None
        
        # La entidad User maneja la lógica de autenticación
        try:
            if user.authenticate(password_verifier.__closure__[0].cell_contents, password_verifier):
                # Actualizar último login
                db_user.updated_at = user.updated_at
                self.session.commit()
                return user
        except Exception:
            pass
        
        return None
    
    def exists_by_username(self, username: str) -> bool:
        """Verificar si existe usuario por nombre de usuario"""
        return self.session.query(UserModel)\
            .filter(UserModel.username == username)\
            .count() > 0
    
    def exists_by_email(self, email: str) -> bool:
        """Verificar si existe usuario por email"""
        return self.session.query(UserModel)\
            .filter(UserModel.email == email)\
            .count() > 0
    
    def count(self) -> int:
        """Contar total de usuarios"""
        return self.session.query(UserModel).count()
    
    def _to_domain(self, db_user: UserModel) -> Optional[User]:
        """Convertir de modelo de persistencia a entidad de dominio"""
        if not db_user:
            return None
        
        from ....app.domain.entities.user import UserRole
        
        return User(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            hashed_password=db_user.hashed_password,
            full_name=db_user.full_name,
            role=UserRole(db_user.role.value),
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )