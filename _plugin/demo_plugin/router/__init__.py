from _plugin.demo_plugin.router.show_router import show_router
from main import app

print('show router __init__.py')
app.include_router(show_router, prefix="/show", tags=["show"])