from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from common import *
from database import get_db
from dataclassform import NewwinForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from models import NewWin

router = APIRouter()
templates = MyTemplates(directory=[ADMIN_TEMPLATES_DIR, EDITOR_PATH])
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals["today"] = datetime.now().strftime("%Y-%m-%d 00:00:00")
templates.env.globals["after_7days"] = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d 23:59:59")
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names

MENU_KEY = "100310"


@router.get("/newwin_list")
def newwin_list(request: Request, db: Session = Depends(get_db)):
    """
    팝업 목록
    """
    request.session["menu_key"] = MENU_KEY

    newwins = db.query(NewWin).order_by(NewWin.nw_id.desc()).all()

    context = {
        "request": request,
        "newwins": newwins,
    }
    return templates.TemplateResponse("newwin_list.html", context)


@router.get("/newwin_form")
def newwin_form_add(request: Request):
    """
    팝업 등록 폼
    """
    return templates.TemplateResponse(
        "newwin_form.html", {"request": request, "newwin": None}
    )


@router.get("/newwin_form/{nw_id}")
def newwin_form_edit(request: Request, nw_id: int, db: Session = Depends(get_db)):
    """
    팝업 수정 폼
    """
    newwin = db.query(NewWin).get(nw_id)

    return templates.TemplateResponse(
        "newwin_form.html", {"request": request, "newwin": newwin}
    )

@router.post("/newwin_form_update")
def newwin_form_update(request: Request,
                        db: Session = Depends(get_db),
                        token: str = Form(...),
                        nw_id: int = Form(None),
                        form_data: NewwinForm = Depends()
                        ):
    """
    팝업 등록 및 수정 처리
    """
    if compare_token(request, token, 'insert'): # 토큰에 등록돤 action이 insert라면 신규 등록
        newwin = NewWin(**form_data.__dict__)
        db.add(newwin)
        db.commit()
        
    elif compare_token(request, token, 'update'):  # 토큰에 등록된 action이 update라면 수정
        newwin = db.query(NewWin).get(nw_id)
        if not newwin:
            raise AlertException(status_code=404, detail=f"{nw_id} : 팝업이 존재하지 않습니다.")

        # 데이터 수정 후 commit
        for field, value in form_data.__dict__.items():
            setattr(newwin, field, value)
        db.commit()
    
    else: # 토큰 검사 실패
        raise AlertException(status_code=403, detail=f"{token} : 토큰이 존재하지 않습니다.")

    return RedirectResponse(url=f"/admin/newwin_form/{newwin.nw_id}", status_code=302)


@router.get("/newwin_delete/{nw_id}")
def newwin_delete(nw_id: int, 
                   request: Request, 
                   db: Session = Depends(get_db),
                   token: str = Query(...)):
    """
    팝업 삭제
    """
    if not compare_token(request, token, 'delete'):
        raise AlertException(status_code=403, detail=f"{token} : 토큰이 존재하지 않습니다.")
    
    newwin = db.query(NewWin).get(nw_id)
    if not newwin:
        raise AlertException(status_code=404, detail=f"{nw_id}: 팝업이 존재하지 않습니다.")

    # 팝업 삭제
    db.delete(newwin)
    db.commit()

    return RedirectResponse(url=f"/admin/newwin_list", status_code=302)