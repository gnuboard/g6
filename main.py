import datetime
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter

from database import get_db
from starlette.middleware.sessions import SessionMiddleware
from common import *

from user_agents import parse
import models
import secrets

# models.Base.metadata.create_all(bind=engine)
APP_IS_DEBUG = TypeAdapter(bool).validate_python(os.getenv("APP_IS_DEBUG", False))
app = FastAPI(debug=APP_IS_DEBUG)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = MyTemplates(directory=[TEMPLATES_DIR], extensions=["jinja2.ext.i18n"])
templates.env.globals["is_admin"] = is_admin
templates.env.filters["default_if_none"] = default_if_none

from _admin.admin import router as admin_router
from _bbs.board import router as board_router
from _bbs.login import router as login_router
from _bbs.register import router as register_router
from _bbs.content import router as content_router
from _bbs.faq import router as faq_router
from _bbs.qa import router as qa_router
from _bbs.member_profile import router as user_profile_router
from _bbs.memo import router as memo_router
from _bbs.poll import router as poll_router
from _bbs.point import router as point_router
from _bbs.scrap import router as scrap_router
from _bbs.board_new import router as board_new_router
from _bbs.ajax_good import router as good_router
from _bbs.ajax_autosave import router as autosave_router
from _bbs.social import router as social_router
from _bbs.password import router as password_router
from _bbs.search import router as search_router
from _lib.editor.ckeditor4 import router as editor_router
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(board_router, prefix="/board", tags=["board"])
app.include_router(login_router, prefix="/bbs", tags=["login"])
app.include_router(register_router, prefix="/bbs", tags=["register"])
app.include_router(user_profile_router, prefix="/bbs", tags=["profile"])
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
# is_mobile = False
# user_device = 'pc'

# 항상 실행해야 하는 미들웨어
@app.middleware("http")
async def main_middleware(request: Request, call_next):

    ### 미들웨어가 여러번 실행되는 것을 막는 코드 시작    
    # 요청의 경로를 얻습니다.
    path = request.url.path
    # 경로가 정적 파일에 대한 것이 아닌지 확인합니다 (css, js, 이미지 등).
    if (path.startswith('/static') or path.endswith(('.css', '.js', '.jpg', '.png', '.gif', '.webp'))):
        response = await call_next(request)
        return response
    ### 미들웨어가 여러번 실행되는 것을 막는 코드 끝
    
    try:
        if path.startswith("/admin"):
            # 관리자 페이지는 로그인이 필요합니다.
            if not request.session.get("ss_mb_id"):
                raise AlertException(status_code=302, detail="로그인이 필요합니다.", url="/bbs/login?url="+path)
    except AlertException as e:
        # 예외처리 실행
        return await alert_exception_handler(request, e)

    member = None

    db: Session = SessionLocal()
    config = db.query(models.Config).first()
    request.state.config = config

    is_super_admin = False
    is_autologin = False
    ss_mb_id = request.session.get("ss_mb_id", "")
    # 로그인
    if ss_mb_id:
        member = db.query(models.Member).filter(models.Member.mb_id == ss_mb_id).first()
        if member:
            ymd_str = datetime.now().strftime("%Y-%m-%d")
            if member.mb_intercept_date or member.mb_leave_date: # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
                request.session["ss_mb_id"] = ""
                member = None
            elif member.mb_today_login.strftime("%Y-%m-%d") != datetime.now().strftime("%Y-%m-%d"):  # 오늘 처음 로그인 이라면
                # 첫 로그인 포인트 지급
                insert_point(request, member.mb_id, config.cf_login_point, ymd_str + " 첫로그인", "@login", member.mb_id, ymd_str)
                # 오늘의 로그인이 될 수도 있으며 마지막 로그인일 수도 있음
                # 해당 회원의 접근일시와 IP 를 저장
                member.mb_today_login = datetime.now()
                member.mb_login_ip = request.client.host
                db.commit()

            # 최고관리자인지 확인
            if member and config.cf_admin == member.mb_id:
                is_super_admin = True
    # 자동로그인
    else:
        cookie_mb_id = request.cookies.get("ck_mb_id", "")
        if cookie_mb_id:
            cookie_mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20] # 쿠키에 저장된 아이디에서 영문자,숫자,_ 20글자 얻는다.
        if cookie_mb_id and cookie_mb_id.lower() != config.cf_admin.lower(): # 최고관리자 아이디라면 자동로그인 금지
            member = db.query(models.Member).filter(models.Member.mb_id == cookie_mb_id).first()
            if member and not (member.mb_intercept_date or member.mb_leave_date): # 차단 했거나 탈퇴한 회원이 아니면
                # 메일인증을 사용하고 메일인증한 시간이 있다면, 년도만 체크하여 시간이 있음을 확인
                if config.cf_use_email_certify and not is_none_datetime(member.mb_email_certify):
                    ss_mb_key  = session_member_key(request, member)
                    # 쿠키에 저장된 키와 여러가지 정보를 조합하여 만든 키가 일치한다면 로그인으로 간주
                    if request.cookies.get("ck_auto") == ss_mb_key:
                        request.session["ss_mb_id"] = cookie_mb_id
                        is_autologin = True

    db.close()
    request.state.is_super_admin = is_super_admin

    if request.method == "GET":
        request.state.sst = request.query_params.get("sst") if request.query_params.get("sst") else ""
        request.state.sod = request.query_params.get("sod") if request.query_params.get("sod") else ""
        request.state.sfl = request.query_params.get("sfl") if request.query_params.get("sfl") else ""
        request.state.stx = request.query_params.get("stx") if request.query_params.get("stx") else ""
        request.state.sca = request.query_params.get("sca") if request.query_params.get("sca") else ""
        request.state.page = request.query_params.get("page") if request.query_params.get("page") else ""
    else:
        request.state.sst = request._form.get("sst") if request._form and request._form.get("sst") else ""
        request.state.sod = request._form.get("sod") if request._form and request._form.get("sod") else ""
        request.state.sfl = request._form.get("sfl") if request._form and request._form.get("sfl") else ""
        request.state.stx = request._form.get("stx") if request._form and request._form.get("stx") else ""
        request.state.sca = request._form.get("sca") if request._form and request._form.get("sca") else ""
        request.state.page = request._form.get("page") if request._form and request._form.get("page") else ""
        
    # pc, mobile 구분
    request.state.is_mobile = False
    request.state.device = "" # pc 의 기본값은 "" 이고, mobile 은 "mobile" 로 설정
    
    user_agent = request.headers.get("User-Agent", "")
    ua = parse(user_agent)
    if ua.is_mobile or ua.is_tablet: # 모바일과 태블릿에서 접속하면 모바일로 간주
        request.state.is_mobile = True

    if not IS_RESPONSIVE: # 적응형
        # 반영형이 아니라면 모바일 접속은 mobile 로, 그 외 접속은 pc 로 간주
        if request.state.is_mobile:
            request.state.device = "mobile"

    # if 'SET_DEVICE' in globals():
    #     if SET_DEVICE == 'mobile':
    #         request.state.is_mobile = True
    #         request.state.device = 'mobile'
    # else:
    #     user_agent = request.headers.get("User-Agent", "")
    #     ua = parse(user_agent)
    #     if 'USE_MOBILE' in globals() and USE_MOBILE:
    #         if ua.is_mobile or ua.is_tablet: # 모바일과 태블릿에서 접속하면 모바일로 간주
    #             request.state.is_mobile = True
    #             request.state.device = 'mobile'
                
    # 로그인한 회원 정보
    request.state.login_member = member

    # 에디터 전역변수
    request.state.editor = config.cf_editor
    request.state.use_editor = True if config.cf_editor else False
                
    # request.state.context = {
    #     # "request": request,
    #     # "config": config,
    #     # "member": member,
    #     # "outlogin": outlogin.body.decode("utf-8"),
    # }      
    db.close()
    response = await call_next(request)

    if is_autologin:
        # 자동로그인 쿠키를 설정
        response.set_cookie(key="ss_mb_id", value=request.session["ss_mb_id"], max_age=86400 * 30)  # 30 일 동안 유지

    # 접속자 기록
    vi_ip = request.client.host
    ck_visit_ip = request.cookies.get('ck_visit_ip', None)
    if ck_visit_ip != vi_ip:
        # 접속을 추적하는 쿠키 설정 및 접속 레코드 기록
        response.set_cookie('ck_visit_ip', vi_ip, max_age=86400)  # 쿠키를 하루 동안 유지
        # 접속 레코드 기록
        record_visit(request)
        
    # print("After request")

    return response

