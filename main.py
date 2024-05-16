import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Path, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import ProgrammingError
from starlette.staticfiles import StaticFiles

from core import models
from core.database import DBConnect
from core.exception import AlertException, regist_core_exception_handler, template_response
from core.middleware import regist_core_middleware, should_run_middleware
from core.plugin import (
    cache_plugin_menu, cache_plugin_state, get_plugin_state_change_time,
    import_plugin_by_states, read_plugin_state, register_plugin,
    register_plugin_admin_menu, register_statics,
)
from core.routers import router as template_router
from core.settings import ENV_PATH, settings
from core.template import UserTemplates, register_theme_statics
from lib.common import (
    get_client_ip, is_intercept_ip, is_possible_ip, session_member_key
)
from lib.dependency.dependencies import check_use_template
from lib.member import is_super_admin
from lib.scheduler import scheduler
from lib.template_filters import default_if_none
from lib.token import create_session_token
from service.member_service import MemberService
from service.point_service import PointService
from service.visit_service import VisitService

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
    description=""
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

app.include_router(admin_router)
app.include_router(api_router)
app.include_router(template_router)
app.include_router(install_router)
app.include_router(login_router)


@app.middleware("http")
async def main_middleware(request: Request, call_next):
    """요청마다 항상 실행되는 미들웨어"""

    if not await should_run_middleware(request):
        return await call_next(request)

    # 데이터베이스 설치여부 체크
    with DBConnect().sessionLocal() as db:
        url_path = request.url.path
        config = None

        try:
            if not url_path.startswith("/install"):
                if not os.path.exists(ENV_PATH):
                    raise AlertException(".env 파일이 없습니다. 설치를 진행해 주세요.", 400, "/install")
                # 기본환경설정 테이블 조회
                config = db.scalar(select(models.Config))
            else:
                return await call_next(request)

        except AlertException as e:
            context = {"request": request, "errors": e.detail, "url": e.url}
            return template_response("alert.html", context, e.status_code)

        except ProgrammingError as e:
            context = {
                "request": request,
                "errors": "DB 테이블 또는 설정정보가 존재하지 않습니다. 설치를 다시 진행해 주세요.",
                "url": "/install"
            }
            return template_response("alert.html", context, 400)

        # 기본환경설정 조회 및 설정
        request.state.config = config
        request.state.title = config.cf_title

        # 에디터 전역변수
        request.state.editor = config.cf_editor
        request.state.use_editor = True if config.cf_editor else False

        # 쿠키도메인 전역변수
        request.state.cookie_domain = cookie_domain = settings.COOKIE_DOMAIN

        member = None
        is_autologin = False
        ss_mb_key = None
        session_mb_id = request.session.get("ss_mb_id", "")
        cookie_mb_id = request.cookies.get("ck_mb_id", "")
        current_ip = get_client_ip(request)

        try:
            member_service = MemberService(request, db)
            # 로그인 세션 유지 중이라면
            if session_mb_id:
                member = member_service.get_member(session_mb_id)
                # 회원 정보가 없거나 탈퇴한 회원이라면 세션을 초기화
                if not member_service.is_activated(member)[0]:
                    request.session.clear()
                    member = None

            # 자동 로그인 쿠키가 있다면
            elif cookie_mb_id:
                mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20]
                member = member_service.get_member(session_mb_id)

                # 최고관리자는 보안상 자동로그인 기능을 사용하지 않는다.
                if (not is_super_admin(request, mb_id)
                        and member_service.is_member_email_certified(member)[0]
                        and member_service.is_activated(member)[0]):
                    # 쿠키에 저장된 키와 서버에서 생성한 키가 일치하는지 검사
                    ss_mb_key = session_member_key(request, member)
                    if request.cookies.get("ck_auto") == ss_mb_key:
                        request.session["ss_mb_id"] = cookie_mb_id
                        is_autologin = True
        except AlertException as e:
            context = {"request": request, "errors": e.detail, "url": "/"}
            response = template_response("alert.html", context, e.status_code)
            response.delete_cookie("ck_auto")
            response.delete_cookie("ck_mb_id")
            request.session.clear()
            return response

        if member:
            # 오늘 처음 로그인 이라면 포인트 지급 및 로그인 정보 업데이트
            ymd_str = datetime.now().strftime("%Y-%m-%d")
            if member.mb_today_login.strftime("%Y-%m-%d") != ymd_str:
                point_service = PointService(request, db, member_service)
                point_service.save_point(
                    member.mb_id, config.cf_login_point, ymd_str + " 첫로그인",
                    "@login", member.mb_id, ymd_str)

                member.mb_today_login = datetime.now()
                member.mb_login_ip = request.client.host
                db.commit()

        # 로그인한 회원 정보
        request.state.login_member = member
        # 최고관리자 여부
        request.state.is_super_admin = is_super_admin(request, getattr(member, "mb_id", None))

        # 접근가능/차단 IP 체크
        # - IP 체크 기능을 사용할 때 is_super_admin 여부를 확인하기 때문에 로그인 코드 이후에 실행
        if not is_possible_ip(request, current_ip):
            return HTMLResponse("<meta charset=utf-8>접근이 허용되지 않은 IP 입니다.")
        if is_intercept_ip(request, current_ip):
            return HTMLResponse("<meta charset=utf-8>접근이 차단된 IP 입니다.")

    # 응답 객체 설정
    response: Response = await call_next(request)

    with DBConnect().sessionLocal() as db:
        age_1day = 60 * 60 * 24

        # 자동로그인 쿠키 재설정
        # is_autologin과 세션을 확인해서 로그아웃 처리 이후 쿠키가 재설정되는 것을 방지
        if is_autologin and request.session.get("ss_mb_id"):
            response.set_cookie(key="ck_mb_id", value=cookie_mb_id,
                                max_age=age_1day * 30, domain=cookie_domain)
            response.set_cookie(key="ck_auto", value=ss_mb_key,
                                max_age=age_1day * 30, domain=cookie_domain)
        # 방문자 이력 기록
        ck_visit_ip = request.cookies.get('ck_visit_ip', None)
        if ck_visit_ip != current_ip:
            response.set_cookie(key="ck_visit_ip", value=current_ip,
                                max_age=age_1day, domain=cookie_domain)
            visit_service = VisitService(request, db)
            visit_service.create_visit_record()

        try:
            # 현재 방문자 데이터 갱신
            if (not request.state.is_super_admin
                    and not url_path.startswith("/admin")):
                current_login = db.scalar(
                    select(models.Login)
                    .where(models.Login.lo_ip == current_ip)
                )
                if current_login:
                    current_login.mb_id = getattr(member, "mb_id", "")
                    current_login.lo_datetime = datetime.now()
                    current_login.lo_location = url_path
                    current_login.lo_url = url_path
                else:
                    db.execute(
                        insert(models.Login).values(
                            lo_ip=current_ip,
                            mb_id=getattr(member, "mb_id", ""),
                            lo_datetime=datetime.now(),
                            lo_location=url_path,
                            lo_url=url_path)
                    )
                db.commit()

            # 현재 로그인한 이력 삭제
            config_time = timedelta(minutes=int(config.cf_login_minutes))
            db.execute(delete(models.Login)
                    .where(models.Login.lo_datetime < datetime.now() - config_time))
            db.commit()

        except Exception as e:
            print(e)

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
