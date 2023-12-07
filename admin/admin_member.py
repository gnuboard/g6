from typing import List, Optional
from fastapi import APIRouter, Depends, File, Query, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import asc, desc
from common.database import db_session
import common.models as models
import datetime
from lib.common import *
from common.formclass import MemberForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from lib.pbkdf2 import create_hash
from bbs.social import SocialAuthService
import html
import re


router = APIRouter()
templates = AdminTemplates()
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["getattr"] = getattr
templates.env.globals["today"] = SERVER_TIME.strftime("%Y%m%d")
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["is_none_datetime"] = is_none_datetime

MEMBER_MENU_KEY = "200100"
MEMBER_ICON_DIR = "data/member"
MEMBER_IMAGE_DIR = "data/member_image"

cache = {}

@router.get("/member_list")
async def member_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params),
):
    """
    회원관리 목록
    """
    request.session["menu_key"] = MEMBER_MENU_KEY
    
    error = auth_check_menu(request, request.session["menu_key"], "r")
    if error:
        raise AlertException(error)

    result = select_query(
        request,
        models.Member,
        search_params,
        same_search_fields=["mb_level"],
        prefix_search_fields=[
            "mb_name",
            "mb_nick",
            "mb_tel",
            "mb_hp",
            "mb_datetime",
            "mb_recommend",
        ],
    )
    
    def get_mb_nick(request: Request, member: {}):
        config = request.state.config
        profile_html = ""
        icon_html = ""
        # 회원아이콘 사용
        # 0: 미사용, 1: 아이콘만 표시, 2: 아이콘+이름(닉네임) 표시
        if config.cf_use_member_icon in [0, 2]:
            profile_html = f'<a href="/bbs/profile/{member.mb_id}" class="sv_member" title="{member.mb_nick} 자기소개" title="_blank" rel="nofollow" onclick="return false;">'
        if config.cf_use_member_icon in [1, 2]:
            icon = get_member_icon(member.mb_id)
            icon_html = f'<span class="profile_img"><img src="/{icon}" width="22" height="22"></span>'
        return f'''<div class="sv_wrap" data-memberid="{member.mb_id}">{profile_html}{icon_html}{member.mb_nick}</a><div class="dynamic_sideview"></div></div>'''
    

    def get_sideview(mb_id, name='', email='', homepage=''):
        global cache  # 캐시에 접근
        
        name = name  # name을 처리 (예: 텍스트 클리닝)
        
        # 캐시에서 결과 가져오기
        if f"id:{mb_id}" in cache:
            return cache[f"id:{mb_id}"]
        elif name and f"name:{name}" in cache:
            return cache[f"name:{name}"]
        
        # 이메일과 홈페이지 처리
        enc = StringEncrypt()
        encrypted_email = enc.encrypt(email)
        
        homepage = homepage  # 홈페이지 URL 클리닝 및 검증
        
        get_member_icon(member.mb_id)
        
        # 아이콘 파일 처리
        icon_file_url = None
        if mb_id:
            icon_file_url = get_member_icon(member.mb_id)
            # if os.path.exists(icon_file):
            #     icon_file_url = f'<img src="{icon_file}" alt="icon">'
            
        # HTML 생성
        if mb_id: # for member
            result = f"""
            <span class="sv_wrap">
                <a href="/bbs/profile.php?mb_id={mb_id}" class="sv_member" title="{name} 자기소개" target="_blank" rel="nofollow" onclick="return false;">
                    {f'<span class="profile_img"><img src="/{icon_file_url}" width="22" height="22" alt=""></span>' if icon_file_url else ''}
                    {name}
                </a>
                <span class="sv">
                    <a href="/bbs/memo_form?me_recv_mb_id={mb_id}" rel="nofollow" onclick="win_memo(this.href); return false;">쪽지보내기</a>
                    {f'<a href="/bbs/formmail/{mb_id}?name={name}&email={encrypted_email}" onclick="win_email(this.href); return false;" rel="nofollow">메일보내기</a>' if email else ''}
                    {f'<a href="{homepage}" rel="nofollow noopener" target="_blank">홈페이지</a>' if homepage else ''}
                    <a href="/bbs/profile/{mb_id}" onclick="win_profile(this.href); return false;" rel="nofollow">자기소개</a>
                    <a href="/bbs/new?mb_id={mb_id}" class="link_new_page" onclick="check_goto_new(this.href, event);" rel="nofollow">전체게시물</a>
                    {f'<a href="/admin/member_form?mb_id={mb_id}" target="_blank" rel="nofollow">회원정보변경</a>' if request.state.is_super_admin else ''}
                    {f'<a href="/bbs/point_list?sfl=mb_id&stx={mb_id}" target="_blank" rel="nofollow">포인트내역</a>' if request.state.is_super_admin else ''}
                </span>
            </span>
            """
        else: # for none member
            result = f"""
            <span class="sv_wrap">
                {f'<span class="profile_img"><img src="/{icon_file_url}" width="22" height="22" alt=""></span>' if icon_file_url else ''}
                {name}
                <span class="sv">
                    <a href="/bbs/board/{bo_table}?sfl=wr_name,1&stx={name}" class="sv_guest" rel="nofollow">이름으로 검색</a>
                    {f'<a href="/bbs/formmail/{mb_id}&name={name}&email={email}" onclick="win_email(this.href); return false;" rel="nofollow">메일보내기</a>' if email else ''}
                    {f'<a href="{homepage}" rel="nofollow noopener" target="_blank">홈페이지</a>' if homepage else ''}
                </span>
            </span>
            """            
        
        # 캐시에 결과 저장
        if mb_id:
            cache[f"id:{mb_id}"] = result
        elif name:
            cache[f"name:{name}"] = result
        
        return result    

    for member in result["rows"]:
        groupmember_count = db.query(models.GroupMember).filter(models.GroupMember.mb_id == member.mb_id).count()
        member.groupmember_count = groupmember_count
        # member.mb_icon = get_member_icon(member.mb_id)
        # member.mb_nick = get_mb_nick(request, member)
        if is_none_datetime(member.mb_datetime):
            member.mb_datetime = ""
        else:
            member.mb_datetime = member.mb_datetime.strftime("%y-%m-%d")
        member.nick_sideview = get_sideview(member.mb_id, member.mb_nick, member.mb_email, member.mb_homepage)

    context = {
        "request": request,
        "members": result["rows"],
        "admin": request.state.login_member,  # 로그인해 있는 회원을 관리자로 간주함
        "total_count": result["total_count"],
        "paging": get_paging(
            request, search_params["current_page"], result["total_count"]
        ),
    }
    return templates.TemplateResponse("member_list.html", context)


