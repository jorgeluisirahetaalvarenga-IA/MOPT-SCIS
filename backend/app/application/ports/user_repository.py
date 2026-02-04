"""
Puerto para repositorio de usuarios.
Define operaciones de autenticación y gestión de usuarios.
"""
from abc import ABC, abstractmethod
from typing import Optional, List

from ....app.domain.entities.user import User

class UserRepository(ABC):
    """Puerto para operaciones de usuarios"""
    
    @abstractmethod
    def save(self, user: User) -> User:
        """
        Guardar o actualizar un usuario.
        
        Args:
            user: Usuario a persistir
            
        Returns:
            User: Usuario persistido
        """
        pass
    
    @abstractmethod
    def find_by_id(self, user_id: int) -> Optional[User]:
        """
        Buscar usuario por ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Optional[User]: Usuario encontrado o None
        """
        pass
    
    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """
        Buscar usuario por nombre de usuario.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            Optional[User]: Usuario encontrado o None
        """
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        """
        Buscar usuario por email.
        
        Args:
            email: Email del usuario
            
        Returns:
            Optional[User]: Usuario encontrado o None
        """
        pass
    
    @abstractmethod
    def find_all(
        self, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ) -> List[User]:
        """
        Listar usuarios con paginación y filtros.
        
        Args:
            skip: Saltar registros
            limit: Límite de registros
            is_active: Filtrar por estado activo
            role: Filtrar por rol
            
        Returns:
            List[User]: Lista de usuarios
        """
        pass
    
    @abstractmethod
    def authenticate(self, username: str, password_verifier) -> Optional[User]:
        """
        Autenticar usuario con credenciales.
        
        Args:
            username: Nombre de usuario
            password_verifier: Función que verifica contraseña
            
        Returns:
            Optional[User]: Usuario autenticado o None
        """
        pass
    
    @abstractmethod
    def exists_by_username(self, username: str) -> bool:
        """
        Verificar si existe usuario por nombre de usuario.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            bool: True si existe
        """
        pass
    
    @abstractmethod
    def exists_by_email(self, email: str) -> bool:
        """
        Verificar si existe usuario por email.
        
        Args:
            email: Email
            
        Returns:
            bool: True si existe
        """
        pass
    
    @abstractmethod
    def count(self) -> int:
        """
        Contar total de usuarios.
        
        Returns:
            int: Número total de usuarios
        """
        pass