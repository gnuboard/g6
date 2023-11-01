import hashlib
import logging
import os
import random
import re
from time import sleep
from typing import Any, Dict, List, Optional, Union
import uuid
from urllib.parse import urlencode
import PIL
import shutil
from fastapi import Query, Request, HTTPException, UploadFile
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from passlib.context import CryptContext
from sqlalchemy import Index, asc, desc, and_, or_, func, extract
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, Session
from models import Auth, Config, Member, Memo, Board, Group, Menu, NewWin, Point, Poll, Popular, Visit, VisitSum, UniqId
from models import WriteBaseModel
from database import SessionLocal, engine, DB_TABLE_PREFIX
from datetime import datetime, timedelta, date, time
import json
from PIL import Image
from user_agents import parse
import base64
from dotenv import load_dotenv
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


load_dotenv()


# 전역변수 선언(global variables)
TEMPLATES = "templates"
EDITOR_PATH = f"{TEMPLATES}/editor"

def get_theme_from_db(config=None):
    # main.py 에서 config 를 인수로 받아서 사용
    if not config:
        db: Session = SessionLocal()
        config = db.query(Config).first()
    theme = config.cf_theme if config and config.cf_theme else "basic"
    theme_path = f"{TEMPLATES}/{theme}"
    
    # Check if the directory exists
    if not os.path.exists(theme_path):
        theme_path = f"{TEMPLATES}/basic"
    
    return theme_path

# python setup.py 를 실행하는 것이 아니라면
if os.environ.get("is_setup") != "true":
    TEMPLATES_DIR = get_theme_from_db()
    
ADMIN_TEMPLATES_DIR = "_admin/templates"

SERVER_TIME = datetime.now()
TIME_YMDHIS = SERVER_TIME.strftime("%Y-%m-%d %H:%M:%S")
TIME_YMD = TIME_YMDHIS[:10]

# pc 설정 시 모바일 기기에서도 PC화면 보여짐
# mobile 설정 시 PC에서도 모바일화면 보여짐
# both 설정 시 접속 기기에 따른 화면 보여짐 (pc에서 접속하면 pc화면을, mobile과 tablet에서 접속하면 mobile 화면)
SET_DEVICE = 'both'

# mobile 을 사용하지 않을 경우 False 로 설정
USE_MOBILE = True
    

def hash_password(password: str):
    '''
    비밀번호를 해시화하여 반환하는 함수
    '''
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)  


def verify_password(plain_password, hashed_passwd):
    '''
    입력한 비밀번호와 해시화된 비밀번호를 비교하여 일치 여부를 반환하는 함수
    '''
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_passwd)  

# 동적 모델 캐싱: 모델이 이미 생성되었는지 확인하고, 생성되지 않았을 경우에만 새로 생성하는 방법입니다. 
# 이를 위해 간단한 전역 딕셔너리를 사용하여 이미 생성된 모델을 추적할 수 있습니다.
_created_models = {}

# 동적 게시판 모델 생성
def dynamic_create_write_table(table_name: str, create_table: bool = False):
    '''
    WriteBaseModel 로 부터 게시판 테이블 구조를 복사하여 동적 모델로 생성하는 함수
    인수의 table_name 에서는 DB_TABLE_PREFIX + 'write_' 를 제외한 테이블 이름만 입력받는다.
    Create Dynamic Write Table Model from WriteBaseModel
    '''
    # 이미 생성된 모델 반환
    if table_name in _created_models:
        return _created_models[table_name]
    
    class_name = "Write" + table_name.capitalize()
    DynamicModel = type(
        class_name, 
        (WriteBaseModel,), 
        {   
            "__tablename__": DB_TABLE_PREFIX + 'write_' + table_name,
            "__table_args__": (
                Index(f'idx_wr_num_reply_{table_name}', 'wr_num', 'wr_reply'),
                Index(f'idex_wr_is_comment_{table_name}', 'wr_is_comment'),
                {"extend_existing": True}),
        }
    )
    # 게시판 추가시 한번만 테이블 생성
    if (create_table):
        DynamicModel.__table__.create(bind=engine, checkfirst=True)
    # 생성된 모델 캐싱
    _created_models[table_name] = DynamicModel
    return DynamicModel

def get_real_client_ip(request: Request):
    '''
    클라이언트의 IP 주소를 반환하는 함수
    '''
    if 'X-Forwarded-For' in request.headers:
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    return request.client.host


def session_member_key(request: Request, member: Member):
    '''
    세션에 저장할 회원의 고유키를 생성하여 반환하는 함수
    '''
    ss_mb_key = hashlib.md5((member.mb_datetime.strftime(format="%Y-%m-%d %H:%M:%S") + get_real_client_ip(request) + request.headers.get('User-Agent')).encode()).hexdigest()
    return ss_mb_key


# 회원레벨을 SELECT 형식으로 얻음
def get_member_level_select(id: str, start: int, end: int, selected: int, event=''):
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}>')
    for i in range(start, end+1):
        html_code.append(f'<option value="{i}" {"selected" if i == selected else ""}>{i}</option>')
    html_code.append('</select>')
    return ''.join(html_code)

    
# skin_gubun(new, search, connect, faq 등) 에 따른 스킨을 SELECT 형식으로 얻음
def get_skin_select(skin_gubun, id, selected, event='', device='pc'):
    skin_path = TEMPLATES_DIR + f"/{skin_gubun}/{device}"
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}>')
    html_code.append(f'<option value="">선택</option>')
    for skin in os.listdir(skin_path):
        # print(f"{skin_path}/{skin}")
        if os.path.isdir(f"{skin_path}/{skin}"):
            html_code.append(f'<option value="{skin}" {"selected" if skin == selected else ""}>{skin}</option>')
    html_code.append('</select>')
    return ''.join(html_code)


# DHTML 에디터를 SELECT 형식으로 얻음
def get_editor_select(id, selected):
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}">')
    if id == 'bo_select_editor':
        html_code.append(f'<option value="" {"selected" if selected == "" else ""}>기본환경설정의 에디터 사용</option>')
    else:
        html_code.append(f'<option value="">사용안함</option>')
    for editor in os.listdir("static/plugin/editor"):
        if editor == 'textarea':
            continue
        if os.path.isdir(f"static/plugin/editor/{editor}"):
            html_code.append(f'<option value="{editor}" {"selected" if editor == selected else ""}>{editor}</option>')
    html_code.append('</select>')
    return ''.join(html_code)


# 회원아이디를 SELECT 형식으로 얻음
def get_member_id_select(id, level, selected, event=''):
    db = SessionLocal()
    # 테이블에서 지정된 필드만 가져 오는 경우 load_only(Member.field1, Member.field2) 함수를 사용 
    members = db.query(Member).options(load_only(Member.mb_id)).filter(Member.mb_level >= level).all()
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}><option value="">선택하세요</option>')
    for member in members:
        html_code.append(f'<option value="{member.mb_id}" {"selected" if member.mb_id == selected else ""}>{member.mb_id}</option>')
    html_code.append('</select>')
    return ''.join(html_code)