@router.post("/member_list_update", dependencies=[Depends(validate_token)])
async def member_list_update(
        request: Request,
        db: db_session,
        checks: Optional[List[int]] = Form(None, alias="chk[]"),
        mb_id: Optional[List[str]] = Form(None, alias="mb_id[]"),
        mb_open: Optional[List[int]] = Form(None, alias="mb_open[]"),
        mb_mailling: Optional[List[int]] = Form(None, alias="mb_mailling[]"),
        mb_sms: Optional[List[int]] = Form(None, alias="mb_sms[]"),
        mb_intercept_date: Optional[List[int]] = Form(None, alias="mb_intercept_date[]"),
        mb_level: Optional[List[str]] = Form(None, alias="mb_level[]"),
        act_button: Optional[str] = Form(...),
        ):
    """회원관리 목록 일괄 수정"""
    # 선택수정
    for i in checks:
        member = db.query(models.Member).filter(models.Member.mb_id == mb_id[i]).first()
        if member:
            if (request.state.config.cf_admin == mb_id[i]) or (request.state.login_member.mb_id == mb_id[i]):
                # 관리자와 로그인된 본인은 차단일자를 설정했다면 수정불가
                if get_from_list(mb_intercept_date, i, 0):
                    print("관리자와 로그인된 본인은 차단일자를 설정했다면 수정불가")
                    continue
            
            # print(get_from_list(mb_open, i, 0))
            member.mb_open = get_from_list(mb_open, i, 0)
            member.mb_mailling = get_from_list(mb_mailling, i, 0)
            member.mb_sms = get_from_list(mb_sms, i, 0)
            member.mb_intercept_date = (datetime.now().strftime("%Y%m%d") if get_from_list(mb_intercept_date, i, 0) else "")
            member.mb_level = mb_level[i]
            db.commit()

    return RedirectResponse(f"/admin/member_list?{query_string(request)}", status_code=303)


