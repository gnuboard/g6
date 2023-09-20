from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session
from database import SessionLocal, get_db, engine
# from models import create_dynamic_create_write_table
import models 
from common import *
from jinja2 import Environment, FileSystemLoader
import random
import os
from typing import List, Optional
import socket

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# 파이썬 함수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals['getattr'] = getattr

from admin import router as admin_config_router
router.include_router(admin_config_router, prefix="/admin", tags=["admin"])


@router.get("/")
def base(request: Request, db: Session = Depends(get_db)):
    # template = env.get_template("index.html")
    # render = template.render(request=request)
    # return templates.TemplateResponse(template, {"request": request})
    return templates.TemplateResponse("admin/index.html", {"request": request})


# skin_gubun(new, search, connect, faq 등) 에 따른 스킨을 SELECT 형식으로 얻음
def get_skin_select(skin_gubun, id, selected, event=''):
    skin_path = TEMPLATES_DIR + f"/{skin_gubun}"
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}>')
    html_code.append(f'<option value="">선택</option>')
    for skin in os.listdir(skin_path):
        if os.path.isdir(f"{skin_path}/{skin}"):
            html_code.append(f'<option value="{skin}" {"selected" if skin == selected else ""}>{skin}</option>')
    html_code.append('</select>')
    return ''.join(html_code)


# DHTML 에디터를 SELECT 형식으로 얻음
def get_editor_select(id, selected):
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}">')
    html_code.append(f'<option value="">사용안함</option>')
    for editor in os.listdir("static/plugin/editor"):
        if os.path.isdir(f"static/plugin/editor/{editor}"):
            html_code.append(f'<option value="{editor}" {"selected" if editor == selected else ""}>{editor}</option>')
    html_code.append('</select>')
    return ''.join(html_code)


# 회원아이디를 SELECT 형식으로 얻음
def get_member_id_select(id, level, selected, event=''):
    db = SessionLocal()
    members = db.query(models.Member).filter(models.Member.mb_level >= level).all()
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}><option value="">선택하세요</option>')
    for member in members:
        html_code.append(f'<option value="{member.mb_id}" {"selected" if member.mb_id == selected else ""}>{member.mb_id}</option>')
    html_code.append('</select>')
    return ''.join(html_code)

# 회원레벨을 SELECT 형식으로 얻음
def get_member_level_select(id: str, start: int, end: int, selected: int, event=''):
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}>')
    for i in range(start, end+1):
        html_code.append(f'<option value="{i}" {"selected" if i == selected else ""}>{i}</option>')
    html_code.append('</select>')
    return ''.join(html_code)

# # 캡챠를 SELECT 형식으로 얻음
# def get_captcha_select(id, selected=''):
#     captcha_list = ["kcaptcha", "recaptcha", "recaptcha_inv"]
#     select_options = []
#     select_options.append(f'<select id="{id}" name="{id}" required class="required">')
#     for captcha in captcha_list:
#         if captcha == selected:
#             select_options.append(f'<option value="{captcha}" selected>{captcha}</option>')
#         else:
#             select_options.append(f'<option value="{captcha}">{captcha}</option>')
#     select_options.append('</select>')
#     return ''.join(select_options)


# 필드에 저장된 값과 기본 값을 비교하여 selected 를 반환
def get_selected(field_value, value):
    if isinstance(value, int):
        return ' selected="selected"' if (int(field_value) == int(value)) else ''
    return ' selected="selected"' if (field_value == value) else ''


# function option_array_checked($option, $arr=array()){
#     $checked = '';
#     if( !is_array($arr) ){
#         $arr = explode(',', $arr);
#     }
#     if ( !empty($arr) && in_array($option, (array) $arr) ){
#         $checked = 'checked="checked"';
#     }
#     return $checked;
# }
# 위 코드를 파이썬으로 변환해줘
def option_array_checked(option, arr=[]):
    checked = ''
    if not isinstance(arr, list):
        arr = arr.split(',')
    if arr and option in arr:
        checked = 'checked="checked"'
    return checked


from starlette.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def create_jwt_token(data: dict):
    encoded_jwt = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str):
    try:
        decoded_jwt = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_jwt
    except:
        raise HTTPException(status_code=401, detail="Invalid Token")   
    
security = HTTPBearer()

@router.get("/ajax_token")
def generate_token():
    token_data = random.randint(1, 1000)
    token = create_jwt_token(token_data)
    return {"admin_csrf_token_key": token}

@router.post("/submit_form")
def submit_form(token: HTTPAuthorizationCredentials = Depends(security), form_data: str = Form(...)):
    decoded_token = verify_jwt_token(token.credentials)
    if decoded_token.get("form_data") != form_data:
        raise HTTPException(status_code=400, detail="Form data has been tampered!")
    return {"message": "Form submitted successfully!"}
    

