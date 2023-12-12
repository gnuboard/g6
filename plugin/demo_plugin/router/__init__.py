from ..plugin_info import module_name
from plugin.demo_plugin.router.show_router import show_router
from main import app

app.include_router(show_router, prefix="/bbs", tags=[module_name])
