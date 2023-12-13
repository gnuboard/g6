from main import app
from .show_router import router
from ...plugin_info import module_name, router_prefix


def register_user_router():
    app.include_router(router, prefix=f"/{router_prefix}", tags=[module_name])
