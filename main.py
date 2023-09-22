import datetime 
from datetime import timedelta
import re
from fastapi import FastAPI, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from database import engine, get_db, SessionLocal
import models
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from common import *

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# from starlette.middleware.base import BaseHTTPMiddleware
# class CustomMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request, call_next):
#         db: Session = SessionLocal()
#         # 여기서는 모든 요청을 가로챕니다.
#         # 실제 사용시에는 특정 조건에 따라 응답을 반환하거나 call_next를 호출하면 됩니다.
#         # print("====================================Before request")
#         # return Response("Intercepted by Middleware", media_type="text/plain")
#         ss_mb_id = request.session.get("ss_mb_id", "")
#         if ss_mb_id:
#             member = db.query(models.Member).filter(models.Member.mb_id == ss_mb_id).first()
#             if member:
#                 outlogin = templates.TemplateResponse("login/outlogin_after_login.html", {"request": request, "member": member})
#         else:
#             outlogin = templates.TemplateResponse("login/outlogin_before_login.html", {"request": request})
        
# app.add_middleware(CustomMiddleware)    


from _admin.admin import router as admin_router
from _board.board import router as board_router
from _login.login import router as login_router
from _register.register import router as register_router
import _user.user_router 

app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(board_router, prefix="/board", tags=["board"])
app.include_router(login_router, prefix="/bbs", tags=["login"])
app.include_router(register_router, prefix="/bbs", tags=["register"])

# 항상 실행해야 하는 미들웨어
@app.middleware("http")
async def common(request: Request, call_next):
    member = None
    outlogin = None

    db: Session = SessionLocal()
    config = db.query(models.Config).first()
    
    ss_mb_id = request.session.get("ss_mb_id", "")
    
    if ss_mb_id:
        member = db.query(models.Member).filter(models.Member.mb_id == ss_mb_id).first()
        if member:
            if member.mb_intercept_date or member.mb_leave_date: # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
                request.session["ss_mb_id"] = ""
                member = None
            else:
                # if member.mb_today_login[:10] != datetime.datetime.now().strftime("%Y%m%d"): # 오늘 처음 로그인 이라면
                # formatted_date = member.mb_today_login.strftime("%Y-%m-%d")
                # if formatted_date != TIME_YMD: # 오늘 처음 로그인 이라면
                if member.mb_today_login[:10] != TIME_YMD: # 오늘 처음 로그인 이라면
                    # 첫 로그인 포인트 지급
                    # insert_point(member.mb_id, config["cf_login_point"], current_date + " 첫로그인", "@login", member.mb_id, current_date)
                    # 오늘의 로그인이 될 수도 있으며 마지막 로그인일 수도 있음
                    # 해당 회원의 접근일시와 IP 를 저장
                    member.mb_today_login = TIME_YMDHIS
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
        
    request.state.sst = request.query_params.get("sst")
    request.state.sod = request.query_params.get("sod")
    request.state.sfl = request.query_params.get("sfl")
    request.state.stx = request.query_params.get("stx")
    request.state.page = request.query_params.get("page")
    # request.state.w = request.query_params.get("w")
        
    request.state.context = {
        "request": request,
        # "sst": request.state.sst,
        # "sod": request.state.sod,
        # "sfl": request.state.sfl,
        # "stx": request.state.stx,
        # "page": request.state.page,
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
    
    # latests = {}
    # boards = db.query(models.Board).all()
    # for board in boards:
    #     models.Write = dynamic_create_write_table(board.bo_table)
    #     writes = db.query(models.Write).order_by(models.Write.wr_num).limit(5).all()
    #     # for write in writes:
    #     #     print(write.__dict__)
    #     writes.bo_table = board.bo_table
    #     writes.bo_subject = board.bo_subject
    #     latests[board.bo_table] = writes
        
    #     latests = templates.TemplateResponse("latest/basic.html", {"request": request, "latests": latests})
        
    # request.state.context["latests"] = latests
    
    # # return templates.TemplateResponse("index.html", {"request": request, "outlogin": request.state.context["outlogin"]})
    # return templates.TemplateResponse("index.html", request.state.context)
    
    return templates.TemplateResponse("index.html", 
        {
            "request": request,
            "outlogin": request.state.context["outlogin"],
            "latest": latest,        
        })

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
        write.icon_new = write.wr_datetime > (datetime.datetime.now() - timedelta(days=1))
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
