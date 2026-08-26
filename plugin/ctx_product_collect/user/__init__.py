from fastapi import Depends

from lib.dependency.dependencies import check_use_template, set_template_basic_data
from main import app
from .user_router import router, api_router
from ..plugin_config import module_name, router_prefix


def register_user_router():
    """사용자 라우터 등록"""
    # 일반 페이지 라우터 — 템플릿 의존성 포함
    app.include_router(
        router,
        prefix=router_prefix,
        tags=[module_name],
        include_in_schema=False,
        dependencies=[
            Depends(check_use_template),
            Depends(set_template_basic_data),
        ],
    )
    # API 프록시 라우터 — 템플릿 의존성 없이 JSON 응답 전용
    app.include_router(
        api_router,
        prefix=router_prefix,
        tags=[module_name],
        include_in_schema=False,
    )
