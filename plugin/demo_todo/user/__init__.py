from main import app
from .user_router import router
from ..plugin_config import module_name, router_prefix


def register_user_router():
    app.include_router(router, prefix=router_prefix, tags=[module_name])