@router.get("/config_form")
def config_form(request: Request, db: Session = Depends(get_db)):
    '''
    기본환경설정
    '''
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    
    config = db.query(models.Config).first()
    return templates.TemplateResponse("admin/config_form.html", 
        {
            "request": request, 
            "config": config, 
            "host_name": host_name,
            "host_ip": host_ip,
            "get_member_id_select": get_member_id_select,
            "get_skin_select": get_skin_select, 
            "get_editor_select": get_editor_select,
            "get_selected": get_selected,
            "get_member_level_select": get_member_level_select,
            "option_array_checked": option_array_checked,
        })
    
@router.post("/config_form_update")  
def config_form_update(request: Request, db: Session = Depends(get_db),
                       cf_title: str = Form(...),
                       cf_admin: str = Form(None),
                       cf_admin_email: str = Form(None),
                       cf_admin_email_name: str = Form(None),
                       cf_use_point: int = Form(None),
                       cf_login_point: int = Form(None),
                       cf_memo_send_point: int = Form(None),
                       cf_cut_name: int = Form(None),
                       cf_nick_modify: int = Form(None),
                       cf_new_del: int = Form(None),
                       cf_memo_del: int = Form(None),
                       cf_visit_del: int = Form(None),
                       cf_popular_del: int = Form(None),
                       cf_login_minutes: int = Form(None),
                       cf_new_rows: int = Form(None),
                       cf_page_rows: int = Form(None),
                       cf_mobile_page_rows: int = Form(None),
                       cf_write_pages: int = Form(None),
                       cf_mobile_pages: int = Form(None),
                       cf_new_skin: str = Form(None),
                       cf_search_skin: str = Form(None),
                       cf_mobile_search_skin: str = Form(None),
                       cf_connect_skin: str = Form(None),
                       cf_mobile_connect_skin: str = Form(None),
                       cf_faq_skin: str = Form(None),
                       cf_mobile_faq_skin: str = Form(None),
                       cf_editor: str = Form(None),
                       cf_captcha: str = Form(None),
                       cf_captcha_mp3: str = Form(None),
                       cf_recaptcha_site_key: str = Form(None),
                       cf_recaptcha_secret_key: str = Form(None),
                       cf_use_copy_log: int = Form(None),
                       cf_point_term: int = Form(None),
                       cf_possible_ip: str = Form(None),
                       cf_intercept_ip: str = Form(None),
                       cf_analytics: str = Form(None),
                       cf_add_meta: str = Form(None),
                       cf_syndi_token: str = Form(None),
                       cf_syndi_except: str = Form(None),
                       cf_delay_sec: int = Form(None),
                       cf_link_target: str = Form(None),
                       cf_read_point: int = Form(None),
                       cf_write_point: int = Form(None),
                       cf_comment_point: int = Form(None),
                       cf_download_point: int = Form(None),
                       cf_search_part: str = Form(None),
                       cf_image_extension: str = Form(None),
                       cf_flash_extension: str = Form(None),
                       cf_movie_extension: str = Form(None),
                       cf_filter: str = Form(None),
                       cf_member_skin: str = Form(None),
                       cf_mobile_member_skin: str = Form(None),
                       cf_use_homepage: int = Form(None),
                       cf_req_homepage: int = Form(None),
                       cf_use_addr: int = Form(None),
                       cf_req_addr: int = Form(None),
                       cf_use_tel: int = Form(None),
                       cf_req_tel: int = Form(None),
                       cf_use_hp: int = Form(None),
                       cf_req_hp: int = Form(None),
                       cf_use_signature: int = Form(None),
                       cf_req_signature: int = Form(None),
                       cf_use_profile: int = Form(None),
                       cf_req_profile: int = Form(None),
                       cf_register_level: int = Form(None),
                       cf_register_point: int = Form(None),
                       cf_leave_day: int = Form(None),
                       cf_use_member_icon: int = Form(None),
                       cf_icon_level: int = Form(None),
                       cf_member_icon_size: int = Form(None),
                       cf_member_icon_width: int = Form(None),
                       cf_member_icon_height: int = Form(None),
                       cf_memeber_img_size: int = Form(None),
                       cf_member_img_width: int = Form(None),
                       cf_member_img_height: int = Form(None),
                       cf_use_recommend: int = Form(None),
                       cf_recommend_point: int = Form(None),
                       cf_prohibit_id: str = Form(None),
                       cf_prohibit_email: str = Form(None),
                       cf_stipulation: str = Form(None),
                       cf_privacy: str = Form(None),
                       cf_cert_use: int = Form(None),
                       cf_cert_find: int = Form(None),
                       cf_cert_simple: int = Form(None),
                       cf_cert_hp: int = Form(None),
                       cf_cert_ipin: int = Form(None),
                       cf_cert_kg_mid: str = Form(None),
                       cf_cert_kg_cd: str = Form(None),
                       cf_cert_kcb_cd: str = Form(None),
                       cf_cert_kcp_cd: str = Form(None),
                       cf_cert_limit: int = Form(None),
                       cf_cert_req: int = Form(None),
                       cf_bbs_rewrite: int = Form(None),
                       cf_email_use: int = Form(None),
                       cf_use_email_certify: int = Form(None),
                       cf_formmail_is_member: int = Form(None),
                       cf_email_wr_super_admin: int = Form(None),
                       cf_email_wr_group_admin: int = Form(None),
                       cf_email_wr_board_admin: int = Form(None),
                       cf_email_wr_write: int = Form(None),
                       cf_email_wr_comment_all: int = Form(None),
                       cf_email_mb_super_admin: int = Form(None),
                       cf_email_mb_member: int = Form(None),
                       cf_email_po_super_admin: int = Form(None),
                       cf_social_login_use: int = Form(None),
                       cf_social_servicelist: Optional[List[str]] = Form(None, alias="cf_social_servicelist[]"),
                       cf_naver_client_id: str = Form(None),
                       cf_naver_secret: str = Form(None),
                       cf_facebook_appid: str = Form(None),
                       cf_twitter_key: str = Form(None),
                       cf_google_client_id: str = Form(None),
                       cf_googl_shorturl_apikey: str = Form(None),
                       cf_kakao_rest_key: str = Form(None),
                       cf_kakao_js_apikey: str = Form(None),
                       cf_payco_client_id: str = Form(None),
                       cf_payco_secret: str = Form(None),
                       cf_add_script: str = Form(None),
                       cf_sms_use: str = Form(None),
                       cf_sms_type: str = Form(None),
                       cf_icode_id: str = Form(None),
                       cf_icode_pw: str = Form(None),
                       cf_icode_server_ip: str = Form(None),
                       cf_icode_token_key: str = Form(None),
                       cf_1_subj: str = Form(None),
                       cf_1: str = Form(None),
                       cf_2_subj: str = Form(None),
                       cf_2: str = Form(None),
                       cf_3_subj: str = Form(None),
                       cf_3: str = Form(None),
                       cf_4_subj: str = Form(None),
                       cf_4: str = Form(None),
                       cf_5_subj: str = Form(None),
                       cf_5: str = Form(None),
                       cf_6_subj: str = Form(None),
                       cf_6: str = Form(None),
                       cf_7_subj: str = Form(None),
                       cf_7: str = Form(None),
                       cf_8_subj: str = Form(None),
                       cf_8: str = Form(None),
                       cf_9_subj: str = Form(None),
                       cf_9: str = Form(None),
                       cf_10_subj: str = Form(None),
                       cf_10: str = Form(None),
                       ):

    # 배열로 넘어오는 자료를 문자열로 변환. 예) "naver,kakao,facebook,google,twitter,payco"
    cf_social_servicelist = ','.join(cf_social_servicelist) if cf_social_servicelist else ''
    
    config = db.query(models.Config).first()
    config.cf_title                 = cf_title
    config.cf_admin                 = cf_admin if cf_admin is not None else ""
    config.cf_admin_email           = cf_admin_email if cf_admin_email is not None else ""
    config.cf_admin_email_name      = cf_admin_email_name if cf_admin_email_name is not None else ""
    config.cf_use_point             = cf_use_point if cf_use_point is not None else 0
    config.cf_login_point           = cf_login_point if cf_login_point is not None else 0
    config.cf_memo_send_point       = cf_memo_send_point if cf_memo_send_point is not None else 0
    config.cf_cut_name              = cf_cut_name if cf_cut_name is not None else 0
    config.cf_nick_modify           = cf_nick_modify if cf_nick_modify is not None else 0
    config.cf_new_del               = cf_new_del if cf_new_del is not None else 0
    config.cf_memo_del              = cf_memo_del if cf_memo_del is not None else 0
    config.cf_visit_del             = cf_visit_del if cf_visit_del is not None else 0
    config.cf_popular_del           = cf_popular_del if cf_popular_del is not None else 0
    config.cf_login_minutes         = cf_login_minutes if cf_login_minutes is not None else 0
    config.cf_new_rows              = cf_new_rows if cf_new_rows is not None else 0
    config.cf_page_rows             = cf_page_rows if cf_page_rows is not None else 0
    config.cf_mobile_page_rows      = cf_mobile_page_rows if cf_mobile_page_rows is not None else 0
    config.cf_write_pages           = cf_write_pages if cf_write_pages is not None else 0
    config.cf_mobile_pages          = cf_mobile_pages if cf_mobile_pages is not None else 0
    config.cf_new_skin              = cf_new_skin if cf_new_skin is not None else ""
    config.cf_search_skin           = cf_search_skin if cf_search_skin is not None else ""
    config.cf_mobile_search_skin    = cf_mobile_search_skin if cf_mobile_search_skin is not None else ""
    config.cf_connect_skin          = cf_connect_skin if cf_connect_skin is not None else ""
    config.cf_mobile_connect_skin   = cf_mobile_connect_skin if cf_mobile_connect_skin is not None else ""
    config.cf_faq_skin              = cf_faq_skin if cf_faq_skin is not None else ""
    config.cf_mobile_faq_skin       = cf_mobile_faq_skin if cf_mobile_faq_skin is not None else ""
    config.cf_editor                = cf_editor if cf_editor is not None else ""
    config.cf_captcha               = cf_captcha if cf_captcha is not None else ""
    config.cf_captcha_mp3           = cf_captcha_mp3 if cf_captcha_mp3 is not None else ""
    config.cf_recaptcha_site_key    = cf_recaptcha_site_key if cf_recaptcha_site_key is not None else ""
    config.cf_recaptcha_secret_key  = cf_recaptcha_secret_key if cf_recaptcha_secret_key is not None else ""
    config.cf_use_copy_log          = cf_use_copy_log if cf_use_copy_log is not None else 0
    config.cf_point_term            = cf_point_term if cf_point_term is not None else 0
    config.cf_possible_ip           = cf_possible_ip if cf_possible_ip is not None else ""
    config.cf_intercept_ip          = cf_intercept_ip if cf_intercept_ip is not None else ""
    config.cf_analytics             = cf_analytics if cf_analytics is not None else ""
    config.cf_add_meta              = cf_add_meta if cf_add_meta is not None else ""
    config.cf_syndi_token           = cf_syndi_token if cf_syndi_token is not None else ""
    config.cf_syndi_except          = cf_syndi_except if cf_syndi_except is not None else ""
    config.cf_delay_sec             = cf_delay_sec if cf_delay_sec is not None else 0
    config.cf_link_target           = cf_link_target if cf_link_target is not None else ""
    config.cf_read_point            = cf_read_point if cf_read_point is not None else 0
    config.cf_write_point           = cf_write_point if cf_write_point is not None else 0
    config.cf_comment_point         = cf_comment_point if cf_comment_point is not None else 0
    config.cf_download_point        = cf_download_point if cf_download_point is not None else 0
    config.cf_search_part           = cf_search_part if cf_search_part is not None else ""
    config.cf_image_extension       = cf_image_extension if cf_image_extension is not None else ""
    config.cf_flash_extension       = cf_flash_extension if cf_flash_extension is not None else ""
    config.cf_movie_extension       = cf_movie_extension if cf_movie_extension is not None else ""
    config.cf_filter                = cf_filter if cf_filter is not None else ""
    config.cf_member_skin           = cf_member_skin if cf_member_skin is not None else ""
    config.cf_mobile_member_skin    = cf_mobile_member_skin if cf_mobile_member_skin is not None else ""
    config.cf_use_homepage          = cf_use_homepage if cf_use_homepage is not None else 0
    config.cf_req_homepage          = cf_req_homepage if cf_req_homepage is not None else 0
    config.cf_use_addr              = cf_use_addr if cf_use_addr is not None else 0
    config.cf_req_addr              = cf_req_addr if cf_req_addr is not None else 0
    config.cf_use_tel               = cf_use_tel if cf_use_tel is not None else 0
    config.cf_req_tel               = cf_req_tel if cf_req_tel is not None else 0
    config.cf_use_hp                = cf_use_hp if cf_use_hp is not None else 0 
    config.cf_req_hp                = cf_req_hp if cf_req_hp is not None else 0
    config.cf_use_signature         = cf_use_signature if cf_use_signature is not None else 0
    config.cf_req_signature         = cf_req_signature if cf_req_signature is not None else 0
    config.cf_use_profile           = cf_use_profile if cf_use_profile is not None else 0
    config.cf_req_profile           = cf_req_profile if cf_req_profile is not None else 0
    config.cf_register_level        = cf_register_level if cf_register_level is not None else 0
    config.cf_register_point        = cf_register_point if cf_register_point is not None else 0
    config.cf_leave_day             = cf_leave_day if cf_leave_day is not None else 0
    config.cf_use_member_icon       = cf_use_member_icon if cf_use_member_icon is not None else 0
    config.cf_icon_level            = cf_icon_level if cf_icon_level is not None else 0
    config.cf_member_icon_size      = cf_member_icon_size if cf_member_icon_size is not None else 0
    config.cf_member_icon_width     = cf_member_icon_width if cf_member_icon_width is not None else 0
    config.cf_member_icon_height    = cf_member_icon_height if cf_member_icon_height is not None else 0
    config.cf_memeber_img_size      = cf_memeber_img_size if cf_memeber_img_size is not None else 0
    config.cf_member_img_width      = cf_member_img_width if cf_member_img_width is not None else 0
    config.cf_member_img_height     = cf_member_img_height if cf_member_img_height is not None else 0
    config.cf_use_recommend         = cf_use_recommend if cf_use_recommend is not None else 0
    config.cf_recommend_point       = cf_recommend_point if cf_recommend_point is not None else 0
    config.cf_prohibit_id           = cf_prohibit_id if cf_prohibit_id is not None else ""
    config.cf_prohibit_email        = cf_prohibit_email if cf_prohibit_email is not None else ""
    config.cf_stipulation           = cf_stipulation if cf_stipulation is not None else ""
    config.cf_privacy               = cf_privacy if cf_privacy is not None else ""
    config.cf_cert_use              = cf_cert_use if cf_cert_use is not None else 0
    config.cf_cert_find             = cf_cert_find if cf_cert_find is not None else 0
    config.cf_cert_simple           = cf_cert_simple if cf_cert_simple is not None else 0
    config.cf_cert_hp               = cf_cert_hp if cf_cert_hp is not None else 0
    config.cf_cert_ipin             = cf_cert_ipin if cf_cert_ipin is not None else 0
    config.cf_cert_kg_mid           = cf_cert_kg_mid if cf_cert_kg_mid is not None else ""
    config.cf_cert_kg_cd            = cf_cert_kg_cd if cf_cert_kg_cd is not None else ""
    config.cf_cert_kcb_cd           = cf_cert_kcb_cd if cf_cert_kcb_cd is not None else ""
    config.cf_cert_kcp_cd           = cf_cert_kcp_cd if cf_cert_kcp_cd is not None else ""
    config.cf_cert_limit            = cf_cert_limit if cf_cert_limit is not None else 0
    config.cf_cert_req              = cf_cert_req if cf_cert_req is not None else 0
    config.cf_bbs_rewrite           = cf_bbs_rewrite if cf_bbs_rewrite is not None else 0
    config.cf_email_use             = cf_email_use if cf_email_use is not None else 0
    config.cf_use_email_certify     = cf_use_email_certify if cf_use_email_certify is not None else 0
    config.cf_formmail_is_member    = cf_formmail_is_member if cf_formmail_is_member is not None else 0
    config.cf_email_wr_super_admin  = cf_email_wr_super_admin if cf_email_wr_super_admin is not None else 0
    config.cf_email_wr_group_admin  = cf_email_wr_group_admin if cf_email_wr_group_admin is not None else 0
    config.cf_email_wr_board_admin  = cf_email_wr_board_admin if cf_email_wr_board_admin is not None else 0
    config.cf_email_wr_write        = cf_email_wr_write if cf_email_wr_write is not None else 0
    config.cf_email_wr_comment_all  = cf_email_wr_comment_all if cf_email_wr_comment_all is not None else 0
    config.cf_email_mb_super_admin  = cf_email_mb_super_admin if cf_email_mb_super_admin is not None else 0
    config.cf_email_mb_member       = cf_email_mb_member if cf_email_mb_member is not None else 0
    config.cf_email_po_super_admin  = cf_email_po_super_admin if cf_email_po_super_admin is not None else 0
    config.cf_social_login_use      = cf_social_login_use if cf_social_login_use is not None else 0
    config.cf_social_servicelist    = cf_social_servicelist if cf_social_servicelist is not None else ""
    config.cf_naver_client_id       = cf_naver_client_id if cf_naver_client_id is not None else ""
    config.cf_naver_secret          = cf_naver_secret if cf_naver_secret is not None else ""
    config.cf_facebook_appid        = cf_facebook_appid if cf_facebook_appid is not None else ""
    config.cf_twitter_key           = cf_twitter_key if cf_twitter_key is not None else ""
    config.cf_google_client_id      = cf_google_client_id if cf_google_client_id is not None else ""
    config.cf_googl_shorturl_apikey = cf_googl_shorturl_apikey if cf_googl_shorturl_apikey is not None else ""
    config.cf_kakao_rest_key        = cf_kakao_rest_key if cf_kakao_rest_key is not None else ""
    config.cf_kakao_js_apikey       = cf_kakao_js_apikey if cf_kakao_js_apikey is not None else ""
    config.cf_payco_client_id       = cf_payco_client_id if cf_payco_client_id is not None else ""
    config.cf_payco_secret          = cf_payco_secret if cf_payco_secret is not None else ""
    config.cf_add_script            = cf_add_script if cf_add_script is not None else ""
    config.cf_sms_use               = cf_sms_use if cf_sms_use is not None else ""
    config.cf_sms_type              = cf_sms_type if cf_sms_type is not None else ""
    config.cf_icode_id              = cf_icode_id if cf_icode_id is not None else ""
    config.cf_icode_pw              = cf_icode_pw if cf_icode_pw is not None else ""
    config.cf_icode_server_ip       = cf_icode_server_ip if cf_icode_server_ip is not None else ""
    config.cf_icode_token_key       = cf_icode_token_key if cf_icode_token_key is not None else ""
    config.cf_1_subj                = cf_1_subj if cf_1_subj is not None else ""
    config.cf_1                     = cf_1 if cf_1 is not None else ""
    config.cf_2_subj                = cf_2_subj if cf_2_subj is not None else ""
    config.cf_2                     = cf_2 if cf_2 is not None else ""
    config.cf_3_subj                = cf_3_subj if cf_3_subj is not None else ""
    config.cf_3                     = cf_3 if cf_3 is not None else ""
    config.cf_4_subj                = cf_4_subj if cf_4_subj is not None else ""
    config.cf_4                     = cf_4 if cf_4 is not None else ""
    config.cf_5_subj                = cf_5_subj if cf_5_subj is not None else ""
    config.cf_5                     = cf_5 if cf_5 is not None else ""
    config.cf_6_subj                = cf_6_subj if cf_6_subj is not None else ""
    config.cf_6                     = cf_6 if cf_6 is not None else ""
    config.cf_7_subj                = cf_7_subj if cf_7_subj is not None else ""
    config.cf_7                     = cf_7 if cf_7 is not None else ""
    config.cf_8_subj                = cf_8_subj if cf_8_subj is not None else ""
    config.cf_8                     = cf_8 if cf_8 is not None else ""
    config.cf_9_subj                = cf_9_subj if cf_9_subj is not None else ""
    config.cf_9                     = cf_9 if cf_9 is not None else ""
    config.cf_10_subj               = cf_10_subj if cf_10_subj is not None else ""
    config.cf_10                    = cf_10 if cf_10 is not None else ""                      
    
    db.commit()
    return RedirectResponse("/admin/config_form", status_code=303)


