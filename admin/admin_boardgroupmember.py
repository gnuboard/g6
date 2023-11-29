import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session, aliased
from common.database import get_db, engine
import common.models as models 
from lib.common import *
from typing import List, Optional
from common.formclass import BoardForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = AdminTemplates(directory=[ADMIN_TEMPLATES_DIR, EDITOR_PATH])
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["editor_path"] = editor_path


            # <?php
            # $sql = " select *
            #             from {$g5['group_table']}
            #             where gr_use_access = 1 ";
            # if ($is_admin != 'super') {
            #     $sql .= " and gr_admin = '{$member['mb_id']}' ";
            # }
            # $sql .= " order by gr_id ";
            # $result = sql_query($sql);
            # for ($i = 0; $row = sql_fetch_array($result); $i++) {
            #     echo "<option value=\"" . $row['gr_id'] . "\">" . $row['gr_subject'] . "</option>";
            # }
            # ?>

def get_group_select(request: Request, mb_id: str):
    db = SessionLocal()
    if request.state.is_super_admin:
    # groups = db.query(models.Group).filter_by(gr_use_access = 1, gr_admin = mb_id if mb_id != 'super' else None).order_by(models.Group.gr_id).all()
    # if is_admin == 'super':
        groups = db.query(models.Group).filter(models.Group.gr_use_access == 1).order_by(models.Group.gr_id).all()
    else:
        groups = db.query(models.Group).filter(models.Group.gr_use_access == 1, models.Group.gr_admin == mb_id).order_by(models.Group.gr_id).all()
    return groups


# 등록 폼
@router.get("/boardgroupmember_form/{mb_id}")
def board_form(mb_id: str, request: Request, db: Session = Depends(get_db)):
    
    config = request.state.config
    exists_member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not exists_member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} 회원이 존재하지 않습니다."]})

    gm = aliased(models.GroupMember)
    gr = aliased(models.Group)
    if request.state.is_super_admin:
        group_members = db.query(gm, gr).join(gr, gm.gr_id == gr.gr_id).filter(gm.mb_id == mb_id).order_by(desc(gm.gr_id)).all()
    else:
        group_members = db.query(gm, gr).join(gr, gm.gr_id == gr.gr_id).filter(gm.mb_id == mb_id, gr.gr_admin == mb_id).order_by(desc(gm.gr_id)).all()
        
    context = {
        "request": request,
        "config": config,
        "member": exists_member,
        "groups": get_group_select(request, mb_id),
        "group_members": group_members,
    }
    return templates.TemplateResponse("boardgroupmember_form.html", context)


@router.post("/boardgroupmember_insert")
async def boardgroupmember_insert(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    mb_id: str = Form(...),
    gr_id: str = Form(...),
    ):
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)
    
    exists_member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not exists_member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} 회원이 존재하지 않습니다."]})
    
    exists_group = db.query(models.Group).filter(models.Group.gr_id == gr_id).first()
    if not exists_group:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{gr_id} 그룹이 존재하지 않습니다."]})
    
    exists_group_member = db.query(models.GroupMember).filter(models.GroupMember.gr_id == gr_id, models.GroupMember.mb_id == mb_id).first()
    if exists_group_member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} 회원은 이미 {gr_id} 그룹에 등록되어 있습니다."]})
    
    group_member = models.GroupMember(
        gr_id = gr_id,
        mb_id = mb_id,
        gm_datetime = datetime.now(),
    )
    db.add(group_member)
    db.commit()
    
    return RedirectResponse(f"/admin/boardgroupmember_form/{mb_id}", status_code=303)


@router.post("/boardgroupmember_delete")
async def boardgroupmember_delete(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    checks: List[int] = Form(None, alias="chk[]"),
    mb_id: str = Form(...),
    ):
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    for i in checks:
        gm_id = i
        exists_groupmember = db.query(models.GroupMember).filter(models.GroupMember.gm_id == gm_id).first()
        if exists_groupmember:
            db.delete(exists_groupmember)
            db.commit()

    return RedirectResponse(f"/admin/boardgroupmember_form/{mb_id}?{query_string(request)}", status_code=303)

