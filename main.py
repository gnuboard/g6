import datetime 
from datetime import timedelta
import re

from debug_toolbar.middleware import DebugToolbarMiddleware
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from database import get_db

from jinja2 import Environment, FileSystemLoader
from database import engine, get_db, SessionLocal
import models
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from common import *
from typing import Optional

from settings import G6_IS_DEBUG
from user_agents import parse

models.Base.metadata.create_all(bind=engine)

app = FastAPI(debug=G6_IS_DEBUG)
if G6_IS_DEBUG:
    app.add_middleware(DebugToolbarMiddleware)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# # 1. main.py의 위치를 얻습니다.
# current_path = os.path.dirname(os.path.abspath(__file__))
# # 2. 해당 위치를 기준으로 Jinja2의 FileSystemLoader를 설정합니다.
# env = Environment(loader=FileSystemLoader(current_path))

from _admin.admin import router as admin_router
from _bbs.board import router as board_router
from _bbs.login import router as login_router
from _bbs.register import router as register_router
from _bbs.content import router as content_router
import _user.user_router 

app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(board_router, prefix="/board", tags=["board"])
app.include_router(login_router, prefix="/bbs", tags=["login"])
app.include_router(register_router, prefix="/bbs", tags=["register"])
app.include_router(content_router, prefix="/content", tags=["content"])

# is_mobile = False
# user_device = 'pc'

# 항상 실행해야 하는 미들웨어
@app.middleware("http")
async def common(request: Request, call_next):
    # global is_mobile, user_device
    
    member = None
    outlogin = None

    db: Session = SessionLocal()
    config = db.query(models.Config).first()
    
    ss_mb_id = request.session.get("ss_mb_id", "")
    
    if ss_mb_id:
        member = db.query(models.Member).filter(models.Member.mb_id == ss_mb_id).first()
        if member:
            if member.mb_intercept_date or member.mb_leave_date:  # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
                request.session["ss_mb_id"] = ""
                member = None
            else:
                if member.mb_today_login.strftime(format="%Y-%m-%d") != TIME_YMD:  # 오늘 처음 로그인 이라면
                    # 첫 로그인 포인트 지급
                    # insert_point(member.mb_id, config["cf_login_point"], current_date + " 첫로그인", "@login", member.mb_id, current_date)
                    # 오늘의 로그인이 될 수도 있으며 마지막 로그인일 수도 있음
                    # 해당 회원의 접근일시와 IP 를 저장
                    member.mb_today_login = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    member.mb_login_ip = request.client.host
                    db.commit()
            
                outlogin = templates.TemplateResponse("bbs/outlogin_after.html", {"request": request, "member": member})            
            
    else:
        cookie_mb_id = request.cookies.get("ck_mb_id")
        if cookie_mb_id:
            cookie_mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20] # 쿠키에 저장된 아이디에서 영문자,숫자,_ 20글자 얻는다.
        if cookie_mb_id and cookie_mb_id.lower() != config.cf_admin.lower(): # 최고관리자 아이디라면 자동로그인 금지
            member = db.query(models.Member).filter(models.Member.mb_id == cookie_mb_id).first()
            if member and not (member.mb_intercept_date or member.mb_leave_date): # 차단 했거나 탈퇴한 회원이 아니면
                # 메일인증을 사용하고 메일인증한 시간이 있다면, 년도만 체크하여 시간이 있음을 확인
                if config.cf_use_email_certify and member.mb_email_certify[:2] != "00":
                    ss_mb_key  = session_member_key(request, member)
                    # 쿠키에 저장된 키와 여러가지 정보를 조합하여 만든 키가 일치한다면 로그인으로 간주
                    if request.cookies.get("ck_auto") == ss_mb_key:
                        request.session["ss_mb_id"] = cookie_mb_id
                        return RedirectResponse(url="/", status_code=302)

    if not outlogin:
        outlogin = templates.TemplateResponse("bbs/outlogin_before.html", {"request": request})
    
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
    # if 'SET_DEVICE' in globals():
    #     if SET_DEVICE == 'mobile':
    #         is_mobile = True
    #         user_device = 'mobile'
    # else:
    #     user_agent = request.headers.get("User-Agent", "")
    #     ua = parse(user_agent)
    #     if 'USE_MOBILE' in globals() and USE_MOBILE:
    #         if ua.is_mobile or ua.is_tablet:
    #             is_mobile = True
    #             user_device = 'mobile'
    
    # pc, mobile 구분
    request.state.is_mobile = False
    request.state.device = 'pc'
    
    if 'SET_DEVICE' in globals():
        if SET_DEVICE == 'mobile':
            request.state.is_mobile = True
            request.state.device = 'mobile'
    else:
        user_agent = request.headers.get("User-Agent", "")
        ua = parse(user_agent)
        if 'USE_MOBILE' in globals() and USE_MOBILE:
            if ua.is_mobile or ua.is_tablet: # 모바일과 태블릿에서 접속하면 모바일로 간주
                request.state.is_mobile = True
                request.state.device = 'mobile'
        
    request.state.context = {
        "request": request,
        "config": config,
        "member": member,
        "outlogin": outlogin.body.decode("utf-8"),
    }        
                        
    response = await call_next(request)
    # print("After request")
    return response

# 아래 app.add_middleware(...) 코드는 반드시 common 함수의 아래에 위치해야 함. 
# 안 그러면 아래와 같은 오류를 맛볼수 있음 ㅠㅠ
# AssertionError: SessionMiddleware must be installed to access request.session
app.add_middleware(SessionMiddleware, secret_key="secret", session_cookie="session", max_age=3600 * 3)


def get_member(mb_id, db: Session = Depends(get_db)):
    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    return member

@app.get("/root")
def read_root():
    return {"Hello": "World"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, response: Response, db: Session = Depends(get_db)):
    
    context = {
        "request": request,
        "outlogin": request.state.context["outlogin"],
        "latest": latest,
    }
    # return templates.TemplateResponse(f"index.{user_device}.html", 
    return templates.TemplateResponse(f"index.{request.state.device}.html", context)

def latest(skin_dir='', bo_table='', rows=10, subject_len=40, request: Request = None):

    if not skin_dir:
        skin_dir = 'basic'
    
    db = SessionLocal()
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    
    models.Write = dynamic_create_write_table(bo_table)
    writes = db.query(models.Write).filter(models.Write.wr_is_comment == False).order_by(models.Write.wr_num).limit(rows).all()
    for write in writes:
        write.is_notice = write.wr_id in board.bo_notice.split(",")
        write.subject = write.wr_subject[:subject_len]
        write.icon_hot = write.wr_hit >= 100
        write.icon_new = write.wr_datetime > (datetime.now() - timedelta(days=1))
        write.icon_file = write.wr_file
        write.icon_link = write.wr_link1 or write.wr_link2
        write.icon_reply = write.wr_reply
    
    context = {
        "request": request,
        "writes": writes,
        "bo_table": bo_table,
        "bo_subject": board.bo_subject,
    }
        
    template = templates.TemplateResponse(f"latest/{skin_dir}.html", context)
    return template.body.decode("utf-8")