@router.get("/board_list")
def board_list(request: Request, db: Session = Depends(get_db)):
    boards = db.query(models.Board).all()
    return templates.TemplateResponse("admin/board_list.html", {"request": request, "boards": boards})


@router.get("/board_form")
def board_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("admin/board_form.html", {"request": request})


@router.get("/board_form/{bo_table}")
def board_form(bo_table: str, request: Request, db: Session = Depends(get_db)):
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return templates.TemplateResponse("admin/board_form.html", {"request": request, "board": board})


@router.post("/board_form_update")  
def board_form_update(request: Request, db: Session = Depends(get_db),
                        bo_table: str = Form(...),
                        gr_id: str = Form(...),
                        bo_subject: str = Form(...),
                        bo_mobile_subject: str = Form(None),
                        bo_device: str = Form(...),
                        bo_admin: str = Form(None),
                        bo_category_list: str = Form(None)
                        # bo_list_level: int = Form(...),
                        # bo_read_level: int = Form(...),
                        # bo_write_level: int = Form(...),
                        # bo_reply_level: int = Form(...),
                        # bo_comment_level: int = Form(...),
                        # bo_upload_level: int = Form(...),
                        # bo_download_level: int = Form(...),
                        # bo_html_level: int = Form(...),
                        # bo_link_level: int = Form(...),
                        # bo_count_delete: int = Form(...),
                        # bo_count_modify: int = Form(...),
                        # bo_read_point: int = Form(...),
                        # bo_write_point: int = Form(...),
                        # bo_comment_point: int = Form(...),
                        # bo_download_point: int = Form(...),
                        # bo_use_category: int = Form(...),
                        # bo_category_list: str = Form(...),
                        # bo_use_sideview: int = Form(...),
                        # bo_use_file_content: int = Form(...),
                        # bo_use_secret: int = Form(...),
                        # bo_use_dhtml_editor: int = Form(...),
                        # bo_select_editor: str = Form(...),
                        # bo_use_rss_view: int = Form(...),
                        # bo_use_good: int = Form(...),
                        # bo_use_nogood: int = Form(...),
                        # bo_use_name: int = Form(...),
                        # bo_use_signature: int = Form(...),
                        # bo_use_ip_view: int = Form(...),
                        # bo_use_list_view: int = Form(...),
                        # bo_use_list_file: int = Form(...),
                        # bo_use_list_content: int = Form(...),
                        # bo_table_width: int = Form(...),
                        # bo_subject_len: int = Form(...),
                        # bo_mobile_subject_len: int = Form(...),
                        # bo_page_rows: int = Form(...),
                        # bo_mobile_page_rows: int = Form(...),
                        # bo_new: int = Form(...),
                        # bo_hot: int = Form(...),
                        # bo_image_width: int = Form(...),
                        # bo_skin: str = Form(...),
                        # bo_mobile_skin: str = Form(...),
                        # bo_include_head: str = Form(...),
                        # bo_include_tail: str = Form(...),
                        # bo_content_head: str = Form(...),
                        # bo_mobile_content_head: str = Form(...),
                        # bo_content_tail: str = Form(...),
                        # bo_mobile_content_tail: str = Form(...),
                        # bo_insert_content: str = Form(...),
                        # bo_gallery_cols: int = Form(...),
                        # bo_gallery_width: int = Form(...),
                        # bo_gallery_height: int = Form(...),
                        # bo_mobile_gallery_width: int = Form(...),
                        # bo_mobile_gallery_height: int = Form(...),
                        # bo_upload_size: int = Form(...),
                        # bo_reply_order: int = Form(...),
                        # bo_use_search: int = Form(...),
                        # bo_order: int = Form(...),
                        # bo_count_write: int = Form(...),
                        # bo_count_comment: int = Form(...),
                        # bo_write_min: int = Form(...),
                        # bo_write_max: int = Form(...),
                        # bo_comment_min: int = Form(...),
                        # bo_comment_max: int = Form(...),
                        # bo_notice: str = Form(...),
                        # bo_upload_count: int = Form(...),
                        # bo_use_email: int = Form(...),
                        # bo_use_cert: str = Form(...),
                        # bo_use_sns: int = Form(...),
                        # bo_use_captcha: int = Form(...),
                        # bo_sort_field: str = Form(...),
                        # bo_1_subj: str = Form(...),
                        # bo_2_subj: str = Form(...),
                        # bo_3_subj: str = Form(...),
                        # bo_4_subj: str = Form(...),
                        # bo_5_subj: str = Form(...),
                        # bo_6_subj: str = Form(...),
                        # bo_7_subj: str = Form(...),
                        # bo_8_subj: str = Form(...),
                        # bo_9_subj: str = Form(...),
                        # bo_10_subj: str = Form(...),
                        # bo_1: str = Form(...),
                        # bo_2: str = Form(...),
                        # bo_3: str = Form(...),
                        # bo_4: str = Form(...),
                        # bo_5: str = Form(...),
                        # bo_6: str = Form(...),
                        # bo_7: str = Form(...),
                        # bo_8: str = Form(...),
                        # bo_9: str = Form(...),
                        # bo_10: str = Form(...),                       
                        ):
    board = db.query(models.Board).filter(models.Board.bo_table == bo_table).first()
    if (board):
        board.gr_id = gr_id
        board.bo_subject = bo_subject
        board.bo_mobile_subject = bo_mobile_subject if bo_mobile_subject is not None else ""
        board.bo_device = bo_device
        board.bo_admin = bo_admin if bo_admin is not None else ""
        board.bo_category_list = bo_category_list if bo_category_list is not None else ""
        db.commit()
    else:
        board = models.Board(
            bo_table=bo_table,
            gr_id=gr_id,
            bo_subject=bo_subject if bo_subject is not None else "",
            bo_mobile_subject=bo_mobile_subject if bo_mobile_subject is not None else "",
            bo_device=bo_device,
            bo_admin=bo_admin if bo_admin is not None else "",
            bo_category_list=bo_category_list if bo_category_list is not None else "",
            # bo_list_level=bo_list_level,
            # bo_read_level=bo_read_level,
            # bo_write_level=bo_write_level,
            # bo_reply_level=bo_reply_level,
            # bo_comment_level=bo_comment_level,
            # bo_upload_level=bo_upload_level,
            # bo_download_level=bo_download_level,
            # bo_html_level=bo_html_level,
            # bo_link_level=bo_link_level,
            # bo_count_delete=bo_count_delete,
            # bo_count_modify=bo_count_modify,
            # bo_read_point=bo_read_point,
            # bo_write_point=bo_write_point,
            # bo_comment_point=bo_comment_point,
            # bo_download_point=bo_download_point,
            # bo_use_category=bo_use_category,
            # bo_category_list=bo_category_list,
            # bo_use_sideview=bo_use_sideview,
            # bo_use_file_content=bo_use_file_content,
            # bo_use_secret=bo_use_secret,
            # bo_use_dhtml_editor=bo_use_dhtml_editor,
            # bo_select_editor=bo_select_editor,
            # bo_use_rss_view=bo_use_rss_view,
            # bo_use_good=bo_use_good,
            # bo_use_nogood=bo_use_nogood,
            # bo_use_name=bo_use_name,
            # bo_use_signature=bo_use_signature,
            # bo_use_ip_view=bo_use_ip_view,
            # bo_use_list_view=bo_use_list_view,
            # bo_use_list_file=bo_use_list_file,
            # bo_use_list_content=bo_use_list_content,
            # bo_table_width=bo_table_width,
            # bo_subject_len=bo_subject_len,
            # bo_mobile_subject_len=bo_mobile_subject_len,
            # bo_page_rows=bo_page_rows,
            # bo_mobile_page_rows=bo_mobile_page_rows,
            # bo_new=bo_new,
            # bo_hot=bo_hot,
            # bo_image_width=bo_image_width,
            # bo_skin=bo_skin,
            # bo_mobile_skin=bo_mobile_skin,
            # bo_include_head=bo_include_head,
            # bo_include_tail=bo_include_tail,
            # bo_content_head=bo_content_head,
            # bo_mobile_content_head=bo_mobile_content_head,
            # bo_content_tail=bo_content_tail,
            # bo_mobile_content_tail=bo_mobile_content_tail,
            # bo_insert_content=bo_insert_content,
            # bo_gallery_cols=bo_gallery_cols,
            # bo_gallery_width=bo_gallery_width,
            # bo_gallery_height=bo_gallery_height,
            # bo_mobile_gallery_width=bo_mobile_gallery_width,
            # bo_mobile_gallery_height=bo_mobile_gallery_height,
            # bo_upload_size=bo_upload_size,
            # bo_reply_order=bo_reply_order,
            # bo_use_search=bo_use_search,
            # bo_order=bo_order,
            # bo_count_write=bo_count_write,
            # bo_count_comment=bo_count_comment,
            # bo_write_min=bo_write_min,
            # bo_write_max=bo_write_max,
            # bo_comment_min=bo_comment_min,
            # bo_comment_max=bo_comment_max,
            # bo_notice=bo_notice,
            # bo_upload_count=bo_upload_count,
            # bo_use_email=bo_use_email,
            # bo_use_cert=bo_use_cert,
            # bo_use_sns=bo_use_sns,
            # bo_use_captcha=bo_use_captcha,
            # bo_sort_field=bo_sort_field,
            # bo_1_subj=bo_1_subj,
            # bo_2_subj=bo_2_subj,
            # bo_3_subj=bo_3_subj,
            # bo_4_subj=bo_4_subj,
            # bo_5_subj=bo_5_subj,
            # bo_6_subj=bo_6_subj,
            # bo_7_subj=bo_7_subj,
            # bo_8_subj=bo_8_subj,
            # bo_9_subj=bo_9_subj,
            # bo_10_subj=bo_10_subj,
            # bo_1=bo_1,
            # bo_2=bo_2,
            # bo_3=bo_3,
            # bo_4=bo_4,
            # bo_5=bo_5,
            # bo_6=bo_6,
            # bo_7=bo_7,
            # bo_8=bo_8,
            # bo_9=bo_9,
            # bo_10=bo_10,
        )
        db.add(board)
        db.commit()
        
        # 새로운 게시판 테이블 생성
        # 지금 생성하지 않아도 자동으로 만들어짐
        # DynamicModel = dynamic_create_write_table(bo_table)
        
        # 처음 한번만 테이블을 생성한다.
        dynamic_create_write_table(bo_table, True)
        
        # DynamicModel = create_dynamic_create_write_table(f"g5_write_{bo_table}")

        # # 게시판 글, 댓글 테이블 생성
        # metadata = MetaData()
        
        # # src_table = models.Write.__table__        
        # # new_table = src_table.tometadata(metadata, f"{src_table}_{bo_table}")
        # # new_table.create(bind=db.bind)
        
        # src_table_name = models.Write.__table__
        # src_table = Table(src_table_name, metadata, autoload=engine)
        # new_table = Table(f"{src_table_name}_{bo_table}", metadata, *(column.copy() for column in src_table.columns))
        # new_table.create(engine)
        
        # with engine.begin() as conn:
        #     data = conn.execute(select([src_table])).fetchall()
        #     if data:
        #         conn.execute(new_table.insert(), data)
                
    return RedirectResponse("admin/board_list", status_code=303)
