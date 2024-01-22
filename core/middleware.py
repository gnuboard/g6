import os
from user_agents import parse

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from core.plugin import (
    register_plugin_admin_menu, get_plugin_state_change_time,
    read_plugin_state, cache_plugin_state, cache_plugin_menu, register_plugin,
    unregister_plugin, delete_router_by_tagname
)
from core.template import TemplateService


def regist_core_middleware(app: FastAPI) -> None:
    """애플리케이션에 아래 미들웨어를 추가합니다.

    미들웨어의 실행 순서는 코드의 역순으로 실행됩니다.
    - main.py의 main_middleware()보다 먼저 실행됩니다.
    """

    # 기본으로 실행되는 core 미들웨어를 추가합니다.
    @app.middleware("http")
    async def core_middleware(request: Request, call_next):
        if not await should_run_middleware(request):
            return await call_next(request)

        # 플러그인 설정
        plugin_state_change_time = get_plugin_state_change_time()
        if cache_plugin_state.__getitem__('change_time') != plugin_state_change_time:
            # 플러그인 상태변경시 캐시를 업데이트.
            # 업데이트 이후 관리자 메뉴, 라우터 재등록/삭제
            new_plugin_state = read_plugin_state()
            register_plugin(new_plugin_state)
            unregister_plugin(new_plugin_state)
            for plugin in new_plugin_state:
                if not plugin.is_enable:
                    delete_router_by_tagname(app, plugin.module_name)

            cache_plugin_menu.__setitem__('admin_menus', register_plugin_admin_menu(new_plugin_state))
            cache_plugin_state.__setitem__('change_time', plugin_state_change_time)
            cache_plugin_state.__setitem__('info', new_plugin_state)

        # 접속환경 설정
        request.state.is_mobile = False
        request.state.is_responsive = TemplateService.get_responsive()

        # 반응형이라면 PC/모바일 버전 설정 세션을 초기화합니다.
        if request.state.is_responsive:
            request.session["is_mobile"] = False
        else:
            # 사용자가 설정한 PC/모바일 버전 설정 세션을 확인합니다.
            if request.session.get("is_mobile"):
                request.state.is_mobile = request.session.get("is_mobile", False)
            else:
                # User-Agent 헤더를 통해 모바일 여부를 판단합니다. (모바일과 태블릿 접속)
                user_agent = parse(request.headers.get("User-Agent", ""))
                if user_agent.is_mobile or user_agent.is_tablet:
                    request.state.is_mobile = True

        # 디바이스 기본값 설정
        request.state.device = "mobile" if request.state.is_mobile else "pc"

        # 미들웨어에서 라우터를 사용할 수 있도록 설정합니다.
        request.scope["router"] = app.router

        return await call_next(request)

    # 세션 미들웨어를 추가합니다.
    # .env 파일의 설정을 통해 secret_key, session_cookie를 설정할 수 있습니다.
    app.add_middleware(SessionMiddleware,
                       secret_key=os.getenv("SESSION_SECRET_KEY", "secret"),
                       session_cookie=os.getenv("SESSION_COOKIE_NAME", "session"),
                       max_age=60 * 60 * 3)

    # 클라이언트가 사용할 프로토콜을 결정하는 미들웨어를 추가합니다.
    app.add_middleware(BaseSchemeMiddleware)


async def should_run_middleware(request: Request) -> bool:
    """미들웨어의 실행 여부를 결정합니다.

    아래 요청에 대해서는 미들웨어를 실행하지 않습니다.
    - 토큰을 생성하는 요청
    - 정적 파일 요청 (css, js, 이미지 등)

    Args:
        request (Request): FastAPI의 Request 객체

    Returns:
        bool: 미들웨어를 실행할지 여부
    """
    path = request.url.path
    if (path.startswith('/generate_token')
            or path.startswith('/device/change')
            or path.startswith('/static')
            or path.startswith('/data')
            or path.endswith(('.css', '.js', '.jpg', '.png', '.gif', '.webp'))):
        return False

    return True


class BaseSchemeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # X-Forwarded-Proto 헤더를 통해 클라이언트가 사용하는 실제 프로토콜을 결정합니다.
        request.scope["scheme"] = request.headers.get("X-Forwarded-Proto", "http")
        return await call_next(request)
