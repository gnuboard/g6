import datetime
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
templates = Jinja2Templates(directory="templates")

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


from admin import router as admin_router
from board import router as board_router
from login import router as login_router
from register import router as register_router
import user_router 

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
        # member = get_member(ss_mb_id)
        if member:
            # 차단 되었거나, 탈퇴한 회원이면 세션 초기화
            if member.mb_intercept_date or member.mb_leave_date:
                # 세션에 저장한다
                request.session["ss_mb_id"] = ""
                member = None
        
            # 오늘 처음 로그인 이라면
            if member.mb_today_login[:10] != datetime.datetime.now().strftime("%Y%m%d"):
                # 첫 로그인 포인트 지급
                # insert_point(member.mb_id, config["cf_login_point"], current_date + " 첫로그인", "@login", member.mb_id, current_date)
                # 오늘의 로그인이 될 수도 있으며 마지막 로그인일 수도 있음
                # 해당 회원의 접근일시와 IP 를 저장
                member.mb_today_login = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                member.mb_login_ip = request.client.host
                db.commit()
            
            outlogin = templates.TemplateResponse("bbs/outlogin_after.html", {"request": request, "member": member})            
            
    else:
        # 쿠키에 저장된 아이디에서 영문자,숫자,_ 20글자 얻는다.
        cookie_mb_id = request.cookies.get("ck_mb_id")
        if cookie_mb_id:
            cookie_mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20]
        # 최고관리자 아이디라면 자동로그인 금지
        if cookie_mb_id and cookie_mb_id.lower() != config.cf_admin.lower():
            member = db.query(models.Member).filter(models.Member.mb_id == cookie_mb_id).first()
            # 차단 했거나 탈퇴한 회원이 아니면
            if member and not (member.mb_intercept_date or member.mb_leave_date):
                # 메일인증을 사용하고 메일인증한 시간이 있다면, 년도만 체크하여 시간이 있음을 확인
                if config.cf_use_email_certify and member.mb_email_certify[:2] != "00":
                    ss_mb_key  = session_member_key(request, member)
                    # 쿠키에 저장된 키와 여러가지 정보를 조합하여 만든 키가 일치한다면 로그인으로 간주
                    if request.cookies.get("ck_auto") == ss_mb_key:
                        request.session["ss_mb_id"] = cookie_mb_id
                        return RedirectResponse(url="/", status_code=302)

    if not outlogin:
        outlogin = templates.TemplateResponse("bbs/outlogin_before.html", {"request": request})
        
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
    # 캐시 제어 헤더 설정 (캐시된 페이지를 보여주지 않고 새로운 페이지를 보여줌)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # items = db.query(models.Item).all()
    return templates.TemplateResponse("index.html", {"request": request, "outlogin": request.state.context["outlogin"]})