# 아래 app.add_middleware(...) 코드는 반드시 common 함수의 아래에 위치해야 함. 
# 안 그러면 아래와 같은 오류를 맛볼수 있음 ㅠㅠ
# AssertionError: SessionMiddleware must be installed to access request.session
app.add_middleware(SessionMiddleware, secret_key="secret", session_cookie="session", max_age=3600 * 3)


@app.exception_handler(AlertException)
async def alert_exception_handler(request: Request, exc: AlertException):
    """AlertException 예외처리 등록

    Args:
        request (Request): request 객체
        exc (AlertException): 예외 객체

    Returns:
        _TemplateResponse: 경고창 템플릿
    """
    return templates.TemplateResponse(
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
    return templates.TemplateResponse(
        "alert_close.html", {"request": request, "errors": exc.detail}, status_code=exc.status_code
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """
    메인 페이지
    """
    query_boards = db.query(models.Board).join(
        models.Group, models.Board.gr_id == models.Group.gr_id
    ).filter(models.Board.bo_device != 'mobile')
    # 최고관리자는 모든 게시판을 볼 수 있음
    if not request.state.is_super_admin:
        query_boards = query_boards.filter(
            models.Board.bo_use_cert == '',
            models.Board.bo_table.notin_(['notice', 'gallery'])
        )
    boards = query_boards.order_by(
        models.Group.gr_order,
        models.Board.bo_order
    ).all()

    context = {
        "request": request,
        "newwins": get_newwins(request),
        "boards": boards,
    }
    return templates.TemplateResponse(f"{request.state.device}/main.html", context)


@app.post("/generate_token")
async def generate_token(request: Request):
    token = secrets.token_hex(16)  # 16바이트 토큰 생성
    request.session["ss_token"] = token  # 세션에 토큰 저장

    return JSONResponse(content={"success": True, "token": token})

