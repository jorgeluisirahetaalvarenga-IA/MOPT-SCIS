"""
Excepciones específicas del dominio.
Definen el lenguaje ubicuo para errores de negocio.

Diferencia con core/exceptions.py:
- core/exceptions.py: Excepciones base del sistema
- domain/exceptions.py: Excepciones específicas del dominio de inventario
"""
from ...app.core.exceptions import DomainException, BusinessRuleException


class ProductNotFoundError(DomainException):
    """Producto no encontrado en el sistema"""
    def __init__(self, product_id: int):
        super().__init__(
            message=f"Producto con ID {product_id} no encontrado",
            details={"product_id": product_id, "resource": "Product"}
        )


class InsufficientStockError(BusinessRuleException):
    """Stock insuficiente para realizar operación"""
    def __init__(self, product_id: int, available: int, required: int):
        super().__init__(
            message=f"Stock insuficiente para producto {product_id}. Disponible: {available}, Requerido: {required}",
            rule_name="insufficient_stock",
            details={
                "product_id": product_id,
                "available": available,
                "required": required,
                "deficit": required - available
            }
        )


class StockExceedsMaximumError(BusinessRuleException):
    """Stock excede el máximo permitido"""
    def __init__(self, product_id: int, current: int, max_allowed: int):
        super().__init__(
            message=f"Stock excede máximo permitido para producto {product_id}. Actual: {current}, Máximo: {max_allowed}",
            rule_name="stock_exceeds_maximum",
            details={
                "product_id": product_id,
                "current": current,
                "max_allowed": max_allowed,
                "excess": current - max_allowed
            }
        )


class InvalidMovementTypeError(BusinessRuleException):
    """Tipo de movimiento inválido"""
    def __init__(self, movement_type: str):
        super().__init__(
            message=f"Tipo de movimiento inválido: {movement_type}",
            rule_name="invalid_movement_type",
            details={
                "movement_type": movement_type,
                "valid_types": ["IN", "OUT"]
            }
        )


class UserNotFoundError(DomainException):
    """Usuario no encontrado en el sistema"""
    def __init__(self, user_id: int = None, username: str = None):
        identifier = f"ID {user_id}" if user_id else f"usuario '{username}'"
        super().__init__(
            message=f"Usuario {identifier} no encontrado",
            details={"user_id": user_id, "username": username, "resource": "User"}
        )


class InvalidCredentialsError(DomainException):
    """Credenciales de autenticación inválidas"""
    def __init__(self, username: str):
        super().__init__(
            message=f"Credenciales inválidas para usuario '{username}'",
            details={"username": username}
        )


class UserInactiveError(BusinessRuleException):
    """Usuario inactivo"""
    def __init__(self, user_id: int):
        super().__init__(
            message=f"Usuario con ID {user_id} está inactivo",
            rule_name="user_inactive",
            details={"user_id": user_id}
        )


class InsufficientPermissionsError(BusinessRuleException):
    """Permisos insuficientes para operación"""
    def __init__(self, user_role: str, required_role: str):
        super().__init__(
            message=f"Rol '{user_role}' no tiene permisos para esta operación. Se requiere: '{required_role}'",
            rule_name="insufficient_permissions",
            details={
                "user_role": user_role,
                "required_role": required_role
            }
        )