import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Path, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import TypeAdapter
from sqlalchemy import select, insert, inspect
from starlette.staticfiles import StaticFiles

import core.models as models
from core.database import DBConnect, db_session
from core.exception import (
    AlertException,
    regist_core_exception_handler,
    template_response
)
from core.middleware import should_run_middleware, regist_core_middleware
from core.plugin import (
    cache_plugin_state, cache_plugin_menu, get_plugin_state_change_time,
    import_plugin_by_states, read_plugin_state, register_plugin,
    register_plugin_admin_menu, register_statics
)
from core.template import register_theme_statics, TemplateService, UserTemplates
from lib.common import *
from lib.member_lib import is_super_admin, MemberService
from lib.point import insert_point
from lib.template_filters import default_if_none
from lib.token import create_session_token

# .env 파일로부터 환경 변수를 로드합니다.
# 이 함수는 해당 파일 내의 키-값 쌍을 환경 변수로 로드하는 데 사용됩니다.
load_dotenv()

# 'APP_IS_DEBUG' 환경 변수를 가져와서 boolean 타입으로 변환합니다.
# 이 환경 변수가 설정되어 있지 않은 경우, 기본값으로 False를 사용합니다.
# TypeAdapter는 값을 특정 타입으로 변환하는 데 사용되는 유틸리티 클래스입니다.
APP_IS_DEBUG = TypeAdapter(bool).validate_python(os.getenv("APP_IS_DEBUG", False))

# APP_IS_DEBUG 값이 True일 경우, 디버그 모드가 활성화됩니다.
app = FastAPI(debug=APP_IS_DEBUG)

templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none

from admin.admin import router as admin_router
from install.router import router as install_router
from bbs.board import router as board_router
from bbs.login import router as login_router
from bbs.register import router as register_router
from bbs.content import router as content_router
from bbs.faq import router as faq_router
from bbs.qa import router as qa_router
from bbs.member_profile import router as user_profile_router
from bbs.profile import router as profile_router
from bbs.memo import router as memo_router
from bbs.poll import router as poll_router
from bbs.point import router as point_router
from bbs.scrap import router as scrap_router
from bbs.board_new import router as board_new_router
from bbs.ajax_good import router as good_router
from bbs.ajax_autosave import router as autosave_router
from bbs.member_leave import router as member_leave_router
from bbs.member_find import router as member_find_router
from bbs.social import router as social_router
from bbs.password import router as password_router
from bbs.search import router as search_router
from bbs.current_connect import router as current_connect_router
from lib.editor.ckeditor4 import router as editor_router

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

app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(install_router, prefix="/install", tags=["install"])
app.include_router(board_router, prefix="/board", tags=["board"])
app.include_router(login_router, prefix="/bbs", tags=["login"])
app.include_router(register_router, prefix="/bbs", tags=["register"])
app.include_router(user_profile_router, prefix="/bbs", tags=["profile"])
app.include_router(profile_router, prefix="/bbs", tags=["profile"])
app.include_router(member_leave_router, prefix="/bbs", tags=["member_leave"])
app.include_router(member_find_router, prefix="/bbs", tags=["member_find"])
app.include_router(content_router, prefix="/bbs", tags=["content"])
app.include_router(faq_router, prefix="/bbs", tags=["faq"])
app.include_router(qa_router, prefix="/bbs", tags=["qa"])
app.include_router(memo_router, prefix="/bbs", tags=["memo"])
app.include_router(poll_router, prefix="/bbs", tags=["poll"])
app.include_router(point_router, prefix="/bbs", tags=["point"])
app.include_router(scrap_router, prefix="/bbs", tags=["scrap"])
app.include_router(board_new_router, prefix="/bbs", tags=["board_new"])
app.include_router(good_router, prefix="/bbs/ajax", tags=["good"])
app.include_router(autosave_router, prefix="/bbs/ajax", tags=["autosave"])
app.include_router(social_router, prefix="/bbs", tags=["social"])
app.include_router(password_router, prefix="/bbs", tags=["password"])
app.include_router(search_router, prefix="/bbs", tags=["search"])
app.include_router(current_connect_router, prefix="/bbs", tags=["current_connect"])
app.include_router(editor_router, prefix="/editor", tags=["editor"])


