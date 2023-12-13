from main import app
from ...plugin_info import module_name
from .show_router import router


def register_user_router():
    app.include_router(router, prefix="/bbs", tags=[module_name])
