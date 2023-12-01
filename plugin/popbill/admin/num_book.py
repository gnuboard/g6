from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi.params import Depends, Query, Form
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from common.database import get_db
from common.models import Member
from lib.common import AlertException, ADMIN_TEMPLATES_DIR, get_member_id_select, get_skin_select, get_editor_select, \
    get_selected, get_member_level_select, option_array_checked, get_admin_menus, generate_token, get_client_ip, \
    auth_check_menu
from lib.plugin.service import get_all_plugin_module_names, get_admin_plugin_menus
from plugin.popbill import PLUGIN_TEMPLATES_DIR
from plugin.popbill.admin.send import get_hp
from plugin.popbill.models import SmsBook, SmsBookGroup

admin_router = APIRouter(prefix="/sms_admin")
templates = Jinja2Templates(directory=[ADMIN_TEMPLATES_DIR, PLUGIN_TEMPLATES_DIR])
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["getattr"] = getattr
templates.env.globals["get_member_id_select"] = get_member_id_select
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_editor_select"] = get_editor_select
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["option_array_checked"] = option_array_checked
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["generate_token"] = generate_token
templates.env.globals["get_client_ip"] = get_client_ip


@admin_router.get("/num_book/write")
def show_num_book_write_form(request: Request,
                             bk_no: Optional[str] = Query(default=""),
                             bg_no: Optional[str] = Query(default=None),
                             ap: Optional[str] = Query(default=None),
                             db: Session = Depends(get_db)):
    """
    번호보관함 저장
    """
    title = "휴대폰 번호"
    exist_hplist = []
    exist_msg = ""

    if bk_no:  # 수정
        sms_book_data = db.query(SmsBook).filter(SmsBook.bk_no == bk_no).first()
        if not sms_book_data:
            raise AlertException("데이터가 없습니다.", 400)

        if sms_book_data.mb_id:
            member_result = db.query(Member.mb_id).filter(Member.mb_id == sms_book_data.mb_id).first()
            if not member_result:
                raise AlertException("데이터가 없습니다.", 400)

            sms_book_data.mb_id = member_result.mb_id
            member_data = db.query(Member.mb_id).filter(
                Member.mb_hp == sms_book_data.bk_hp,
                Member.mb_id != sms_book_data.mb_id,
                Member.mb_hp != "").all()

            for member in member_data:
                exist_hplist.append(member.mb_id)

            exist_msg_1 = '(수정시 회원정보에 반영되지 않습니다.)'
            exist_msg_2 = '(수정시 회원정보에 반영됩니다.)'
            exist_msg = exist_msg_1 if len(exist_hplist) > 0 else exist_msg_2

            title += " 수정"

    else:
        sms_book_data = SmsBook()
        sms_book_data.bg_no = bg_no
        sms_book_data.mb_id = ""
        sms_book_data.bk_name = ""
        sms_book_data.bk_hp = ""
        sms_book_data.mb_no = 0
        sms_book_data.bk_receipt = 1
        sms_book_data.bk_datetime = datetime.now()
        sms_book_data.bk_memo = ""

        title += " 추가"

    none_group = db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == 1).first()
    if not none_group:
        none_group = SmsBookGroup()
        none_group.bg_no = 1
        none_group.bg_name = ""
        none_group.bg_count = 0
        none_group.bg_datetime = datetime.now()

    groups = db.query(SmsBookGroup).order_by(SmsBookGroup.bg_name).filter(SmsBookGroup.bg_no > 1).all()

    context = {
        "request": request,
        "ap": ap,
        "title": title,
        "bk_no": bk_no,
        "bg_no": bg_no,
        "groups": groups,
        "none_group": none_group,
        "exist_hplist": exist_hplist,
        "exist_msg": exist_msg,
        "sms_book_data": sms_book_data,
    }

    return templates.TemplateResponse("admin/num_book_write_form.html", context)


