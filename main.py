import os

from contextlib import asynccontextmanager
from wsgiref import validate
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from starlette.staticfiles import StaticFiles

from core import models
from core.database import db_session
from core.exception import regist_core_exception_handler
from core.middleware import regist_core_middleware, should_run_middleware
from core.plugin import (
    cache_plugin_menu, cache_plugin_state, get_plugin_state_change_time,
    import_plugin_by_states, read_plugin_state, register_plugin,
    register_plugin_admin_menu, register_statics,
)
from core.routers import router as template_router
from core.settings import settings
from core.template import UserTemplates, register_theme_statics
from lib.dependency.auth import manage_member_authentication
from lib.dependency.dependencies import (
    check_ip, check_use_template, check_visit_record, get_config, set_current_connect, validate_installed
)
from lib.newwin import get_newwins_except_cookie
from lib.scheduler import scheduler
from lib.template_filters import default_if_none
from lib.token import create_session_token

from admin.admin import router as admin_router
from install.router import router as install_router
from bbs.login import router as login_router

from api.v1.routers import router as api_router

# .env 파일로부터 환경 변수를 로드합니다.
# 이 함수는 해당 파일 내의 키-값 쌍을 환경 변수로 로드하는 데 사용됩니다.
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    앱의 시작과 종료 시점에 실행되는 코드를 정의합니다.
    - yield 이전의 코드: 서버가 시작될 때 실행
    - yield 이후의 코드: 서버가 종료될 때 실행
    """
    yield
    scheduler.remove_flag()


app = FastAPI(
    debug=settings.APP_IS_DEBUG,  # 디버그 모드가 활성화 설정
    lifespan=lifespan,
    title="그누보드6",
    description="",
    dependencies=[Depends(get_config),
                  Depends(check_ip)],
)
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none

# git clone으로 소스를 받은 경우에는 data디렉토리가 없으므로 생성해야 함
if not os.path.exists("data"):
    os.mkdir("data")

# 각 경로에 있는 파일들을 정적 파일로 등록합니다.
register_theme_statics(app)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

# 플러그인 라우터 우선 등록
plugin_states = read_plugin_state()
import_plugin_by_states(plugin_states)
register_plugin(plugin_states)
register_statics(app, plugin_states)

cache_plugin_state.__setitem__('info', plugin_states)
cache_plugin_state.__setitem__('change_time', get_plugin_state_change_time())
cache_plugin_menu.__setitem__('admin_menus', register_plugin_admin_menu(plugin_states))

# 라우터 등록
app.include_router(api_router)
app.include_router(install_router)
app.include_router(admin_router)
app.include_router(login_router)
app.include_router(template_router)


@app.middleware("http")
async def main_middleware(request: Request, call_next):
    """요청마다 항상 실행되는 미들웨어"""

    if not await should_run_middleware(request):
        return await call_next(request)

    response: Response = await call_next(request)

    return response

# 기본 실행할 미들웨어를 추가하는 함수
# 함수는 반드시 main_middleware 함수의 아래에 위치해야 합니다.
# 그렇지 않으면 아래와 같은 오류를 만날 수 있습니다.
# AssertionError: SessionMiddleware must be installed to access request.session
regist_core_middleware(app)

# 기본 예외처리 핸들러를 등록하는 함수
regist_core_exception_handler(app)

# 스케줄러 등록 및 실행
scheduler.run_scheduler()


@app.get("/",
         dependencies=[Depends(validate_installed),
                       Depends(check_use_template),
                       Depends(manage_member_authentication),
                       Depends(check_visit_record),
                       Depends(set_current_connect)],
         response_class=HTMLResponse,
         include_in_schema=False)
async def index(request: Request, db: db_session):
    """
    메인 페이지
    """
    # 게시판 목록 조회
    query_boards = (
        select(models.Board)
        .join(models.Board.group)
        .where(models.Board.bo_device != 'mobile')
        .order_by(
            models.Group.gr_order,
            models.Board.bo_order
        )
    )
    # 최고관리자가 아니라면 인증게시판 및 갤러리/공지사항 게시판은 제외
    if not request.state.is_super_admin:
        query_boards = query_boards.where(
            models.Board.bo_use_cert == '',
            models.Board.bo_table.notin_(['notice', 'gallery'])
        )
    boards = db.scalars(query_boards).all()

    context = {
        "request": request,
        "newwins": get_newwins_except_cookie(request),
        "boards": boards,
    }
    return templates.TemplateResponse("/index.html", context)


@app.post("/generate_token",
          include_in_schema=False)
async def generate_token(request: Request) -> JSONResponse:
    """세션 토큰 생성 후 반환

    Args:
        request (Request): FastAPI의 Request 객체

    Returns:
        JSONResponse: 성공 여부와 토큰을 포함한 JSON 응답
    """
    token = create_session_token(request)

    return JSONResponse(content={"success": True, "token": token})


@app.get("/device/change/{device}",
         dependencies=[Depends(check_use_template)],
         include_in_schema=False)
async def device_change(
    request: Request,
    device: str = Path(...)
) -> RedirectResponse:
    """접속환경(디바이스) 변경
    - PC/모바일 버전을 강제로 변경합니다.

    Args:
        request (Request): FastAPI의 Request 객체
        device (str, optional): 변경할 디바이스. Defaults to Path(...).

    Returns:
        RedirectResponse: 이전 페이지로 리디렉션
    """
    if (device in ["pc", "mobile"]
            and not settings.IS_RESPONSIVE):
        if device == "pc":
            request.session["is_mobile"] = False
        else:
            request.session["is_mobile"] = True

    referer = request.headers.get("Referer", "/")
    return RedirectResponse(referer, status_code=303)
