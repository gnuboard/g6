from main import app
from ..plugin_config import module_name, router_prefix
from ..user.user_router import router


def register_user_router():
    app.include_router(router, prefix=router_prefix, tags=[module_name])