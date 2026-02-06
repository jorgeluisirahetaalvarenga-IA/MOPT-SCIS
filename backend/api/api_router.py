from fastapi import APIRouter

from api.routers.auth import router as auth_router
from api.routers.inventory import router as inventory_router
from api.routers.products import router as products_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(inventory_router)
api_router.include_router(products_router)