@app.middleware("http")
async def main_middleware(request: Request, call_next):
    """요청마다 항상 실행되는 미들웨어"""

    if not await should_run_middleware(request):
        return await call_next(request)

    # 데이터베이스 설치여부 체크
    db_connect = DBConnect()
    db = db_connect.sessionLocal()
    url_path = request.url.path

    try:
        if not url_path.startswith("/install"):
            if not os.path.exists(ENV_PATH):
                raise AlertException(".env 파일이 없습니다. 설치를 진행해 주세요.", 400, "/install")

            if not inspect(db_connect.engine).has_table(db_connect.table_prefix + "config"):
                raise AlertException("DB 또는 테이블이 존재하지 않습니다. 설치를 진행해 주세요.", 400, "/install")
        else:
            return await call_next(request)

    except AlertException as e:
        context = {"request": request, "errors": e.detail, "url": e.url}
        return template_response("alert.html", context, e.status_code)

    # 기본환경설정 조회 및 설정
    config = db.scalar(select(Config))
    request.state.config = config
    request.state.title = config.cf_title

    # 에디터 전역변수
    request.state.editor = config.cf_editor
    request.state.use_editor = True if config.cf_editor else False

    # 쿠키도메인 전역변수
    request.state.cookie_domain = os.getenv("COOKIE_DOMAIN", "")

    member = None
    is_autologin = False
    ss_mb_key = None
    session_mb_id = request.session.get("ss_mb_id", "")
    cookie_mb_id = request.cookies.get("ck_mb_id", "")
    current_ip = get_client_ip(request)

    # 로그인 세션 유지 중이라면
    if session_mb_id:
        member = MemberService.create_by_id(db, session_mb_id)
        if member.is_intercept_or_leave():
            request.session.clear()
            member = None
    # 자동 로그인 쿠키가 있다면
    elif cookie_mb_id:
        mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20]
        member = MemberService.create_by_id(db, mb_id)
        # 최고관리자는 보안상 자동로그인 기능을 사용하지 않는다.
        if (not is_super_admin(request, mb_id)
                and member.is_email_certify(bool(config.cf_use_email_certify))
                and not member.is_intercept_or_leave()):
            # 쿠키에 저장된 키와 여러가지 정보를 조합하여 만든 키가 일치한다면 로그인으로 간주
            ss_mb_key = session_member_key(request, member)
            if request.cookies.get("ck_auto") == ss_mb_key:
                request.session["ss_mb_id"] = cookie_mb_id
                is_autologin = True

    if member:
        # 오늘 처음 로그인 이라면 포인트 지급 및 로그인 정보 업데이트
        ymd_str = datetime.now().strftime("%Y-%m-%d")
        if member.mb_today_login.strftime("%Y-%m-%d") != ymd_str:
            insert_point(request, member.mb_id, config.cf_login_point, ymd_str + " 첫로그인", "@login", member.mb_id, ymd_str)

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

    age_1day = 60 * 60 * 24
    cookie_domain = request.state.cookie_domain

    # 자동로그인 쿠키 재설정
    # is_autologin과 세션을 확인해서 로그아웃 처리 이후 쿠키가 재설정되는 것을 방지
    if is_autologin and request.session.get("ss_mb_id"):
        response.set_cookie(key="ck_mb_id", value=cookie_mb_id,
                            max_age=age_1day * 30, domain=cookie_domain)
        response.set_cookie(key="ck_auto", value=ss_mb_key,
                            max_age=age_1day * 30, domain=cookie_domain)
    # 접속자 기록
    ck_visit_ip = request.cookies.get('ck_visit_ip', None)
    if ck_visit_ip != current_ip:
        response.set_cookie(key="ck_visit_ip", value=current_ip,
                            max_age=age_1day, domain=cookie_domain)
        record_visit(request)

    # 현재 접속자 데이터 갱신
    if (not request.state.is_super_admin
            and not url_path.startswith("/admin")):
        current_login = db.scalar(
            select(models.Login)
            .where(models.Login.lo_ip == current_ip)
        )
        if current_login:
            current_login.lo_ip = current_ip
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

    db.close()

    return response

# 기본 실행할 미들웨어를 추가하는 함수
# 함수는 반드시 main_middleware 함수의 아래에 위치해야 합니다.
# 그렇지 않으면 아래와 같은 오류를 만날 수 있습니다.
# AssertionError: SessionMiddleware must be installed to access request.session
regist_core_middleware(app)

# 기본 예외처리 핸들러를 등록하는 함수
regist_core_exception_handler(app)


# 예약 작업을 관리할 스케줄러 생성
# https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html
scheduler = BackgroundScheduler(timezone='Asia/Seoul')
@scheduler.scheduled_job('cron', hour=10, id='remove_data_by_config')
def job():
    delete_old_records()
# FastAPI 앱 시작 시 스케줄러 시작
scheduler.start()


@app.get("/", response_class=HTMLResponse)
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
        "newwins": get_newwins(request),
        "boards": boards,
    }
    return templates.TemplateResponse("/index.html", context)


@app.post("/generate_token")
async def generate_token(request: Request) -> JSONResponse:
    """세션 토큰 생성 후 반환

    Args:
        request (Request): FastAPI의 Request 객체

    Returns:
        JSONResponse: 성공 여부와 토큰을 포함한 JSON 응답
    """
    token = create_session_token(request)

    return JSONResponse(content={"success": True, "token": token})


@app.get("/device/change/{device}")
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
            and not TemplateService.get_responsive()):
        if device == "pc":
            request.session["is_mobile"] = False
        else:
            request.session["is_mobile"] = True

    referer = request.headers.get("Referer", "/")
    return RedirectResponse(referer, status_code=303)
