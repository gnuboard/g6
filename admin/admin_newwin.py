from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.exception import AlertException
from core.formclass import NewwinForm
from core.models import NewWin
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_token

router = APIRouter()
templates = AdminTemplates()
templates.env.globals["start_day"] = datetime.now().strftime("%Y-%m-%d 00:00:00")
templates.env.globals["after_7days"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d 23:59:59")

NEWWIN_MENU_KEY = "100310"


def get_newwin(db: db_session, nw_id: int):
    """
    팝업 정보조회 의존성 주입 함수
    """
    newwin = db.get(NewWin, nw_id)
    if not newwin:
        raise AlertException(f"{nw_id} : 팝업이 존재하지 않습니다.", 404)

    return newwin


@router.get("/newwin_list")
async def newwin_list(request: Request, db: db_session):
    """
    팝업 목록
    """
    request.session["menu_key"] = NEWWIN_MENU_KEY

    newwins = db.scalars(
        select(NewWin).order_by(NewWin.nw_id.desc())
    ).all()

    context = {
        "request": request,
        "newwins": newwins,
    }
    return templates.TemplateResponse("newwin_list.html", context)


@router.get("/newwin_form")
async def newwin_form_add(request: Request):
    """
    팝업 등록 폼
    """
    context = {"request": request, "newwin": None}
    return templates.TemplateResponse("newwin_form.html", context)


@router.get("/newwin_form/{nw_id}")
async def newwin_form_edit(
    request: Request,
    newwin: NewWin = Depends(get_newwin)
):
    """
    팝업 수정 폼
    """
    context = {"request": request, "newwin": newwin}
    return templates.TemplateResponse("newwin_form.html", context)


@router.post("/newwin_form_update", dependencies=[Depends(validate_token)])
async def newwin_form_update(
    request: Request,
    db: db_session,
    nw_id: int = Form(None),
    form_data: NewwinForm = Depends()
):
    """
    팝업 등록 및 수정 처리
    """
    # 등록
    if not nw_id:
        newwin = NewWin(**form_data.__dict__)
        db.add(newwin)
        db.commit()
    # 수정
    else:
        newwin = get_newwin(db, nw_id)
        for field, value in form_data.__dict__.items():
            setattr(newwin, field, value)
        db.commit()

    return RedirectResponse(url=f"/admin/newwin_form/{newwin.nw_id}", status_code=302)


@router.get("/newwin_delete/{nw_id}", dependencies=[Depends(validate_token)])
async def newwin_delete(
    request: Request,
    db: db_session,
    newwin: NewWin = Depends(get_newwin)
):
    """
    팝업 삭제
    """
    # 팝업 삭제
    db.delete(newwin)
    db.commit()

    return RedirectResponse(url=f"/admin/newwin_list", status_code=302)