@admin_router.post("/num_book/save")
def num_book_save(request: Request,
                  bg_no: Optional[str] = Form(default=None),
                  bk_no: Optional[str] = Form(default="") or Query(default=""),
                  bk_hp: Optional[str] = Form(default=""),
                  bk_name: Optional[str] = Form(default=""),
                  bk_memo: Optional[str] = Form(default=""),
                  bk_receipt: Optional[int] = Form(default=""),
                  db: Session = Depends(get_db)):
    """연락처 저장
    num_book_update.php
    """

    MEMBER_MENU_KEY = "900800"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException("권한이 없습니다.", 403)

    # is_hp_exist = False=
    if bg_no.isnumeric():
        bg_no = int(bg_no)
    else:
        bg_no = None

    if bk_no.isnumeric():
        bk_no = int(bk_no)
    else:
        bk_no = None
    is_update = True if bk_no else False
    bk_hp = bk_hp.strip()
    bk_name = bk_name.strip()
    bk_memo = bk_memo.strip()

    if not request.state.page:
        request.state.page = 1

    # 입력값 검사 끝 

    # 등록
    if not is_update:

        if not bg_no:  # 그룹이 없을 경우 미분류 그룹은 1번
            bg_no = 1

        if not bk_receipt:
            bk_receipt = 0
        else:
            bk_receipt = 1

        if not len(bk_name):
            raise AlertException("이름을 입력해주세요.", 400)

        if not len(bk_hp):
            raise AlertException("휴대폰 번호를 입력해주세요.", 400)

        result = db.query(SmsBook).filter(SmsBook.bk_hp == bk_hp).first()
        if result:
            raise AlertException("이미 등록된 번호입니다.", 400)

        if bk_receipt == 1:
            filter = {SmsBookGroup.bg_receipt: SmsBookGroup.bg_receipt + 1}
        else:
            filter = {SmsBookGroup.bg_reject: SmsBookGroup.bg_reject + 1}

        new_book_entry = SmsBook(bg_no=bg_no, bk_name=bk_name, bk_hp=bk_hp, bk_receipt=bk_receipt, bk_memo=bk_memo,
                                 bk_datetime=datetime.now())
        db.add(new_book_entry)

        db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == bg_no).update({
            SmsBookGroup.bg_count: SmsBookGroup.bg_count + 1,
            SmsBookGroup.bg_nomember: SmsBookGroup.bg_nomember + 1,
            **filter  # dict
        })

        db.commit()

        return RedirectResponse(url=f"/admin/sms_admin/num_book?page={request.state.page}", status_code=302)

    # 수정시
    if is_update:
        if not bg_no:
            bg_no = 0

        if not bk_receipt:
            bk_receipt = 0
        else:
            bk_receipt = 1
        if not len(bk_name):
            raise AlertException("이름을 입력해주세요.", 400)

        if not len(bk_hp):
            raise AlertException("휴대폰 번호를 입력해주세요.", 400)

        result = db.query(SmsBook).filter(SmsBook.bk_no == bk_no).first()
        if not result:
            raise AlertException("데이터가 없습니다.", 400)

        if bg_no != result.bg_no:
            member_colunm_name = "bg_member" if result.mb_id else "bg_nomember"
            sms = "bg_receipt" if result.bk_receipt == 1 else "bg_reject"

            # bg_no = result.bg_no
            db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == result.bg_no).update({
                SmsBookGroup.bg_count: SmsBookGroup.bg_count - 1,
                getattr(SmsBookGroup, member_colunm_name): getattr(SmsBookGroup, member_colunm_name) - 1,
                getattr(SmsBookGroup, sms): getattr(SmsBookGroup, sms) - 1
            })

            # bg_no = bg_no
            db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == bg_no).update({
                SmsBookGroup.bg_count: SmsBookGroup.bg_count + 1,
                getattr(SmsBookGroup, member_colunm_name): getattr(SmsBookGroup, member_colunm_name) + 1,
                getattr(SmsBookGroup, sms): getattr(SmsBookGroup, sms) + 1
            })

        if bk_receipt != result.bk_receipt:
            if bk_receipt == 1:
                db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == bg_no).update({
                    SmsBookGroup.bg_receipt: SmsBookGroup.bg_receipt + 1,
                    SmsBookGroup.bg_reject: SmsBookGroup.bg_reject - 1
                })
            else:
                db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == bg_no).update({
                    SmsBookGroup.bg_receipt: SmsBookGroup.bg_receipt - 1,
                    SmsBookGroup.bg_reject: SmsBookGroup.bg_reject + 1
                })

        # 연락처 업데이트
        db.query(SmsBook).filter(SmsBook.bk_no == bk_no).update({
            SmsBook.bg_no: bg_no,
            SmsBook.bk_hp: bk_hp,
            SmsBook.bk_name: bk_name,
            SmsBook.bk_memo: bk_memo,
            SmsBook.bk_receipt: bk_receipt,
            SmsBook.bk_datetime: datetime.now()
        })

        # 가입된 회원일 때
        if result.mb_id:
            mb_hp_exist = db.query(Member.id).filter(Member.mb_id != result.mb_id, Member.mb_hp == bk_hp).all()
            # 회원의 휴대폰 번호가 중복체크.
            if mb_hp_exist.mb_id:
                is_hp_exist = True
            else:
                # 변경된 연락처 정보를 회원 프로필에 반영
                db.query(Member).filter(Member.mb_id == result.mb_id).update({
                    Member.mb_name: bk_name,
                    Member.mb_hp: bk_hp,
                    Member.mb_sms: bk_receipt
                })

        # transaction
        db.commit()

        # if is_hp_exist: # 회원의 휴대폰 번호가 중복.
        # 중복되어있기 때문에 반영되지 않습니다.
        return RedirectResponse(
            url=f"{request.base_url}admin/sms_admin/num_book/write?bk_no={bk_no}&page={request.state.page}",
            status_code=302)