@router.post("/member_list_delete", dependencies=[Depends(validate_token)])
async def member_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    mb_id: List[str] = Form(None, alias="mb_id[]"),
):
    """회원관리 목록 일괄 삭제"""
    for i in checks:
        # 관리자와 로그인된 본인은 삭제 불가
        if (request.state.config.cf_admin == mb_id[i]) or (request.state.login_member.mb_id == mb_id[i]):
            print("관리자와 로그인된 본인은 삭제 불가")
            continue
        
        member = db.query(models.Member).filter(models.Member.mb_id == mb_id[i]).first()
        if member:
            # 이미 삭제된 회원은 제외
            # if re.match(r"^[0-9]{8}.*삭제함", member.mb_memo):
            #     continue

            # member 의 경우 레코드를 삭제하는게 아니라 mb_id 를 남기고 모두 제거
            member.mb_password = ""
            member.mb_level = 1
            member.mb_email = ""
            member.mb_homepage = ""
            member.mb_tel = ""
            member.mb_hp = ""
            member.mb_zip1 = ""
            member.mb_zip2 = ""
            member.mb_addr1 = ""
            member.mb_addr2 = ""
            member.mb_addr3 = ""
            member.mb_point = 0
            member.mb_profile = ""
            member.mb_birth = ""
            member.mb_sex = ""
            member.mb_signature = ""
            member.mb_memo = (f"{SERVER_TIME.strftime('%Y%m%d')} 삭제함\n{member.mb_memo}")
            member.mb_certify = ""
            member.mb_adult = 0
            member.mb_dupinfo = ""
            
            # 나머지 테이블에서도 삭제
            # 포인트 테이블에서 삭제
            db.query(models.Point).filter(models.Point.mb_id == mb_id[i]).delete()

            # 그룹접근가능 테이블에서 삭제
            db.query(models.GroupMember).filter(models.GroupMember.mb_id == mb_id[i]).delete()
            
            # 쪽지 테이블에서 삭제
            db.query(models.Memo).filter(models.Memo.me_send_mb_id == mb_id[i]).delete()
            
            # 스크랩 테이블에서 삭제
            db.query(models.Scrap).filter(models.Scrap.mb_id == mb_id[i]).delete()
            
            # 관리권한 테이블에서 삭제
            db.query(models.Auth).filter(models.Auth.mb_id == mb_id[i]).delete()

            # 그룹관리자인 경우 그룹관리자를 공백으로
            db.query(models.Group).filter(models.Group.gr_admin == mb_id[i]).update({models.Group.gr_admin: ""})

            # # 게시판관리자인 경우 게시판관리자를 공백으로
            db.query(models.Board).filter(models.Board.bo_admin == mb_id[i]).update({models.Board.bo_admin: ""})

            # 소셜로그인에서 삭제 또는 해제
            # if SocialAuthService.check_exists_by_member_id(mb_id[i]):
            #     SocialAuthService.unlink_social_login(mb_id[i])

            # 아이콘 삭제
            delete_image(f"{MEMBER_ICON_DIR}/{mb_id[i][:2]}", f"{mb_id[i]}.gif", 1)

            # 프로필 이미지 삭제
            delete_image(f"{MEMBER_IMAGE_DIR}/{mb_id[i][:2]}", f"{mb_id[i]}.gif", 1)

            db.commit()

    return RedirectResponse(f"/admin/member_list?{request.query_params}", status_code=303)


@router.get("/member_form")
@router.get("/member_form/{mb_id}")
async def member_form(request: Request, db: db_session,
                mb_id: Optional[str] = None):
    """
    회원추가, 수정 폼
    """
    request.session["menu_key"] = MEMBER_MENU_KEY
    
    error = auth_check_menu(request, request.session["menu_key"], "w")
    if error:
        raise AlertException(error)

    exists_member = None
    if mb_id:
        exists_member = db.query(models.Member).filter_by(mb_id = mb_id).first()
        if not exists_member:
            raise AlertException("회원아이디가 존재하지 않습니다.")
        
        exists_member.mb_icon = get_member_icon(mb_id)
        exists_member.mb_img = get_member_image(mb_id)

    return templates.TemplateResponse("member_form.html", {"request": request, "member": exists_member})