# 필드에 저장된 값과 기본 값을 비교하여 selected 를 반환
# def get_selected(field_value, value):
#     if field_value is None or value is None or field_value == '' or value == '':
#         return ''
#     if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
#         return ' selected="selected"' if (int(field_value) == int(value)) else ''
#     return ' selected="selected"' if (field_value == value) else ''

def get_selected(field_value, value):
    if field_value is None or value is None or field_value == '' or value == '':
        return ''
    if ((isinstance(field_value, str) and field_value.isdigit()) and (
            isinstance(value, int) or (isinstance(value, str) and value.isdigit()))):
        return ' selected="selected"' if int(field_value) == int(value) else ''
    return ' selected="selected"' if field_value == value else ''


def option_array_checked(option, arr=[]):
    checked = ''
    if not isinstance(arr, list):
        arr = arr.split(',')
    if arr and option in arr:
        checked = 'checked="checked"'
    return checked


def get_group_select(id, selected='', event=''):
    db = SessionLocal()
    groups = db.query(Group).order_by(Group.gr_id).all()
    str = f'<select id="{id}" name="{id}" {event}>\n'
    for i, group in enumerate(groups):
        if i == 0:
            str += '<option value="">선택</option>'
        str += option_selected(group.gr_id, selected, group.gr_subject)
    str += '</select>'
    return str


def option_selected(value, selected, text=''):
    if not text:
        text = value
    if value == selected:
        return f'<option value="{value}" selected="selected">{text}</option>\n'
    else:
        return f'<option value="{value}">{text}</option>\n'
    



def subject_sort_link(request: Request, column: str, query_string: str ='', flag: str ='asc'):
    # 현재 상태에서 sst, sod, sfl, stx, sca, page 값을 가져온다.
    sst = request.state.sst if request.state.sst is not None else ""
    sod = request.state.sod if request.state.sod is not None else ""
    sfl = request.state.sfl if request.state.sfl is not None else ""
    stx = request.state.stx if request.state.stx is not None else ""
    sca = request.state.sca if request.state.sca is not None else ""
    page = request.state.page if request.state.page is not None else "" 
    
    # q1에는 column 값을 추가한다.
    q1 = f"sst={column}"

    if flag == 'asc':
        # flag가 'asc'인 경우, q2에 'sod=asc'를 할당한다.
        q2 = 'sod=asc'
        if sst == column:
            if sod == 'asc':
                # 현재 상태에서 sst와 col이 같고 sod가 'asc'인 경우, q2를 'sod=desc'로 변경한다.
                q2 = 'sod=desc'
    else:
        # flag가 'asc'가 아닌 경우, q2에 'sod=desc'를 할당한다.
        q2 = 'sod=desc'
        if sst == column:
            if sod == 'desc':
                # 현재 상태에서 sst와 col이 같고 sod가 'desc'인 경우, q2를 'sod=asc'로 변경한다.
                q2 = 'sod=asc'

    # query_string, q1, q2를 arr_query 리스트에 추가한다.
    arr_query = []
    arr_query.append(query_string)
    arr_query.append(q1)
    arr_query.append(q2)

    # sfl, stx, sca, page 값이 None이 아닌 경우, 각각의 값을 arr_query에 추가한다.
    if sfl is not None:
        arr_query.append(f'sfl={sfl}')
    if stx is not None:
        arr_query.append(f'stx={stx}')
    if sca is not None:
        arr_query.append(f'sca={sca}')
    if page is not None:
        arr_query.append(f'page={page}')

    # arr_query의 첫 번째 요소를 제외한 나머지 요소를 '&'로 연결하여 qstr에 할당한다.
    qstr = '&'.join(arr_query[1:]) if arr_query else ''
    # qstr을 '&'로 분리하여 pairs 리스트에 저장한다.
    pairs = qstr.split('&')

    # params 딕셔너리를 생성한다.
    params = {}

    # pairs 리스트의 각 요소를 '='로 분리하여 key와 value로 나누고, value가 빈 문자열이 아닌 경우 params에 추가한다.
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=')
            if value != '':
                params[key] = value

    # qstr을 쿼리 문자열로 사용하여 링크를 생성하고 반환한다.
    return f'<a href="?{qstr}">'

# 함수 테스트
# print(subject_sort_link('title', query_string='type=list', flag='asc', sst='title', sod='asc', sfl='category', stx='example', page=2))


def get_admin_menus():
    '''
    1, 2단계로 구분된 관리자 메뉴 json 파일이 있으면 load 하여 반환하는 함수
    '''
    files = [
        "_admin/admin_menu_bbs.json",
        "_admin/admin_menu_shop.json",
        "_admin/admin_menu_sms.json"
    ]
    menus = {}
    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                menus.update(json.load(file))
    return menus


def get_head_tail_img(dir: str, filename: str):
    '''
    게시판의 head, tail 이미지를 반환하는 함수
    '''
    img_path = os.path.join('data', dir, filename)  # 변수명 변경
    img_exists = os.path.exists(img_path)
    width = None
    
    if img_exists:
        try:
            with Image.open(img_path) as img_file:
                width = img_file.width
                if width > 750:
                    width = 750
        except PIL.UnidentifiedImageError:
            # 이미지를 열 수 없을 때의 처리
            img_exists = False
            print(f"Error: Cannot identify image file '{img_path}'")
    
    return {
        "img_exists": img_exists,
        "img_url": os.path.join('/data', dir, filename) if img_exists else None,
        "width": width
    }
    
def now():
    '''
    현재 시간을 반환하는 함수
    '''
    return datetime.now().timestamp()

import cachetools

# 캐시 크기와 만료 시간 설정
cache = cachetools.TTLCache(maxsize=10000, ttl=3600)

# def generate_one_time_token():
#     '''
#     1회용 토큰을 생성하여 반환하는 함수
#     '''
#     token = os.urandom(24).hex()
#     cache[token] = 'valid'
#     return token


# def validate_one_time_token(token):
#     '''
#     1회용 토큰을 검증하는 함수
#     '''
#     if token in cache:
#         del cache[token]
#         return True
#     return False


def generate_one_time_token(action: str = 'create'):
    '''
    1회용 토큰을 생성하여 반환하는 함수
    action : 'insert', 'update', 'delete' ...
    '''
    token = os.urandom(24).hex()
    cache[token] = {'status': 'valid', 'action': action}
    return token