@admin_router.get("/num_book/delete")
def delete_num_book_hp(request: Request,
                       bk_no: Optional[int] = Query(default=None),
                       db: Session = Depends(get_db)):
    """
    번호 삭제
    """
    MEMBER_MENU_KEY = "900800"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException("권한이 없습니다.", 403)

    if not bk_no:
        raise AlertException("고유 번호가 없습니다.", 400)

    result = db.query(SmsBook).filter(SmsBook.bk_no == bk_no).first()
    if not result:
        raise AlertException("데이터가 없습니다.", 400)

    bg_sms = 'bg_receipt' if result.bk_receipt == 1 else 'bg_reject'
    bg_mb = 'bg_member' if result.mb_id else 'bg_nomember'

    db.query(SmsBookGroup).filter(SmsBookGroup.bk_no == bk_no).delete()
    db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == result.bg_no).update({
        SmsBookGroup.bg_count: SmsBookGroup.bg_count - 1,
        getattr(SmsBookGroup, bg_mb): getattr(SmsBookGroup, bg_mb) - 1,
        getattr(SmsBookGroup, bg_sms): getattr(SmsBookGroup, bg_sms) - 1
    })

    return RedirectResponse(url=f"/num_book?page={{ request.state.page }}", status_code=302)


@admin_router.post("/num_book/ajax/check_phone_number")
def check_phone_number(request: Request,
                       bk_no: Optional[int] = Form(default=None),
                       bk_hp: Optional[str] = Form(default=""),
                       mb_id: Optional[str] = Form(default=""),
                       db: Session = Depends(get_db)):
    """
    sms_book 번호 중복체크
    """
    MEMBER_MENU_KEY = "900800"
    request.session["menu_key"] = MEMBER_MENU_KEY
    is_update = True if bk_no is not None else False

    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        return JSONResponse({"msg": "권한이 없습니다"}, 403)

    exist_hplist = []
    if not bk_hp:
        return JSONResponse({"msg": "휴대폰 번호를 입력해주세요"}, 400)

    bk_hp = get_hp(bk_hp)
    filters = []
    if is_update and bk_no:
        filters.append(SmsBook.bk_no != bk_no)

    duplicate_count = db.query(func.count()).filter(SmsBook.bk_hp == bk_hp, *filters).scalar()
    if duplicate_count:
        return JSONResponse({"msg": "같은 번호가 존재합니다.", }, 400)
    # 수정일 때 회원정보에서 중복체크
    if not duplicate_count and is_update:
        filters = []
        if mb_id:
            filters.append(Member.mb_id != mb_id)

        member_phone_data = db.query(Member.mb_id).filter(Member.mb_hp == bk_hp, Member.mb_hp != "", *filters).all()
        for member in member_phone_data:
            exist_hplist.append(member.mb_id)

        return JSONResponse({"msg": "같은 번호가 존재합니다.", "exist": exist_hplist}, 200)

    return JSONResponse({"msg": "사용가능한 번호입니다.", "exist": exist_hplist}, 200)