def get_member_icon(mb_id):
    member_icon_dir = f"{MEMBER_ICON_DIR}/{mb_id[:2]}"

    mb_dir = mb_id[:2]
    icon_file = os.path.join(member_icon_dir, f"{mb_id}.gif")

    if os.path.exists(icon_file):
        # icon_url = icon_file.replace(G5_DATA_PATH, G5_DATA_URL)
        icon_filemtime = os.path.getmtime(icon_file) # 캐시를 위해 파일수정시간을 추가
        return f"{icon_file}?{icon_filemtime}"
    # , f'<input type="checkbox" id="del_mb_icon" name="del_mb_icon" value="1">삭제'

    # return None
    return "static/img/no_profile.gif"


def get_member_image(mb_id):
    member_image_dir = f"{MEMBER_IMAGE_DIR}/{mb_id[:2]}"

    mb_dir = mb_id[:2]
    image_file = os.path.join(member_image_dir, f"{mb_id}.gif")

    if os.path.exists(image_file):
        # icon_url = icon_file.replace(G5_DATA_PATH, G5_DATA_URL)
        image_filemtime = os.path.getmtime(image_file) # 캐시를 위해 파일수정시간을 추가
        return f"{image_file}?{image_filemtime}"
    # , f'<input type="checkbox" id="del_mb_icon" name="del_mb_icon" value="1">삭제'

    return None


# 회원수정 폼
# @router.get("/member_form/{mb_id}")
# def member_form_edit(mb_id: str, request: Request, db: db_session):
#     """
#     회원수정 폼
#     """
#     request.session["menu_key"] = MEMBER_MENU_KEY
#     error = auth_check_menu(request, request.session["menu_key"], "r")
#     if error:
#         return templates.TemplateResponse("alert.html", {"request": request, "errors": [error]})

#     exists_member = db.query(models.Member).filter_by(mb_id = mb_id).first()
#     if not exists_member:
#         return templates.TemplateResponse("alert.html", {"request": request, "errors": ["회원아이디가 존재하지 않습니다."]}) 
    
#     exists_member.mb_icon = get_member_icon(mb_id)
#     exists_member.mb_img = get_member_image(mb_id)

#     return templates.TemplateResponse("member_form.html", {"request": request, "member": exists_member})


# DB등록 및 수정
@router.post("/member_form_update", dependencies=[Depends(validate_token)])
async def member_form_update(
        request: Request,
        db: db_session,
        mb_id: str = Form(...),
        mb_password: str = Form(default=""),
        mb_certify_case: Optional[str] = Form(default=""),
        mb_intercept_date: Optional[str] = Form(default=""),
        mb_leave_date: Optional[str] = Form(default=""),
        mb_zip: Optional[str] = Form(default=""),
        form_data: MemberForm = Depends(),
        mb_icon: UploadFile = File(None),
        del_mb_icon: int = Form(None),
        mb_img: UploadFile = File(None),
        del_mb_img: int = Form(None),
    ):    
    error = auth_check_menu(request, request.session["menu_key"], "w")
    if error:
        raise AlertException(error)
    
    # 한국 우편번호 (postalcode)
    form_data.mb_zip1 = mb_zip[:3]
    form_data.mb_zip2 = mb_zip[3:]

    exists_member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not exists_member: # 등록 (회원아이디가 존재하지 않으면)
        
        new_member = models.Member(mb_id=mb_id, **form_data.__dict__)

        if mb_certify_case and form_data.mb_certify:
            new_member.mb_certify = mb_certify_case
            new_member.mb_adult = form_data.mb_adult
        else:
            new_member.mb_certify = ""
            new_member.mb_adult = 0

        if mb_password:
            new_member.mb_password = create_hash(mb_password)
        else:
            # 비밀번호가 없다면 현재시간으로 해시값을 만든후 다시 해시 (알수없게 만드는게 목적)
            new_member.mb_password = create_hash(create_hash(TIME_YMDHIS))

        db.add(new_member)
        db.commit()
        
    else: # 수정 (회원아이디가 존재하면)

        if (request.state.config.cf_admin == mb_id) or (request.state.login_member.mb_id == mb_id):
            # 관리자와 로그인된 본인은 차단일자, 탈퇴일자를 설정했다면 수정불가
            if mb_intercept_date:
                raise AlertException("로그인된 관리자의 차단일자를 설정할 수 없습니다.")
            if mb_leave_date:
                raise AlertException("로그인된 관리자의 탈퇴일자를 설정할 수 없습니다.")

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(exists_member, field, value)

        # 수정시 비밀번호를 입력했다면 (수정에서는 비밀번호를 입력하지 않아도 됨)
        if mb_password:
            exists_member.mb_password = create_hash(mb_password)

        if mb_certify_case and form_data.mb_certify:
            exists_member.mb_certify = mb_certify_case
            exists_member.mb_adult = form_data.mb_adult

        exists_member.mb_intercept_date = mb_intercept_date
        exists_member.mb_leave_date = mb_leave_date

        db.commit()

    upload_member_icon(mb_id, mb_icon, del_mb_icon)
    upload_member_image(mb_id, mb_img, del_mb_img)
    
    return RedirectResponse(url=f"/admin/member_form/{mb_id}", status_code=302)


