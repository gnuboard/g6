import datetime
import secrets

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import TypeAdapter
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from user_agents import parse

from common.database import DBConnect, db_session
import common.models as models
from lib.common import *
from lib.member_lib import MemberService
from lib.plugin.service import register_statics, register_plugin_admin_menu, get_plugin_state_change_time, \
    read_plugin_state, import_plugin_by_states, delete_router_by_tagname, cache_plugin_state, \
    cache_plugin_menu, register_plugin, unregister_plugin

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
templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none
templates.env.filters["datetime_format"] = datetime_format

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
from lib.editor.ckeditor4 import router as editor_router

# git clone으로 소스를 받은 경우에는 data디렉토리가 없으므로 생성해야 함
if not os.path.exists("data"):
    os.mkdir("data")
register_theme_statics(app)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

# 플러그인 라우터 우선 등록
plugin_states = read_plugin_state()
import_plugin_by_states(plugin_states)
register_plugin(plugin_states)
register_statics(app, plugin_states)

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
app.include_router(editor_router, prefix="/editor", tags=["editor"])


# 이 클래스는 BaseHTTPMiddleware를 상속받아, 
# HTTP 요청을 HTTPS로 리디렉션하는 미들웨어로 사용됩니다.
class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("X-Forwarded-Proto") != "https":
            request.scope["scheme"] = "https"
        return await call_next(request)

# 애플리케이션 인스턴스에 이 미들웨어를 추가합니다.
# 이로써 모든 들어오는 요청은 HTTPSRedirectMiddleware를 거치게 됩니다.
app.add_middleware(HTTPSRedirectMiddleware)