@admin_router.post("/num_book/multi_update")
def multi_update(request: Request,
                 bk_no_list: list = Form(..., alias='bk_no[]'),
                 atype: Optional[str] = Form(default=""),
                 db: Session = Depends(get_db)):
    """
    휴대폰번호 관리 일괄 수정
    """

    MEMBER_MENU_KEY = "900800"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException("권한이 없습니다.", 403)

    for bk_no in bk_no_list:
        if not bk_no.strip():
            continue

        result = db.query(SmsBook).filter(SmsBook.bk_no == bk_no).first()

        if not result:
            continue

        if atype == 'reject':
            db.query(SmsBook).filter(SmsBook.bk_no == bk_no).update({
                SmsBook.bk_receipt: 0
            })

            if result.mb_id:
                db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == result.bg_no).update({
                    SmsBookGroup.bg_receipt: func.case([
                        (SmsBookGroup.bg_receipt == 0, 0),
                        (SmsBookGroup.bg_receipt > 0, SmsBookGroup.bg_receipt - 1)
                    ], else_=0),
                    SmsBookGroup.bg_reject: SmsBookGroup.bg_reject + 1
                })

        if atype == 'receipt':
            db.query(SmsBook).filter(SmsBook.bk_no == bk_no).update({
                SmsBook.bk_receipt: 1
            })

            if result.mb_id:
                db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == result.bg_no).update({
                    SmsBookGroup.bg_receipt: SmsBookGroup.bg_receipt + 1,
                    SmsBookGroup.bg_reject: func.case([
                        (SmsBookGroup.bg_reject == 0, 0),
                        (SmsBookGroup.bg_reject > 0, SmsBookGroup.bg_reject - 1)
                    ], else_=0)
                })

        elif atype == 'del':
            db.query(SmsBook).filter(SmsBook.bk_no == bk_no).delete()
            bg_sms = 'bg_receipt' if result.bk_receipt == 1 else 'bg_reject'
            bg_mb = 'bg_member' if result.mb_id else 'bg_nomember'

            db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == result.bg_no).update({
                SmsBookGroup.bg_count: case(
                    (SmsBookGroup.bg_count != 0, SmsBookGroup.bg_count - 1),
                    else_=0
                ),
                getattr(SmsBookGroup, bg_sms): case(
                    (getattr(SmsBookGroup, bg_sms) != 0, getattr(SmsBookGroup, bg_sms) - 1),
                    else_=0
                ),
                getattr(SmsBookGroup, bg_mb): case(
                    (getattr(SmsBookGroup, bg_mb) != 0, getattr(SmsBookGroup, bg_mb) - 1),
                    else_=0
                ),
            })

    db.commit()

    query_params = request.query_params
    if query_params:
        query_params = f"?query_params"
    return RedirectResponse(f"/admin/sms_admin/num_book{query_params}", 302)
