from main import app
from plugin.demo_todo.router.show_router import show_router
from ..plugin_info import module_name

app.include_router(show_router, prefix="/bbs", tags=[module_name])

print('this is demo_todo /router/__init__.py')
print('---z demo_todo_plugin ---')