@app.middleware("http")
async def main_middleware(request: Request, call_next):
    """요청마다 항상 실행되는 미들웨어"""
    # 미들웨어가 여러번 실행되는 것을 막는 코드
    path = request.url.path
    # 토큰을 생성하는 요청의 경우에도 미들웨어를 건너뛰어야 합니다.
    # 경로가 정적 파일에 대한 것이 아닌지 확인합니다 (css, js, 이미지 등).
    if (path.startswith('/generate_token')
            or path.startswith('/static')
            or path.endswith(('.css', '.js', '.jpg', '.png', '.gif', '.webp'))):
        response = await call_next(request)
        return response

    # 데이터베이스 설치여부 체크
    db_connect = DBConnect()
    try:
        if not path.startswith("/install"):
            if not os.path.exists(ENV_PATH):
                raise AlertException(".env 파일이 없습니다. 설치를 진행해 주세요.", 400, "/install")

            if not inspect(db_connect.engine).has_table(db_connect.table_prefix + "config"):
                raise AlertException("DB 또는 테이블이 존재하지 않습니다. 설치를 진행해 주세요.", 400, "/install")
        else:
            return await call_next(request)

    except AlertException as e:
        return await alert_exception_handler(request, e)

    # 기본환경설정 조회
    db = db_connect.sessionLocal()
    config = db.scalar(select(Config))
    request.state.config = config

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

    member = None
    is_autologin = False
    ss_mb_key = None
    session_mb_id = request.session.get("ss_mb_id", "")
    cookie_mb_id = request.cookies.get("ck_mb_id", "")

    # 로그인 세션
    if session_mb_id:
        member = MemberService.create_by_id(db, session_mb_id)
        # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
        if member.is_intercept_or_leave():
            request.session.clear()
            member = None
    # 자동로그인
    elif cookie_mb_id:
        mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20]
        member = MemberService.create_by_id(db, mb_id)
        # 최고관리자는 보안상 자동로그인 기능을 사용하지 않는다.
        if (not is_admin(request, mb_id)
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
    request.state.is_super_admin = is_admin(request, getattr(member, "mb_id", None))

    db.close()

    # 접근가능/차단 IP 체크
    current_ip = request.client.host
    if not is_possible_ip(request, current_ip):
        return HTMLResponse("<meta charset=utf-8>접근이 허용되지 않은 IP 입니다.")
    if is_intercept_ip(request, current_ip):
        return HTMLResponse("<meta charset=utf-8>접근이 차단된 IP 입니다.")

    if request.method == "GET":
        # 쿼리 파라미터에서 값을 가져와서 request의 상태에 저장합니다. 값이 없으면 빈 문자열을 저장합니다.
        request.state.sst = request.query_params.get("sst") if request.query_params.get("sst") else ""
        request.state.sod = request.query_params.get("sod") if request.query_params.get("sod") else ""
        request.state.sfl = request.query_params.get("sfl") if request.query_params.get("sfl") else ""
        request.state.stx = request.query_params.get("stx") if request.query_params.get("stx") else ""
        request.state.sca = request.query_params.get("sca") if request.query_params.get("sca") else ""
        request.state.page = request.query_params.get("page") if request.query_params.get("page") else ""
    else:
        # 폼 데이터에서 값을 가져와서 request의 상태에 저장합니다. 값이 없으면 빈 문자열을 저장합니다.
        request.state.sst = request._form.get("sst") if request._form and request._form.get("sst") else ""
        request.state.sod = request._form.get("sod") if request._form and request._form.get("sod") else ""
        request.state.sfl = request._form.get("sfl") if request._form and request._form.get("sfl") else ""
        request.state.stx = request._form.get("stx") if request._form and request._form.get("stx") else ""
        request.state.sca = request._form.get("sca") if request._form and request._form.get("sca") else ""
        request.state.page = request._form.get("page") if request._form and request._form.get("page") else ""

    # pc, mobile 구분
    request.state.is_mobile = False
    request.state.device = ""  # pc 의 기본값은 "" 이고, mobile 은 "mobile" 로 설정

    user_agent = request.headers.get("User-Agent", "")
    ua = parse(user_agent)
    if ua.is_mobile or ua.is_tablet:  # 모바일과 태블릿에서 접속하면 모바일로 간주
        request.state.is_mobile = True

    if not IS_RESPONSIVE:  # 적응형
        # 반응형이 아니라면 모바일 접속은 mobile 로, 그 외 접속은 desktop 으로 간주
        if request.state.is_mobile:
            request.state.device = "mobile"

    # 에디터 전역변수
    request.state.editor = config.cf_editor
    request.state.use_editor = True if config.cf_editor else False

    response: Response = await call_next(request)

    # 자동로그인 쿠키 재설정
    # is_autologin과 세션을 확인해서 로그아웃 처리 이후 쿠키가 재설정되는 것을 방지
    if is_autologin and request.session.get("ss_mb_id"):
        response.set_cookie(key="ck_mb_id", value=cookie_mb_id, max_age=60 * 60 * 24 * 30)
        response.set_cookie(key="ck_auto", value=ss_mb_key, max_age=60 * 60 * 24 * 30)

    # 접속자 기록
    vi_ip = request.client.host
    ck_visit_ip = request.cookies.get('ck_visit_ip', None)
    if ck_visit_ip != vi_ip:
        # 접속을 추적하는 쿠키 설정 및 접속 레코드 기록
        response.set_cookie('ck_visit_ip', vi_ip, max_age=86400)  # 쿠키를 하루 동안 유지
        # 접속 레코드 기록
        record_visit(request)

    return response

# 아래 app.add_middleware(...) 코드는 반드시 common 함수의 아래에 위치해야 합니다.
# 그렇지 않으면 아래와 같은 오류를 만날 수 있습니다.
# AssertionError: SessionMiddleware must be installed to access request.session
app.add_middleware(SessionMiddleware,
                   secret_key=os.getenv("SESSION_SECRET_KEY", "secret"),
                   session_cookie=os.getenv("SESSION_COOKIE_NAME", "session"),
                   max_age=60 * 60 * 3)


@app.exception_handler(AlertException)
async def alert_exception_handler(request: Request, exc: AlertException):
    """AlertException 예외처리 등록

    Args:
        request (Request): request 객체
        exc (AlertException): 예외 객체

    Returns:
        _TemplateResponse: 경고창 템플릿
    """
    template = Jinja2Templates(directory=[TEMPLATES_DIR])
    return template.TemplateResponse(
        "alert.html", {"request": request, "errors": exc.detail, "url": exc.url}, status_code=exc.status_code
    )


@app.exception_handler(AlertCloseException)
async def alert_close_exception_handler(request: Request, exc: AlertCloseException):
    """AlertCloseException 예외처리 등록

    Args:
        request (Request): request 객체
        exc (AlertCloseException): 예외 객체

    Returns:
        _TemplateResponse: 경고창 & 윈도우창 닫기 템플릿
    """
    template = Jinja2Templates(directory=[TEMPLATES_DIR])
    return template.TemplateResponse(
        "alert_close.html", {"request": request, "errors": exc.detail}, status_code=exc.status_code
    )


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
    return templates.TemplateResponse(f"{request.state.device}/index.html", context)


@app.post("/generate_token")
async def generate_token(request: Request):

    token = create_session_token(request)

    return JSONResponse(content={"success": True, "token": token})
