"""
Contenedor de dependencias para la aplicación.
Centraliza la creación de repositorios y servicios.
"""

from sqlalchemy.orm import Session


class DependencyContainer:
    """Contenedor para gestión de dependencias"""
    
    @staticmethod
    def get_product_repository(db: Session):
        """Proveer repositorio de productos"""
        from .repositories.product_repository_impl import SQLAlchemyProductRepository
        return SQLAlchemyProductRepository(db)
    
    @staticmethod
    def get_movement_repository(db: Session):
        """Proveer repositorio de movimientos"""
        from .repositories.movement_repository_impl import SQLAlchemyMovementRepository
        return SQLAlchemyMovementRepository(db)
    
    @staticmethod
    def get_user_repository(db: Session):
        """Proveer repositorio de usuarios"""
        from .repositories.user_repository_impl import SQLAlchemyUserRepository
        return SQLAlchemyUserRepository(db)
    
    @staticmethod
    def get_case_use_authenticate_user(db: Session):
        """Proveer caso de uso de autenticación"""
        from ...app.application.use_cases.authenticate_user import (
            AuthenticateUserUseCase, 
            JWTAuthenticator
        )
        
        user_repo = DependencyContainer.get_user_repository(db)
        return AuthenticateUserUseCase(
            user_repository=user_repo,
            authenticator=JWTAuthenticator()
        )
    
    @staticmethod
    def get_case_use_register_movement(db: Session):
        """Proveer caso de uso de registro de movimiento"""
        from ...app.application.use_cases.register_movement import (
            RegisterMovementUseCase
        )
        
        product_repo = DependencyContainer.get_product_repository(db)
        movement_repo = DependencyContainer.get_movement_repository(db)
        user_repo = DependencyContainer.get_user_repository(db)
        
        return RegisterMovementUseCase(
            product_repository=product_repo,
            movement_repository=movement_repo,
            user_repository=user_repo
        )


# Instancia global del contenedor
container = DependencyContainer()