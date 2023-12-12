from main import app
from .show_router import router
from plugin.demo_todo.plugin_info import module_name

def register_user_router():
    app.include_router(router, prefix="/bbs", tags=[module_name])

print('this is demo_todo /router/__init__.py')
print('---z demo_todo_plugin ---')