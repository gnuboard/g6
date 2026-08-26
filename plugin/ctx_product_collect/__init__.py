__all__ = [
    "admin",
    "user",
]

from .admin import register_admin_menu, register_admin_router
from .user import register_user_router


def register_plugin():
    """플러그인 활성화 시 실행"""
    register_admin_router()
    register_user_router()


def unregister_plugin():
    """플러그인 비활성화 시 실행"""
    pass
