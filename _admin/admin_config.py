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
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals['getattr'] = getattr
templates.env.globals['get_member_id_select'] = get_member_id_select
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_selected'] = get_selected
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['option_array_checked'] = option_array_checked
templates.env.globals['get_admin_menus'] = get_admin_menus


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
    request.session["menu_key"] = "100100"
    
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    
    config = db.query(models.Config).first()
    return templates.TemplateResponse("admin/config_form.html", 
        {
            "request": request, 
            "config": config, 
            "host_name": host_name,
            "host_ip": host_ip,
            # "get_member_id_select": get_member_id_select,
            # "get_skin_select": get_skin_select, 
            # "get_editor_select": get_editor_select,
            # "get_selected": get_selected,
            # "get_member_level_select": get_member_level_select,
            # "option_array_checked": option_array_checked,
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


