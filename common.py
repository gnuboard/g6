import hashlib
import os
import re
import shutil
from typing import Union

import PIL
from fastapi import Request
from passlib.context import CryptContext
from sqlalchemy import Index
import models
from models import WriteBaseModel
from database import SessionLocal, engine
from datetime import datetime, timedelta
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
    return request.client.host


def session_member_key(request: Request, member: models.Member):
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
    


def subject_sort_link(request: Request, col, query_string='', flag='asc'):
    sst = request.state.sst if request.state.sst is not None else ""
    sod = request.state.sod if request.state.sod is not None else ""
    sfl = request.state.sfl if request.state.sfl is not None else ""
    stx = request.state.stx if request.state.stx is not None else ""
    sca = request.state.sca if request.state.sca is not None else ""
    page = request.state.page if request.state.page is not None else "" 
    
    q1 = f"sst={col}"

    if flag == 'asc':
        q2 = 'sod=asc'
        if sst == col:
            if sod == 'asc':
                q2 = 'sod=desc'
    else:
        q2 = 'sod=desc'
        if sst == col:
            if sod == 'desc':
                q2 = 'sod=asc'

    arr_query = []
    arr_query.append(query_string)
    arr_query.append(q1)
    arr_query.append(q2)

    if sfl is not None:
        arr_query.append(f'sfl={sfl}')
    if stx is not None:
        arr_query.append(f'stx={stx}')
    if sca is not None:
        arr_query.append(f'sca={sca}')
    if page is not None:
        arr_query.append(f'page={page}')

    qstr = '&'.join(arr_query[1:]) if arr_query else ''
    # 여기에서 URL 인코딩을 수행합니다.
    
# |이 코드는 주어진 문자열을 파싱하여 URL 쿼리 문자열을 인코딩하는 기능을 수행합니다.
# |
# |좋은 점:
# |- 딕셔너리 컴프리헨션을 사용하여 간결하고 효율적인 코드를 작성했습니다.
# |- 문자열을 '&'로 분리하고, '='로 분리한 후, '='이 포함된 항목들만 딕셔너리에 추가하여 필터링합니다.
# |- urlencode 함수를 사용하여 딕셔너리를 URL 쿼리 문자열로 인코딩합니다.
# |
# |나쁜 점:
# |- 코드의 가독성이 좋지 않습니다. 한 줄에 모든 작업을 포함하고 있어 이해하기 어려울 수 있습니다.
# |- 변수 이름이 약어로 되어 있어 의미를 파악하기 어렵습니다. 변수 이름을 더 명확하게 작성하는 것이 좋습니다.
# |- 코드에 주석이 없어서 코드의 목적과 동작을 이해하기 어렵습니다. 주석을 추가하여 코드를 설명하는 것이 좋습니다.
# |
# |이 코드를 개선하기 위해서는 가독성을 높이고 코드의 목적을 명확히 전달할 수 있도록 변수 이름을 개선하고, 주석을 추가하는 것이 좋습니다. 또한, 코드를 여러 줄로 나누어 가독성을 향상시킬 수 있습니다.
    # qstr = urlencode({k: v for k, v in [x.split('=') for x in qstr.split('&')] if '=' in x})
    # '&' 문자로 분리
    pairs = qstr.split('&')

    # 빈 딕셔너리 생성
    params = {}

    # 각 쌍을 순회
    for pair in pairs:
        # '=' 문자가 있는지 확인
        if '=' in pair:
            # '=' 문자로 분리하여 key와 value 추출
            key, value = pair.split('=')
            
            # value가 'None'이거나 빈 문자열인 경우 제외
            if value != '':
                # 딕셔너리에 추가
                params[key] = value

    # 딕셔너리를 URL 인코딩
    # qstr_encoded = urlencode(params)

    # short_url_clean, get_params_merge_url 함수는 구현에 따라 다릅니다.
    # url = short_url_clean(get_params_merge_url(qstr_array))

    # URL을 반환합니다.
    return f'<a href="?{qstr}">'


# 함수 테스트
# print(subject_sort_link('title', query_string='type=list', flag='asc', sst='title', sod='asc', sfl='category', stx='example', page=2))


def get_admin_menus():
    '''
    관리자 메뉴를 1, 2단계로 분류하여 반환하는 함수
    '''
    with open("_admin/admin_menu.json", "r", encoding="utf-8") as file:
        menus = json.load(file)
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
kv_cache = cachetools.Cache(maxsize=1)

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


def is_admin(request: Request):
    """관리자 여부 확인
    """
    config = get_config()
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
        config (models.Config): config 모델
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
        config (models.Config): config 모델
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


def get_config():
    """그누보드 config 를 반환.
    """
    if config_cache := kv_cache.get('gnu_config'):
        return config_cache

    db = SessionLocal()
    config = db.query(models.Config).first()
    db.close()
    kv_cache.__setitem__('gnu_config', config)

    return config


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
