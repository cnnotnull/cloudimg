from app.api.storage import router as storage_router
from app.api.image import router as image_router
from app.api.config import router as config_router
from app.api.auth import router as auth_router

__all__ = ["storage_router", "image_router", "config_router", "auth_router"]
