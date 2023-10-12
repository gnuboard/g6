import hashlib
import os
import PIL
from fastapi import Request
from passlib.context import CryptContext
from sqlalchemy import Index
import models
from models import WriteBaseModel
from database import SessionLocal, engine
from datetime import datetime
import json
from PIL import Image

TEMPLATES_DIR = "templates/basic"
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


def session_member_key(request: Request, member: models.Member):
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


# 필드에 저장된 값과 기본 값을 비교하여 selected 를 반환
def get_selected(field_value, value):
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
    groups = db.query(models.Group).order_by(models.Group.gr_id).all()
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
    action : 'create', 'update', 'delete' ...
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