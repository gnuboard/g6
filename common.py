import hashlib
import os
import re
from typing import List, Optional
import uuid
import PIL
import shutil
from fastapi import Query, Request, HTTPException, UploadFile
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from passlib.context import CryptContext
from sqlalchemy import Index, asc, desc, and_, or_, func, extract
from sqlalchemy.orm import load_only, Session
from models import Config, Member, Board, Group, Point, Visit, VisitSum
from models import WriteBaseModel
from database import SessionLocal, engine
from datetime import datetime, timedelta, date, time
import json
from PIL import Image
from user_agents import parse

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

TEMPLATES_DIR = get_theme_from_db()
# print(TEMPLATES_DIR)
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
    인수의 table_name 에서는 g6_write_ 를 제외한 테이블 이름만 입력받는다.
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
            "__tablename__": "g6_write_" + table_name,
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
    return request.remote_addr    


def session_member_key(request: Request, member: Member):
    '''
    세션에 저장할 회원의 고유키를 생성하여 반환하는 함수
    '''
    ss_mb_key = hashlib.md5((member.mb_datetime + get_real_client_ip(request) + request.headers.get('User-Agent')).encode()).hexdigest()
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
    # 테이블에서 지정된 필드만 가져 오는 경우 load_only("field1", "field2") 함수를 사용 
    members = db.query(Member).options(load_only("mb_id")).filter(Member.mb_level >= level).all()
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {event}><option value="">선택하세요</option>')
    for member in members:
        html_code.append(f'<option value="{member.mb_id}" {"selected" if member.mb_id == selected else ""}>{member.mb_id}</option>')
    html_code.append('</select>')
    return ''.join(html_code)


# 필드에 저장된 값과 기본 값을 비교하여 selected 를 반환
def get_selected(field_value, value):
    if field_value is None:
        return ''

    if isinstance(value, int):
        return ' selected="selected"' if (int(field_value) == int(value)) else ''
    return ' selected="selected"' if (field_value == value) else ''


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
    
    
from urllib.parse import urlencode


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


def validate_token_or_raise(token: str = None):
    """토큰을 검증하고 예외를 발생시키는 함수"""
    if not validate_one_time_token(token):
        raise HTTPException(status_code=403, detail="Invalid token.")


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
        file_path = f"{directory}{filename}"
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
        with open(f"{directory}{filename}", "wb") as buffer:
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
# url_prefix : 페이지 링크의 URL 접두사
# add_url : 페이지 링크의 추가 URL
def get_paging(request, current_page, total_count, url_prefix, add_url=""):
    config = request.state.config
    
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
        start_url = f"{url_prefix}1{add_url}"
        page_links.append(f'<a href="{start_url}" class="pg_page pg_start" title="처음 페이지">처음</a>')

    # 이전 페이지 구간 링크 생성
    if start_page > 1:
        prev_page = max(current_page - page_count, 1) 
        prev_url = f"{url_prefix}{prev_page}{add_url}"
        page_links.append(f'<a href="{prev_url}" class="pg_page pg_prev" title="이전 구간">이전</a>')

    # 페이지 링크 생성
    for page in range(start_page, end_page + 1):
        page_url = f"{url_prefix}{page}{add_url}"
        if page == current_page:
            page_links.append(f'<a href="{page_url}"><strong class="pg_current" title="현재 {page} 페이지">{page}</strong></a>')
        else:
            page_links.append(f'<a href="{page_url}" class="pg_page" title="{page} 페이지">{page}</a>')

    # 다음 페이지 구간 링크 생성
    if total_pages > end_page:
        next_page = min(current_page + page_count, total_pages)
        next_url = f"{url_prefix}{next_page}{add_url}"
        page_links.append(f'<a href="{next_url}" class="pg_page pg_next" title="다음 구간">다음</a>')
    
    # 마지막 페이지 링크 생성        
    if current_page < total_pages:
        end_url = f"{url_prefix}{total_pages}{add_url}"
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
        # 새로운 접속 레코드 생성
        referer = request.headers.get("referer", "")
        user_agent = request.headers.get("User-Agent", "")
        ua = parse(user_agent)
        browser = ua.browser.family
        os = ua.os.family
        device = 'pc' if ua.is_pc else 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'unknown'
            
        visit = Visit(
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
            


def get_editor_path(editor_name: Optional[str] = None) -> str:
    """지정한 에디터 경로를 반환하는 함수
    미지정시 그누보드 환경설정값 사용
    """
    if editor_name:
        return editor_name

    db = SessionLocal()
    config = db.query(Config).first()
    db.close()
    return config.cf_editor if config.cf_editor else "textarea"


def nl2br(value) -> str:
    """ \n 을 <br> 태그로 변환
    """
    return escape(value).replace('\n', Markup('<br>\n'))