def validate_one_time_token(token, action: str = 'create'):
    '''
    1회용 토큰을 검증하는 함수
    '''
    token_data = cache.get(token)
    if token_data and token_data.get("action") == action:
        del cache[token]
        return True
    return False


def check_token(request: Request, token: str):
    '''
    세션과 인수로 넘어온 토큰확인 함수
    '''
    if token and token == request.session.get("ss_token"):
        # 세션 삭제
        request.session["ss_token"] = ""
        return True
    return False


def get_client_ip(request: Request):
    '''
    클라이언트의 IP 주소를 반환하는 함수 (PHP의 $_SERVER['REMOTE_ADDR'])
    '''
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list of IPs.
        # The client's requested IP will be the first one.
        client_ip = x_forwarded_for.split(",")[0]
    else:
        client_ip = request.client.host
    return {"client_ip": client_ip}


def make_directory(directory: str):
    """이미지 경로 체크 및 생성

    Args:
        directory (str): 이미지 경로
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def delete_image(directory: str, filename: str, delete: bool = True):
    """이미지 삭제 처리 함수

    Args:
        directory (str): 경로
        filename (str): 파일이름
        delete (bool): 삭제여부. Defaults to True.
    """
    if delete:
        file_path = f"{directory}/{filename}"
        if os.path.exists(file_path):
            os.remove(file_path)


def save_image(directory: str, filename: str, file: UploadFile):
    """이미지 저장 처리 함수

    Args:
        directory (str): 경로
        filename (str): 파일이름
        file (UploadFile): 파일 ojbect
    """
    if file and file.filename:
        with open(f"{directory}/{filename}", "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            

def generate_query_string(request: Request):
    search_fields = {}
    if request.method == "GET":
        search_fields = {
            'sst': request.query_params.get("sst"),
            'sod': request.query_params.get("sod"),
            'sfl': request.query_params.get("sfl"),
            'stx': request.query_params.get("stx"),
            'sca': request.query_params.get("sca"),
            # 'page': request.query_params.get("page")
        }
    else:
        search_fields = {
            'sst': request._form.get("sst") if request._form else "",
            'sod': request._form.get("sod") if request._form else "",
            'sfl': request._form.get("sfl") if request._form else "",
            'stx': request._form.get("stx") if request._form else "",
            'sca': request._form.get("sca") if request._form else "",
            # 'page': request._form.get("page") if request._form else ""
        }    
        
    # None 값을 제거
    search_fields = {k: v for k, v in search_fields.items() if v is not None}

    return urlencode(search_fields)    
            

def query_string(request: Request):
    search_fields = {}
    if request.method == "GET":
        search_fields = {
            'sst': request.query_params.get("sst"),
            'sod': request.query_params.get("sod"),
            'sfl': request.query_params.get("sfl"),
            'stx': request.query_params.get("stx"),
            'sca': request.query_params.get("sca"),
            # 'page': request.query_params.get("page")
        }
    else:
        search_fields = {
            'sst': request._form.get("sst") if request._form else "",
            'sod': request._form.get("sod") if request._form else "",
            'sfl': request._form.get("sfl") if request._form else "",
            'stx': request._form.get("stx") if request._form else "",
            'sca': request._form.get("sca") if request._form else "",
            # 'page': request._form.get("page") if request._form else ""
        }    
        
    # None 값을 제거
    search_fields = {k: v for k, v in search_fields.items() if v is not None}

    return urlencode(search_fields)    

        
# 파이썬의 내장함수인 list 와 이름이 충돌하지 않도록 변수명을 lst 로 변경함
def get_from_list(lst, index, default=0):
    if lst is None:
        return default
    try:
        return 1 if index in lst else default
    except (TypeError, IndexError):
        return default


# 그누보드5 get_paging() 함수와 다른점
# 1. 인수에서 write_pages 삭제
# 2. 인수에서 total_page 대신 total_count 를 사용함

# current_page : 현재 페이지
# total_count : 전체 레코드 수
# add_url : 페이지 링크의 추가 URL
def get_paging(request: Request, current_page, total_count, add_url=""):
    config = request.state.config
    url_prefix = request.url
    
    try:
        current_page = int(current_page)
    except ValueError:
        # current_page가 정수로 변환할 수 없는 경우 기본값으로 1을 사용하도록 설정
        current_page = 1
    total_count = int(total_count)

    # 한 페이지당 라인수
    page_rows = config.cf_mobile_page_rows if request.state.is_mobile and config.cf_mobile_page_rows else config.cf_page_rows
    # 페이지 표시수
    page_count = config.cf_mobile_pages if request.state.is_mobile and config.cf_mobile_pages else config.cf_write_pages
    
    # 올바른 total_pages 계산 (올림처리)
    total_pages = (total_count + page_rows - 1) // page_rows
    
    # print(page_rows, page_count, total_pages)
    
    # 페이지 링크 목록 초기화
    page_links = []
    
    start_page = ((current_page - 1) // page_count) * page_count + 1
    end_page = start_page + page_count - 1

    # # 중앙 페이지 계산
    middle = page_count // 2
    start_page = max(1, current_page - middle)
    end_page = min(total_pages, start_page + page_count - 1)
    
    # 처음 페이지 링크 생성
    if current_page > 1:
        start_url = f"{url_prefix.include_query_params(page=1)}{add_url}"
        page_links.append(f'<a href="{start_url}" class="pg_page pg_start" title="처음 페이지">처음</a>')

    # 이전 페이지 구간 링크 생성
    if start_page > 1:
        prev_page = max(current_page - page_count, 1) 
        prev_url = f"{url_prefix.include_query_params(page=prev_page)}{add_url}"
        page_links.append(f'<a href="{prev_url}" class="pg_page pg_prev" title="이전 구간">이전</a>')

    # 페이지 링크 생성
    for page in range(start_page, end_page + 1):
        page_url = f"{url_prefix.include_query_params(page=page)}{add_url}"
        if page == current_page:
            page_links.append(f'<a href="{page_url}"><strong class="pg_current" title="현재 {page} 페이지">{page}</strong></a>')
        else:
            page_links.append(f'<a href="{page_url}" class="pg_page" title="{page} 페이지">{page}</a>')

    # 다음 페이지 구간 링크 생성
    if total_pages > end_page:
        next_page = min(current_page + page_count, total_pages)
        next_url = f"{url_prefix.include_query_params(page=next_page)}{add_url}"
        page_links.append(f'<a href="{next_url}" class="pg_page pg_next" title="다음 구간">다음</a>')
    
    # 마지막 페이지 링크 생성        
    if current_page < total_pages:
        end_url = f"{url_prefix.include_query_params(page=total_pages)}{add_url}"
        page_links.append(f'<a href="{end_url}" class="pg_page pg_end" title="마지막 페이지">마지막</a>')

    # 페이지 링크 목록을 문자열로 변환하여 반환
    return '<nav class="pg_wrap"><span class="pg">' + ''.join(page_links) + '</span></nav>'


def extract_browser(user_agent):
    # 사용자 에이전트 문자열에서 브라우저 정보 추출
    # 여기에 필요한 정규 표현식 또는 분석 로직을 추가
    # 예를 들어, 단순히 "Mozilla/5.0" 문자열을 추출하는 예제
    browser_match = re.search(r"Mozilla/5.0", user_agent)
    if browser_match:
        return "Mozilla/5.0"
    else:
        return "Unknown"
    
from ua_parser import user_agent_parser    
    

# 접속 레코드 기록 로직을 처리하는 함수
def record_visit(request: Request):
    vi_ip = request.client.host
    
    # 세션 생성
    db = SessionLocal()

    # 오늘의 접속이 이미 기록되어 있는지 확인
    existing_visit = db.query(Visit).filter(Visit.vi_date == date.today(), Visit.vi_ip == vi_ip).first()

    if not existing_visit:
        
        #$tmp_row = sql_fetch(" select max(vi_id) as max_vi_id from {$g5['visit_table']} ");
        tmp_row = db.query(func.max(Visit.vi_id).label("max_vi_id")).first()
        max_vi_id = tmp_row.max_vi_id if tmp_row.max_vi_id else 0
        max_vi_id = max_vi_id + 1
        
        # 새로운 접속 레코드 생성
        referer = request.headers.get("referer", "")
        user_agent = request.headers.get("User-Agent", "")
        ua = parse(user_agent)
        browser = ua.browser.family
        os = ua.os.family
        device = 'pc' if ua.is_pc else 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'unknown'
            
        visit = Visit(
            vi_id=max_vi_id,
            vi_ip=vi_ip,
            vi_date=date.today(),
            vi_time=datetime.now().time(),
            vi_referer=referer,
            vi_agent=user_agent,
            vi_browser=browser,
            vi_os=os,
            vi_device=device,   
        )
        db.add(visit)
        db.commit()

        # VisitSum 테이블 업데이트
        visit_count_today = db.query(func.count(Visit.vi_id)).filter(Visit.vi_date == date.today()).scalar()

        visit_sum = db.query(VisitSum).filter(VisitSum.vs_date == date.today()).first()
        if visit_sum:
            visit_sum.vs_count = visit_count_today
        else:
            visit_sum = VisitSum(vs_date=date.today(), vs_count=visit_count_today)

        db.add(visit_sum)
        db.commit()

    db.close()            
    
    
# 공통 쿼리 파라미터를 받는 함수를 정의합니다.
def common_search_query_params(
        sst: str = Query(default=""), 
        sod: str = Query(default=""), 
        sfl: str = Query(default=""), 
        stx: str = Query(default=""), 
        current_page: str = Query(default="1", alias="page")
        ):
    '''
    공통 쿼리 파라미터를 받는 함수
    '''
    try:
        current_page = int(current_page)
    except ValueError:
        # current_page가 정수로 변환할 수 없는 경우 기본값으로 1을 사용하도록 설정
        current_page = 1
    return {"sst": sst, "sod": sod, "sfl": sfl, "stx": stx, "current_page": current_page}


def select_query(request: Request, table_model, search_params: dict, 
        same_search_fields: Optional[List[str]] = "", # 값이 완전히 같아야지만 필터링 '검색어'
        prefix_search_fields: Optional[List[str]] = "", # 뒤에 %를 붙여서 필터링 '검색어%'
        default_sod: str = "asc",
        # default_sst: Optional[List[str]] = [],
        default_sst: str = "",
    ):
    config = request.state.config
    
    records_per_page = config.cf_page_rows

    db = SessionLocal()
    query = db.query(table_model)
    
    # # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    # if search_params['sst'] is not None and search_params['sst'] != "":
    #     # if search_params['sod'] == "desc":
    #     #     query = query.order_by(desc(getattr(table_model, search_params['sst'])))
    #     # else:
    #     #     query = query.order_by(asc(getattr(table_model, search_params['sst'])))
    #     if search_params.get('sod', default_sod) == "desc":  # 수정된 부분
    #         query = query.order_by(desc(getattr(table_model, search_params['sst'])))
    #     else:
    #         query = query.order_by(asc(getattr(table_model, search_params['sst'])))

    # 'sst' 매개변수가 제공되지 않거나 빈 문자열인 경우, default_sst를 사용합니다.
    sst = search_params.get('sst', default_sst) or default_sst
    
    # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    if sst:
        sod = search_params.get('sod', default_sod) or default_sod
        # sst 가 배열인 경우, 여러 열을 기준으로 정렬을 추가합니다.
        if isinstance(sst, list):
            for sort_attribute in sst:
                sort_column = getattr(table_model, sort_attribute)
                if sod == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(asc(sort_column))
        else:
            if sod == "desc":
                query = query.order_by(desc(getattr(table_model, sst)))
            else:
                query = query.order_by(asc(getattr(table_model, sst)))
        
            
    # sfl과 stx가 제공되면, 해당 열과 값으로 추가 필터링을 합니다.
    if search_params['sfl'] is not None and search_params['stx'] is not None:
        if hasattr(table_model, search_params['sfl']):  # sfl이 Table에 존재하는지 확인
            # if search_params['sfl'] in ["mb_level"]:
            if search_params['sfl'] in same_search_fields:
                query = query.filter(getattr(table_model, search_params['sfl']) == search_params['stx'])
            elif search_params['sfl'] in prefix_search_fields:
                query = query.filter(getattr(table_model, search_params['sfl']).like(f"{search_params['stx']}%"))
            else:
                query = query.filter(getattr(table_model, search_params['sfl']).like(f"%{search_params['stx']}%"))

    # 페이지 번호에 따른 offset 계산
    offset = (search_params['current_page'] - 1) * records_per_page
    # 최종 쿼리 결과를 가져옵니다.
    rows = query.offset(offset).limit(records_per_page).all()
    # # 전체 레코드 개수 계산
    # # total_count = query.count()
    return {
        "rows": rows,
        "total_count": query.count(),
    }
    

# 회원 레코드 얻기    
# fields : 가져올 필드, 예) "mb_id, mb_name, mb_nick"
def get_member(mb_id: str, fields: str = '*'):
    db = SessionLocal()
    return db.query(Member).options(load_only(fields)).filter_by(mb_id=mb_id).first()
    

# 포인트 부여    
def insert_point(request: Request, mb_id: str, point: int, content: str = '', rel_table: str = '', rel_id: str = '', rel_action: str = '', expire: int = 0):
    config = request.state.config
    
    # 포인트를 사용하지 않는다면 종료
    if not config.cf_use_point:
        return 0
    
    # 포인트가 없다면 업데이트를 할 필요가 없으므로 종료
    if point == 0:
        return 0
    
    # 회원아이디가 없다면 종료
    if mb_id == '':
        return 0
    
    # 회원정보가 없다면 종료
    db = SessionLocal()
    
    member = db.query(Member).filter_by(mb_id=mb_id).first()
    if not member:
        return 0
    
    mb_point = get_point_sum(request, mb_id)

    
    if rel_table or rel_id or rel_action:
        record_count = db.query(Point).filter(
            and_(
                Point.mb_id == mb_id,
                Point.po_rel_table == rel_table,
                Point.po_rel_id == rel_id,
                Point.po_rel_action == rel_action
            )
        ).count()
        if record_count:
            return -1
        
    # 포인트 건별 생성
    po_expire_date = '9999-12-31'
    # po_expire_date = datetime.strptime('9999-12-31', '%Y-%m-%d')
    if config.cf_point_term > 0:
        if expire > 0:
            po_expire_date = (SERVER_TIME + timedelta(days=expire-1)).strftime('%Y-%m-%d')
        else:
            po_expire_date = (SERVER_TIME + timedelta(days=config.cf_point_term - 1)).strftime('%Y-%m-%d')
            
    po_expired = 0
    if point < 0:
        po_expired = 1
        po_expire_date = TIME_YMD
    po_mb_point = mb_point + point
    
    new_point = Point(
        mb_id=mb_id,
        po_datetime=TIME_YMDHIS,
        po_content=content,
        po_point=point,
        po_use_point=0,
        po_mb_point=po_mb_point,
        po_expired=po_expired,
        po_expire_date=po_expire_date,
        po_rel_table=rel_table,
        po_rel_id=rel_id,
        po_rel_action=rel_action
    )
    db.add(new_point)
    db.commit()
    
    # filter_by 는 filter 에 비해 기능이 제한적임    
    db.query(Member).filter_by(mb_id=mb_id).update({Member.mb_point: po_mb_point})
    # db.query(Member).filter(Member.mb_id == mb_id).update({Member.mb_point: po_mb_point})
    db.commit()

    return 1


# 소멸 포인트 얻기
def get_expire_point(request: Request, mb_id: str):
    config = request.state.config
    
    if  config.cf_point_term <= 0:
        return 0
    
    db = SessionLocal()
    
    point_sum = db.query(func.sum(Point.po_point - Point.po_use_point)).filter_by(mb_id=mb_id, po_expired=False).filter(Point.po_expire_date < datetime.now()).scalar()
    return point_sum if point_sum else 0


# 포인트 내역 합계
def get_point_sum(request: Request, mb_id: str):
    config = request.state.config
    
    db = SessionLocal()
    
    if config.cf_point_term > 0:
        expire_point = get_expire_point(request, mb_id)
        if expire_point > 0:
            mb = get_member(mb_id, 'mb_point')
            point = expire_point * (-1)
            new_point = Point(
                mb_id=mb_id,
                po_datetime=TIME_YMDHIS,
                po_content='포인트 소멸',
                po_point=expire_point * (-1),
                po_use_point=0,
                po_mb_point=mb.mb_point + point,
                po_expired=1,
                po_expire_date=TIME_YMD,
                po_rel_table='@expire',
                po_rel_id=mb_id,
                po_rel_action='expire-' + str(uuid.uuid4()),
            )   
            db.add(new_point)
            db.commit()
            
            # 포인트를 사용한 경우 포인트 내역에 사용금액 기록
            if point < 0:
                # insert_use_point(mb_id, point)
                pass
        
        # 유효기간이 있을 때 기간이 지난 포인트 expired 체크    
        db.query(Point).filter(
            and_(
                Point.mb_id == mb_id,
                Point.po_expired != 1,
                Point.po_expire_date != '9999-12-31',
                Point.po_expire_date < TIME_YMD
            )
        ).update({Point.po_expired: 1})
        db.commit()            
            
    # 포인트합
    point_sum = db.query(func.sum(Point.po_point)).filter_by(mb_id=mb_id).scalar()
    return point_sum if point_sum else 0


# 사용포인트 입력
def insert_use_point(mb_id: str, point: int, po_id: str = ""):
    global config
    
    point1 = abs(point)
    db = SessionLocal()
    query = db.query(Point).filter_by(mb_id=mb_id, po_expired=False).order_by(Point.po_id.desc())
    query = query(Point.po_id, Point.po_point, Point.po_use_point)\
                .filter(
                    and_(
                        Point.mb_id == mb_id,
                        Point.po_id != po_id,
                        Point.po_expired == 0,
                        Point.po_point > Point.po_use_point
                    )
                )
    if config.cf_point_term:
        query = query.order_by(Point.po_expire_date.asc(), Point.po_id.asc())
    else:
        query = query.order_by(Point.po_id.asc())
    rows = query.all()
    for row in rows:
        point2 = row.po_point
        point3 = row.po_use_point
        
        if (point2 - point3) > point1:
            db.query(Point).filter_by(po_id=row.po_id).update({"po_use_point": (Point.po_use_point + point1)})
            db.commit()
        else:
            point4 = point2 - point3
            db.query(Point).filter_by(po_id=row.po_id).update({"po_use_point": (Point.po_use_point + point4), "po_expired": 100})
            db.commit()
            point1 = point1 - point4


# 포인트 삭제
def delete_point(request: Request, mb_id: str, rel_table: str, rel_id : str, rel_action: str):
    db = SessionLocal()
    result = False
    if rel_table or rel_id or rel_action:
        # 포인트 내역정보    
        row = db.query(Point).filter(Point.mb_id == mb_id, Point.po_rel_table == rel_table, Point.po_rel_id == rel_id, Point.po_rel_action == rel_action).first()
        if row.po_point and row.po_point > 0:
            abs_po_point = abs(row.po_point)
            delete_use_point(request, row.mb_id, abs_po_point)
        else:
            if row.po_use_point and row.po_use_point > 0:
                insert_use_point(request, row.mb_id, row.po_use_point, row.po_id)
                
        db.query(Point).filter(Point.mb_id == mb_id, Point.po_rel_table == rel_table, Point.po_rel_id == rel_id, Point.po_rel_action == rel_action).delete(synchronize_session=False)
        db.commit()

        # po_mb_point에 반영
        if row.po_point:
            db.query(Point).filter(Point.mb_id == mb_id, Point.po_id > row.po_id).update({Point.po_mb_point: Point.po_mb_point - row.po_point}, synchronize_session=False)
            db.commit()
        
        # 포인트 내역의 합을 구하고    
        sum_point = get_point_sum(request, mb_id)
        
        # 포인트 UPDATE
        db.query(Member).filter(Member.mb_id == mb_id).update({Member.mb_point: sum_point}, synchronize_session=False)
        result = db.commit()

    return result


# 사용포인트 삭제
def delete_use_point(request: Request, mb_id: str, point: int):
    config = request.state.config
    db = SessionLocal()
    
    point1 = abs(point)
    rows = db.query(Point).filter(Point.mb_id == mb_id, Point.po_expired != 1, Point.po_use_point > 0).order_by(desc('po_expire_date', 'po_id') if config.cf_point_term else desc('po_id')).all()
    for row in rows:
        point2 = row.po_use_point
        if row.po_expired == 100 and (row.po_expire_date == '9999-12-31' or row.po_expire_date >= TIME_YMD):
            po_expired = 0
        else:
            po_expired = row.po_expired
        
        if point2 > point1:
            db.query(Point).filter(Point.po_id == row.po_id).update({Point.po_use_point: Point.po_use_point - point1, Point.po_expired: po_expired}, synchronize_session=False)
            db.commit()
            break
        else:
            db.query(Point).filter(Point.po_id == row.po_id).update({Point.po_use_point: 0, Point.po_expired: po_expired}, synchronize_session=False)
            db.commit()
            point1 = point1 - point2


# 소멸포인트 삭제
def delete_expire_point(request: Request, mb_id: str, point: int):
    config = request.state.config
    db = SessionLocal()
    
    point1 = abs(point)
    rows = db.query(Point).filter(Point.mb_id == mb_id, Point.po_expired == 1, Point.po_point >= 0, Point.po_use_point > 0).order_by(desc(Point.po_expire_date), desc(Point.po_id)).all()
    for row in rows:
        point2 = row.po_use_point
        po_expired = 0
        po_expire_date = '9999-12-31'
        if config.cf_point_term > 0:
            po_expire_date = (SERVER_TIME + timedelta(days=config.cf_point_term - 1)).strftime('%Y-%m-%d')
    
        if point2 > point1:
            db.query(Point).filter(Point.po_id == row.po_id).update({Point.po_use_point: Point.po_use_point - point1, Point.po_expired: po_expired, Point.po_expire_date: po_expire_date}, synchronize_session=False)
            db.commit()
            break
        else:
            db.query(Point).filter(Point.po_id == row.po_id).update({Point.po_use_point: 0, Point.po_expired: po_expired, Point.po_expire_date: po_expire_date}, synchronize_session=False)
            db.commit()
            point1 = point1 - point2


def domain_mail_host(request: Request, is_at: bool = True):
    domain_host = request.base_url.hostname
    
    if domain_host.startswith("www."):
        domain_host = domain_host[4:]
    
    return f"@{domain_host}" if is_at else domain_host
        

def get_memo_not_read(mb_id: str):
    '''
    메모를 읽지 않은 개수를 반환하는 함수
    '''
    db = SessionLocal()
    return db.query(Memo).filter(Memo.me_recv_mb_id == mb_id, Memo.me_read_datetime == None, Memo.me_type == 'recv').count()


def editor_path(request:Request) -> str:
    """지정한 에디터 경로를 반환하는 함수
    미지정시 그누보드 환경설정값 사용
    request.state.editor: 에디터이름
    request.state.use_editor: 에디터 사용여부 False 이면 'textarea' 반환
    """
    if not request.state.use_editor:
        return "textarea"

    editor_name = request.state.editor
    if not editor_name:
        return "textarea"

    return editor_name


def nl2br(value) -> str:
    """ \n 을 <br> 태그로 변환
    """
    return escape(value).replace('\n', Markup('<br>\n'))


popular_cache = cachetools.TTLCache(maxsize=10, ttl=300)

def get_populars(limit: int = 7, day: int = 3):
    """인기검색어 조회

    Args:
        limit (int, optional): 조회 갯수. Defaults to 7.
        day (int, optional): 오늘부터 {day}일 전. Defaults to 3.

    Returns:
        List[Popular]: 인기검색어 리스트
    """
    if popular_cache.get("populars"):
        return popular_cache.get("populars")

    db = SessionLocal()
    # 현재 날짜와 day일 전 날짜를 구한다.
    today = datetime.now()
    before = today - timedelta(days=day)
    # 현재 날짜와 day일 전 날짜 사이의 인기검색어를 조회한다.
    populars = db.query(
            Popular.pp_word,
            func.count(Popular.pp_word).label('count'),
        ).filter(
        Popular.pp_word != '',
        Popular.pp_date >= before,
        Popular.pp_date <= today
    ).group_by(Popular.pp_word).order_by(desc('count'), Popular.pp_word).limit(limit).all()
    db.close()

    popular_cache.update({"populars": populars})

    return populars


def generate_token(request: Request, action: str = ''):
    '''
    토큰 생성 함수

    Returns:
        str: 생성된 토큰
    '''
    # token = str(uuid.uuid4())  # 임의의 유일한 키 생성
    token = hash_password(action)
    request.session["ss_token"] = token
    return token


def compare_token(request: Request, token: str, action: str = ''):
    '''
    토큰 비교 함수

    Args:
        token (str): 비교할 토큰

    Returns:
        bool: 토큰이 일치하면 True, 일치하지 않으면 False
    '''
    if request.session.get("ss_token") == token and token:
        return verify_password(action, token)
    else:
        return False


lfu_cache = cachetools.LFUCache(maxsize=128)

def get_recent_poll():
    """
    최근 투표 정보 1건을 가져오는 함수
    """
    if lfu_cache.get("poll"):
        return lfu_cache.get("poll")

    db = SessionLocal()
    poll = db.query(Poll).filter(Poll.po_use == 1).order_by(Poll.po_id.desc()).first()
    db.close()

    lfu_cache.update({"poll": poll})

    return poll


def get_menus():
    """사용자페이지 메뉴 조회 함수

    Returns:
        list: 자식메뉴가 포함된 메뉴 list
    """
    if lfu_cache.get("menus"):
        return lfu_cache.get("menus")

    db = SessionLocal()
    menus = []
    # 부모메뉴 조회
    parent_menus = db.query(Menu).filter(func.length(Menu.me_code) == 2).order_by(Menu.me_order).all()
    
    for menu in parent_menus:
        parent_code = menu.me_code

        # 자식 메뉴 조회
        child_menus = db.query(Menu).filter(
            func.length(Menu.me_code) == 4,
            func.substring(Menu.me_code, 1, 2) == parent_code
        ).order_by(Menu.me_order).all()

        menu.sub = child_menus
        menus.append(menu)

    lfu_cache.update({"menus": menus})

    return menus


def get_member_level(request: Request):
    """
    request에서 회원 레벨 정보를 가져오는 함수
    """
    member = request.state.login_member

    return member.mb_level if member else 1


def auth_check_menu(request: Request, menu_key: str, attribute: str):
    '''
    관리권한 체크
    '''    
    # 최고관리자이면 처리 안함
    if request.state.is_super_admin:
        return ""

    db = SessionLocal()

    exists_member = request.state.login_member
    if not exists_member:
        return "로그인 후 이용해 주세요."

    exists_auth = db.query(Auth).filter_by(mb_id=exists_member.mb_id, au_menu=menu_key).first()
    if not exists_auth:
        return "이 메뉴에는 접근 권한이 없습니다.\\n\\n접근 권한은 최고관리자만 부여할 수 있습니다."

    auth_set = set(exists_auth.au_auth.split(","))
    if not attribute in auth_set:
        if attribute == "r":
            error = "읽을 권한이 없습니다."
        elif attribute == "w":
            error = "입력, 추가, 생성, 수정 권한이 없습니다."
        elif attribute == "d":
            error = "삭제 권한이 없습니다."
        else:
            error = f"속성(attribute={attribute})이 잘못 되었습니다."
        return error

    return ""


def get_unique_id(request) -> Optional[str]:
    """고유키 생성 함수
    그누보드 5의 get_uniqid

    년월일시분초00 ~ 년월일시분초99
    년(4) 월(2) 일(2) 시(2) 분(2) 초(2) 100만분의 1초(2)
    Args:
        request (Request): FastAPI Request 객체
    Returns:
        Optional[str]: 고유 아이디, DB 오류시 None
    """

    ip: str = get_client_ip(request)["client_ip"]

    while True:
        current = datetime.now()
        ten_milli_sec = str(current.microsecond)[:2].zfill(2)
        key = f"{current.strftime('%Y%m%d%H%M%S')}{ten_milli_sec}"

        with SessionLocal() as session:
            try:
                session.add(UniqId(uq_id=key, uq_ip=ip))
                session.commit()
                return key

            except IntegrityError:
                # key 중복 에러가 발생하면 다시 시도
                session.rollback()
                sleep(random.uniform(0.01, 0.02))
            except Exception as e:
                logging.log(logging.CRITICAL, 'unique table insert error', exc_info=e)
                return None


class AlertException(HTTPException):
    """스크립트 경고창 출력을 위한 예외 클래스
        - HTTPExceptiond에서 페이지 이동을 위한 url 매개변수를 추가적으로 받는다.

    Args:
        HTTPException (HTTPException): HTTP 예외 클래스
    """
    def __init__(self, detail: str = None, status_code: int = 200, url: str = None):
        self.status_code = status_code
        self.detail = detail
        self.url = url


class AlertCloseException(HTTPException):
    """스크립트 경고창 출력 및 윈도우 창 닫기를 위한 예외 클래스

    Args:
        HTTPException (HTTPException): HTTP 예외 클래스
    """
    def __init__(
        self,
        detail: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers) 


def is_admin(request: Request):
    """관리자 여부 확인
    """
    config = request.state.config
    if config.cf_admin.strip() == "":
        return False

    if mb_id := request.session.get("ss_mb_id", ""):
        if mb_id.strip() == config.cf_admin.strip():
            return True

    return False


def check_profile_open(open_date, config) -> bool:
    """변경일이 지나서 프로필 공개가능 여부를 반환
    Args:
        open_date (datetime): 프로필 공개일
        config (Config): config 모델
    Returns:
        bool: 프로필 공개 가능 여부
    """
    if not open_date:
        return True

    else:
        return open_date < (datetime.now() - timedelta(days=config.cf_open_modify))


def get_next_profile_openable_date(open_date: datetime, config):
    """다음 프로필 공개 가능일을 반환
    Args:
        open_date (datetime): 프로필 공개일
        config (Config): config 모델
    Returns:
        datetime: 다음 프로필 공개 가능일
    """
    cf_open_modify = config.cf_open_modify

    if open_date:
        calculated_date = datetime.strptime(open_date, "%Y-%m-%d") + timedelta(days=cf_open_modify)
    else:
        calculated_date = datetime.now() + timedelta(days=cf_open_modify)

    return calculated_date


def default_if_none(value, arg):
    """If value is None"""
    if value is None:
        return arg
    return value


def valid_email(email: str):
    # Define a basic email address regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    # Use the regex pattern to match the email address
    if re.match(pattern, email):
        return True

    return False


def upload_file(upload_object, filename, path, chunck_size: int = None):
    """폼 파일 업로드
    Args:
        upload_object : form 업로드할 파일객체
        filename (str): 확장자 포함 저장할 파일명 (with ext)
        path (str): 저장할 경로
        chunck_size (int, optional): 파일 저장 단위. 기본값 1MB 로 지정
    Returns:
        str: 저장된 파일명
    """
    # 파일 저장 경로 생성
    os.makedirs(path, exist_ok=True)

    # 파일 저장 경로
    save_path = os.path.join(path, filename)
    # 파일 저장
    if chunck_size is None:
        chunck_size = 1024 * 1024
        with open(f"{save_path}", "wb") as buffer:
            shutil.copyfileobj(upload_object.file, buffer, chunck_size)
    else:
        with open(f"{save_path}", "wb") as buffer:
            shutil.copyfileobj(upload_object.file, buffer)


def get_filetime_str(file_path) -> Union[int, str]:
    """파일의 변경시간
    Args:
        file_path (str): 파일 이름포함 경로
    Returns:
        Union[int, str]: 파일 변경시간, 파일없을시 빈문자열
    """
    try:
        file_time = os.path.getmtime(file_path)
        return int(file_time)
    except FileNotFoundError:
        return ''


class StringEncrypt:
    def __init__(self, salt=''):
        if not salt:
            # You might want to implement your own salt generation logic here
            self.salt = "your_default_salt"
        else:
            self.salt = salt
        
        self.length = len(self.salt)

    def encrypt(self, str_):
        length = len(str_)
        result = ''

        for i in range(length):
            char = str_[i]
            keychar = self.salt[i % self.length]
            char = chr(ord(char) + ord(keychar))
            result += char

        result = base64.b64encode(result.encode()).decode()
        result = result.translate(str.maketrans('+/=', '._-'))

        return result

    def decrypt(self, str_):
        result = ''
        str_ = str_.translate(str.maketrans('._-', '+/='))
        str_ = base64.b64decode(str_).decode()

        length = len(str_)

        for i in range(length):
            char = str_[i]
            keychar = self.salt[i % self.length]
            char = chr(ord(char) - ord(keychar))
            result += char

        return result

# 사용 예
# enc = StringEncrypt()
# encrypted_text = enc.encrypt("hello")
# print(encrypted_text)

# decrypted_text = enc.decrypt(encrypted_text)
# print(decrypted_text)


class MyTemplates(Jinja2Templates):
    """
    Jinja2Template 설정 클래스
    """
    def __init__(self,
                 directory: Union[str, os.PathLike],
                 context_processors: dict = None,
                 globals: dict = None,
                 **env_options: Any,
                 ):
        super().__init__(directory, context_processors, **env_options)
        # 공통 env.global 설정
        self.env.globals["editor_path"] = editor_path
        self.env.globals["generate_token"] = generate_token
        self.env.globals["getattr"] = getattr
        self.env.globals["get_selected"] = get_selected

        # 사용자 템플릿, 관리자 템플릿에 따라 기본 컨텍스트와 env.global 변수를 다르게 설정
        if TEMPLATES_DIR in directory:
            self.context_processors.append(self._default_context)
        elif ADMIN_TEMPLATES_DIR in directory:
            self.context_processors.append(self._default_admin_context)

        # 추가 env.global 설정
        if globals:
            self.env.globals.update(**globals.__dict__)

    def _default_context(self, request: Request):
        # 메인페이지(main.py) latest 함수에서 templates.TemplateResponse가 추가적으로 호출되기 때문에
        # context_processors가 2번 호출된다.
        context = {
            "menus" : get_menus(),
            "poll" : get_recent_poll(),
            "populars" : get_populars(),
        }
        return context
    
    def _default_admin_context(self, request: Request):
        context = {
            "admin_menus": get_admin_menus()
        }
        return context
    

class G6FileCache():
    """파일 캐시 클래스
    """
    cache_dir = os.path.join("data", "cache")
    cache_secret_key = None

    def __init__(self):
        # 캐시 디렉토리가 없으면 생성
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
    def get_cache_secret_key(self):
        """
        캐시 비밀키를 반환하는 함수
        """
        # 캐시된 값이 있다면, 해당 값을 반환
        if self.cache_secret_key:
            return self.cache_secret_key

        # 서버 소프트웨어 및 DOCUMENT_ROOT 값을 해싱하여 6자리 문자열 생성
        server_software = os.environ.get("SERVER_SOFTWARE", "")
        document_root = os.environ.get("DOCUMENT_ROOT", "")
        combined_data = server_software + document_root
        self.cache_secret_key = hashlib.md5(combined_data.encode()).hexdigest()[:6]

        return self.cache_secret_key
    
    def get(self, cache_file: str):
        """
        캐시된 파일이 있으면 파일을 읽어서 반환
        """
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def create(self, data: str, cache_file: str):
        """
        cache_file을 생성하는 함수
        """
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(data)

    def delete(self, cache_file: str):
        """
        cache_file을 삭제하는 함수
        """
        if os.path.exists(cache_file):
            os.remove(cache_file)

    def delete_prefix(self, prefix: str):
        """
        prefix로 시작하는 캐시 파일을 모두 삭제하는 함수
        """
        for file in os.listdir(self.cache_dir):
            if file.startswith(prefix):
                os.remove(os.path.join(self.cache_dir, file))


SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# 메일 발송
# return 은 수정 필요
def mailer(email: str, subject: str, content: str):
    to_emails = email.split(',') if ',' in email else [email]
    for to_email in to_emails:
        try:
            msg = MIMEMultipart()
            msg['From'] = SMTP_USERNAME
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Assuming body is HTML, if not change 'html' to 'plain'
            msg.attach(MIMEText(content, 'html'))  

            with smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT)) as server:
                if SMTP_USERNAME and SMTP_PASSWORD:
                    server.starttls()
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                text = msg.as_string()
                server.sendmail(SMTP_USERNAME, to_email, text)

        except Exception as e:
            print(f"Error sending email to {to_email}: {e}")

    return {"message": f"Emails sent successfully to {', '.join(to_emails)}"}                                
               
                




def latest(request: Request, skin_dir='', bo_table='', rows=10, subject_len=40):
    """최신글 목록 HTML 출력

    Args:
        request (Request): _description_
        skin_dir (str, optional): 스킨 경로. Defaults to ''.
        bo_table (str, optional): 게시판 코드. Defaults to ''.
        rows (int, optional): 노출 게시글 수. Defaults to 10.
        subject_len (int, optional): 제목길이 제한. Defaults to 40.

    Returns:
        str: 최신글 HTML
    """
    templates = MyTemplates(directory=TEMPLATES_DIR)

    if not skin_dir:
        skin_dir = 'basic'

    g6_file_cache = G6FileCache()
    cache_filename = f"latest-{bo_table}-{skin_dir}-{rows}-{subject_len}-{g6_file_cache.get_cache_secret_key()}.html"
    cache_file = os.path.join(g6_file_cache.cache_dir, cache_filename)

    # 캐시된 파일이 있으면 파일을 읽어서 반환
    if os.path.exists(cache_file):
        return g6_file_cache.get(cache_file)
    
    db = SessionLocal()
    board = db.query(Board).filter(Board.bo_table == bo_table).first()
    
    Write = dynamic_create_write_table(bo_table)
    writes = db.query(Write).filter(Write.wr_is_comment == False).order_by(Write.wr_num).limit(rows).all()
    for write in writes:
        write.is_notice = write.wr_id in board.bo_notice.split(",")
        write.subject = write.wr_subject[:subject_len]
        write.icon_hot = write.wr_hit >= 100
        write.icon_new = write.wr_datetime > (datetime.now() - timedelta(days=1))
        write.icon_file = write.wr_file
        write.icon_link = write.wr_link1 or write.wr_link2
        write.icon_reply = write.wr_reply
        write.datetime = write.wr_datetime.strftime("%y-%m-%d")
    
    context = {
        "request": request,
        "writes": writes,
        "bo_table": bo_table,
        "bo_subject": board.bo_subject,
    }
    temp = templates.TemplateResponse(f"latest/{skin_dir}.html", context)
    temp_decode = temp.body.decode("utf-8")

    # 캐시 파일 생성
    g6_file_cache.create(temp_decode, cache_file)

    return temp_decode


def get_newwins(request: Request):
    """
    레이어 팝업 목록 조회
    """
    db = SessionLocal()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_division = "comm" # comm, both, shop
    newwins = db.query(NewWin).filter(
        NewWin.nw_begin_time <= now,
        NewWin.nw_end_time >= now,
        NewWin.nw_device.in_(["both", request.state.device]),
        NewWin.nw_division.in_(["both", current_division]),
    ).order_by(NewWin.nw_id.asc()).all()

    # "hd_pops_" + nw_id 이름으로 선언된 쿠키가 있는지 확인하고 있다면 팝업을 제거
    newwins = [newwin for newwin in newwins if not request.cookies.get("hd_pops_" + str(newwin.nw_id))]

    return newwins


def datetime_format(date: datetime, format="%Y-%m-%d %H:%M:%S"):
    """
    날짜 포맷팅
    """
    if not date:
        return ""

    return date.strftime(format)