CF_MEMBER_IMG_WIDTH = 60
CF_MEMBER_IMG_HEIGHT = 60

# 회원이미지 업로드
def upload_member_image(mb_id: str, uploaded_mb_img: UploadFile, del_mb_img: int):
    image_filename = f"{mb_id}.gif"
    member_image_dir = f"{MEMBER_IMAGE_DIR}/{mb_id[:2]}"

    # 이미지 삭제
    delete_image(member_image_dir, image_filename, del_mb_img)

    if uploaded_mb_img.filename == "" or uploaded_mb_img.size == 0:
        return

    IMAGE_REGEX = r"\.(gif|jpe?g|png)$"
    print(uploaded_mb_img.filename)
    if not re.search(IMAGE_REGEX, uploaded_mb_img.filename, re.IGNORECASE):
        raise AlertException(status_code=400, detail="회원이미지 파일은 이미지 파일만 업로드 가능합니다.")

    make_directory(member_image_dir)

    dest_path = os.path.join(member_image_dir, image_filename)
    save_image(member_image_dir, image_filename, uploaded_mb_img)

    if os.path.exists(dest_path):
        with Image.open(dest_path) as img:
            if img.width > CF_MEMBER_IMG_WIDTH or img.height > CF_MEMBER_IMG_HEIGHT:
                if img.format in ['JPEG', 'PNG']:
                    img.thumbnail((CF_MEMBER_IMG_WIDTH, CF_MEMBER_IMG_HEIGHT))
                    os.unlink(dest_path)
                    img.save(dest_path)
                else:
                    os.unlink(dest_path)
                
                
# 회원아이콘 업로드
def upload_member_icon(mb_id: str, mb_icon: UploadFile, del_mb_icon: int):
    member_icon_dir = f"{MEMBER_ICON_DIR}/{mb_id[:2]}"

    # 이미지 삭제
    delete_image(member_icon_dir, f"{mb_id}.gif", del_mb_icon)

    if mb_icon.filename == "" or mb_icon.size == 0:
        return

    if mb_icon.filename[-3:].lower() != "gif":
        raise AlertException(status_code=400, detail="아이콘은 gif 파일만 업로드 가능합니다.")
        # return templates.TemplateResponse("alert.html", {"request": request, "errors": ["아이콘은 gif 파일만 업로드 가능합니다."]})
    
    # make_directory(MEMBER_ICON_DIR)

    make_directory(member_icon_dir) # 하위경로를 만들지 않아도 알아서 만들어줌 data/member/ka/kagla.gif
    # 이미지 저장
    save_image(member_icon_dir, f"{mb_id}.gif", mb_icon)


@router.get("/check_member_id/{mb_id}")
async def check_member_id(mb_id: str, request: Request, db: db_session):
    """
    회원아이디 중복체크
    """
    exists_member = db.query(models.Member).filter_by(mb_id = mb_id).first()
    if exists_member:
        return {"result": "exists"}
    else:
        return {"result": "not_exists"}
    

@router.get("/check_member_email/{mb_email}/{mb_id}")
async def check_member_email(mb_email: str, mb_id: str, request: Request, db: db_session):
    """
    회원이메일 중복체크
    """
    exists_member = db.query(models.Member).filter(models.Member.mb_email == mb_email).filter(models.Member.mb_id != mb_id).first()
    if exists_member:
        return {"result": "exists"}
    else:
        return {"result": "not_exists"}


@router.get("/check_member_nick/{mb_nick}/{mb_id}")
async def check_member_nick(mb_nick: str, mb_id: str, request: Request, db: db_session):
    """
    회원닉네임 중복체크
    """
    exists_member = db.query(models.Member).filter(models.Member.mb_nick == mb_nick).filter(models.Member.mb_id != mb_id).first()
    if exists_member:
        return {"result": "exists"}
    else:
        return {"result": "not_exists"}
