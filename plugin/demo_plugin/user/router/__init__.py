from main import app
from ...plugin_info import module_name, router_prefix
from .show_router import router


def register_user_router():
    app.include_router(router, prefix=f"/{router_prefix}", tags=[module_name])
