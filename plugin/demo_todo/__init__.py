# 패키지 외부에서 접근 가능한 모듈 목록
# "static" 폴더는 제외.
__all__ = [
    "admin",
    "user",
]

from .admin import register_admin_menu, register_admin_router
from .user import register_user_router


def register_plugin():
    """플러그인 활성화시 실행
    """
    register_admin_router()
    register_user_router()
    # 그밖에 필요한 작업 추가하세요


def unregister_plugin():
    """플러그인 비활성화시 실행
    """
    pass
    # 사용자와, 관리자 라우터 등록해제는 플러그인시스템에서 태그이름을 찾아서 자동으로 해제한다.
    # 기타 종료시 비활성화할 작업 추가하세요
