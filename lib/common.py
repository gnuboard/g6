import base64
import hashlib
import json
import logging
import math
import os
import random
import re
import shutil
from datetime import date, datetime, timedelta
from time import sleep
from typing import Any, List, Optional, Union

import httpx
from dotenv import load_dotenv
from fastapi import Request, UploadFile
from markupsafe import Markup, escape
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import (
    Index, asc, cast, delete, desc, func, select, String, DateTime
)
from sqlalchemy.exc import IntegrityError
from starlette.datastructures import URL

from core.database import DBConnect, db_session, MySQLCharsetMixin
from core.models import (
    BoardNew, Config, Member, Memo, UniqId, Visit, WriteBaseModel
)
from core.plugin import get_admin_menu_id_by_path

load_dotenv()

# 전역변수 선언(global variables)
CAPTCHA_PATH = "lib/captcha/templates"
EDITOR_PATH = "lib/editor/templates"


# 동적 모델 캐싱: 모델이 이미 생성되었는지 확인하고, 생성되지 않았을 경우에만 새로 생성하는 방법입니다.
# 이를 위해 간단한 전역 딕셔너리를 사용하여 이미 생성된 모델을 추적할 수 있습니다.
_created_models = {}

# 동적 게시판 모델 생성
def dynamic_create_write_table(
        table_name: str,
        create_table: bool = False,
    ) -> WriteBaseModel:
    '''
    WriteBaseModel 로 부터 게시판 테이블 구조를 복사하여 동적 모델로 생성하는 함수
    인수의 table_name 에서는 table_prefix + 'write_' 를 제외한 테이블 이름만 입력받는다.
    Create Dynamic Write Table Model from WriteBaseModel
    '''
    # 이미 생성된 모델 반환
    if table_name in _created_models:
        return _created_models[table_name]

    if isinstance(table_name, int):
        table_name = str(table_name)

    class_name = "Write" + table_name.capitalize()
    db_connect = DBConnect()
    DynamicModel = type(
        class_name,
        (WriteBaseModel,),
        {
            "__tablename__": db_connect.table_prefix + 'write_' + table_name,
            "__table_args__": (
                Index(f'idx_wr_num_reply_{table_name}', 'wr_num', 'wr_reply'),
                Index(f'idex_wr_is_comment_{table_name}', 'wr_is_comment'),
                {
                    "extend_existing": True,
                    **MySQLCharsetMixin().__table_args__
                },
            ),
        }
    )
    # 게시판 추가시 한번만 테이블 생성
    if create_table:
        DynamicModel.__table__.create(bind=db_connect.engine, checkfirst=True)
    # 생성된 모델 캐싱
    _created_models[table_name] = DynamicModel
    return DynamicModel


def session_member_key(request: Request, member: Member):
    '''
    세션에 저장할 회원의 고유키를 생성하여 반환하는 함수
    '''
    ss_mb_key = hashlib.md5(
        (member.mb_datetime.strftime(format="%Y-%m-%d %H:%M:%S")
         + get_client_ip(request)
         + request.headers.get('User-Agent')).encode()).hexdigest()
    return ss_mb_key


def get_admin_menus():
    '''
    1, 2단계로 구분된 관리자 메뉴 json 파일이 있으면 load 하여 반환하는 함수
    '''
    files = [
        "admin/admin_menu_bbs.json",
        "admin/admin_menu_shop.json",
        "admin/admin_menu_sms.json"
    ]
    menus = {}
    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                menus.update(json.load(file))
    return menus


def get_head_tail_img(directory: str, filename: str, width: int = 750) -> dict:
    """
    디렉토리/파일 이름에 해당하는 이미지를 찾아,
    해당 이미지가 존재하는 경우 이미지의 URL과 너비를 반환합니다.
    - 이미지 너비는 기본적으로 최대 750px로 제한됩니다.

    Args:
        directory (str): 이미지 디렉토리
        filename (str): 이미지 파일 이름

    Returns:
        dict: 이미지 존재 여부, 이미지 URL, 이미지 너비
        
    """
    img_path = os.path.join('data', directory, filename)
    img_exists = os.path.exists(img_path)
    img_width = 0

    if img_exists:
        try:
            with Image.open(img_path) as img_file:
                img_width = min(img_file.width, width)  # 이미지 너비를 750px로 제한
        except UnidentifiedImageError:
            print(f"Error: Cannot identify image file '{img_path}'")
            img_exists = False

    return {
        "exists": img_exists,
        "url": f"/{img_path}" if img_exists else "",
        "width": img_width
    }


def get_client_ip(request: Request) -> str:
    '''
    클라이언트의 IP 주소를 반환하는 함수 (PHP의 $_SERVER['REMOTE_ADDR'])
    '''
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # X-Forwarded-For can be a comma-separated list of IPs.
        # The client's requested IP will be the first one.
        return x_forwarded_for.split(",")[0]
    else:
        return request.client.host


async def get_host_public_ip() -> str:
    """
    호스트의 공인 IP 주소를 반환하는 함수
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get('https://httpbin.org/ip')
            return response.json()['origin']
        except httpx.TimeoutException:
            return "IP 정보를 불러오지 못했습니다. 다시 시도해주세요."


def delete_image(directory: str, filename: str, is_delete: bool = True):
    """이미지 삭제 처리 함수

    Args:
        directory (str): 경로
        filename (str): 파일이름
        is_delete (bool): 삭제여부. Defaults to True.
    """
    if is_delete:
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


# 파이썬의 내장함수인 list 와 이름이 충돌하지 않도록 변수명을 lst 로 변경함
def get_from_list(lst, index, default=0):
    if lst is None:
        return default
    try:
        return 1 if index in lst else default
    except (TypeError, IndexError):
        return default


def select_query(request: Request, db: db_session, table_model, search_params: dict,
        same_search_fields: Optional[List[str]] = "", # 값이 완전히 같아야지만 필터링 '검색어'
        prefix_search_fields: Optional[List[str]] = "", # 뒤에 %를 붙여서 필터링 '검색어%'
        default_sod: str = "asc",
        # default_sst: Optional[List[str]] = [],
        default_sst: str = "",
    ):
    config = request.state.config
    records_per_page = config.cf_page_rows

    query = select()
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
    sod = search_params.get('sod', default_sod) or default_sod

    if sst:
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
                query = query.where(getattr(table_model, search_params['sfl']) == search_params['stx'])
            elif search_params['sfl'] in prefix_search_fields:
                query = query.where(getattr(table_model, search_params['sfl']).like(f"{search_params['stx']}%"))
            else:
                query = query.where(cast(getattr(table_model, search_params['sfl']), String).like(f"%{search_params['stx']}%"))

    # 페이지 번호에 따른 offset 계산
    page = search_params['current_page']
    offset = (page - 1) * records_per_page if page > 0 else 0
    # 최종 쿼리 결과를 가져옵니다.
    rows = db.scalars(query.add_columns(table_model).offset(offset).limit(records_per_page)).all()
    # 전체 레코드 개수 계산
    total_count = db.scalar(query.add_columns(func.count()).select_from(table_model).order_by(None))

    return {
        "rows": rows,
        "total_count": total_count,
    }


def domain_mail_host(request: Request, is_at: bool = True):
    domain_host = request.base_url.hostname

    if domain_host.startswith("www."):
        domain_host = domain_host[4:]

    return f"@{domain_host}" if is_at else domain_host


def nl2br(value) -> str:
    """ \n 을 <br> 태그로 변환
    """
    return escape(value).replace('\n', Markup('<br>\n'))


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

    ip: str = get_client_ip(request)

    while True:
        current = datetime.now()
        ten_milli_sec = str(current.microsecond)[:2].zfill(2)
        key = f"{current.strftime('%Y%m%d%H%M%S')}{ten_milli_sec}"

        with DBConnect().sessionLocal() as session:
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

class FileCache():
    """파일 캐시 클래스
    """
    cache_dir = os.path.join("data", "cache")
    cache_secret_key = None

    def __init__(self):
        # 캐시 디렉토리가 없으면 생성
        os.makedirs(self.cache_dir, exist_ok=True)

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


def get_admin_email(request: Request):
    """관리자 이메일 주소를 반환하는 함수

    Args:
        request (Request): Request 객체

    Returns:
        str: 환경설정에서 설정된 관리자 이메일 주소
    """
    return getattr(request.state.config, "cf_admin_email", "")


def get_admin_email_name(request: Request):
    """관리자 이메일 발송이름을 반환하는 함수

    Args:
        request (Request): Request 객체

    Returns:
        str: 환경설정에서 설정된 관리자 이메일 주소
    """
    return getattr(request.state.config, "cf_admin_email_name", "")


def is_none_datetime(input_date: Union[date, str]) -> bool:
    """date, datetime 이 0001, 0000 등 유효하지 않은 날짜인지 확인하는 함수
    0001, mysql 5.7이하 0000,
    """
    if isinstance(input_date, str):  # pymysql 라이브러리는 '0000', 12월 32일등 잘못된 날짜 일때 str 타입반환.
        return True

    if input_date.strftime("%Y")[:2] == "00":
        return True

    return False


def calculator_image_resize(source_width, source_height, target_width=0, target_height=0):
    """
    이미지 비율을 유지하며 계산 , 너비와 높이 중 하나만 입력된 경우 비율 계산
    원본이미지가 target_width, target_height 보다 작으면 False 반환
    Args:
        source_width (int): 원본 이미지 너비
        source_height (int): 원본 이미지 높이
        target_width (int): 변경할 이미지 너비. Defaults 0.
        target_height (int): 변경할 이미지 높이. Defaults 0.
    Returns:
        Union[bool, dict]: 변경할 이미지 너비, 높이 dict{'width': new_width, 'height': new_height} or False
    """
    # 작은경우 리사이즈 안함
    if source_width < target_width and source_height < target_height:
        return False

    if source_width > target_width and source_height > target_height:
        # 원본이 타겟보다 크면 축소 비율 계산
        ratio_width = target_width / source_width
        ratio_height = target_height / source_height
        min_ratio = min(ratio_width, ratio_height)
        return {'width': int(source_width * min_ratio), 'height': int(source_height * min_ratio)}

    # 이미지 비율을 유지하며 계산
    # 너비와 높이 중 하나만 입력된 경우 비율 계산
    if target_width and not target_height:
        ratio = target_width / source_width
        new_width = target_width
        new_height = int(source_height * ratio)

    elif not target_width and target_height:
        ratio = target_height / source_height
        new_width = int(source_width * ratio)
        new_height = target_height

    else:
        return False  # 너비와 높이 둘 다 입력되거나 입력되지 않은 경우 처리

    return {'width': new_width, 'height': new_height}



def thumbnail(source_file: str, target_path: str = None, width: int = 200, height: int = 150, **kwargs) -> str:
    """섬네일 이미지를 생성한다.

    Args:
        source_file (str): 원본 이미지 파일 경로
        target_path (str, optional): 섬네일 이미지 파일 경로. Defaults to None.
        width (int, optional): 섬네일 이미지 너비. Defaults to 200.
        height (int, optional): 섬네일 이미지 높이. Defaults to 150.

    Returns:
        str: 섬네일 이미지 파일 경로
    """
    try:
        source_basename = os.path.basename(source_file)
        source_path = os.path.dirname(source_file)
        target_path = target_path or source_path

        # 섬네일 저장경로 생성
        os.makedirs(target_path, exist_ok=True)

        # 섬네일 파일 경로
        thumbnail_file = os.path.join(target_path, f"thumbnail_{width}x{height}_{source_basename}")
        # 섬네일 파일이 존재
        # 원본파일 생성시간 < 섬네일 파일 생성시간
        if os.path.exists(thumbnail_file):
            if os.path.getmtime(source_file) < os.path.getmtime(thumbnail_file):
                return thumbnail_file

        # 이미지 객체 생성
        # 파일이 없가나 이미지가 아닐 경우 예외가 발생하므로 검사를 따로 하지 않음.
        source_image = Image.open(source_file)
        source_width, source_height = source_image.size

        # 이미지가 섬네일이미지보다 작을 경우
        if source_width < width or source_height < height:
            # 확장 이미지 생성
            expanded_img = Image.new("RGB", (width, height), (255, 255, 255))
            # 기존 이미지를 확장된 이미지 중앙에 삽입
            left = (width - source_width) // 2
            top = (height - source_height) // 2
            expanded_img.paste(source_image, (left, top))
            expanded_img.save(thumbnail_file)
        else:
            # 이미지를 지정한 크기로 자르고 저장
            ImageOps.fit(source_image, (width, height)).save(thumbnail_file)
            # source_image.thumbnail((width, height))
            # source_image.save(thumbnail_file)

        return thumbnail_file

    except UnidentifiedImageError as e:
        print("원본 이미지 객체 생성 실패 : ", e)
        return ""

    except Exception as e:
        print("섬네일 생성 실패 : ", e)
        return ""


def get_editor_image(contents: str, view: bool = True) -> list:
    """에디터에서 이미지 태그를 추출한다.

    Args:
        contents (str): 내용
        view (bool, optional): 보기모드 여부. Defaults to True.

    Returns:
        list: 이미지 태그 src 속성 값
    """
    if not contents:
        return []

    # contents 중 img 태그 추출
    if view:
        pattern = re.compile(r"<img([^>]*)>", re.IGNORECASE | re.DOTALL)
    else:
        pattern = re.compile(r"<img[^>]*src=[\'\"]?([^>\'\"]+[^>\'\"]+)[\'\"]?[^>]*>", re.IGNORECASE | re.DOTALL)

    matches = pattern.findall(contents)

    return matches


def extract_alt_attribute(img_tag: str) -> str:
    """alt 속성 추출

    Args:
        img_tag (str): img 태그

    Returns:
        str: alt 속성 값
    """
    alt_match = re.search(r'alt=[\"\']?([^\"\']*)[\"\']?', img_tag, re.IGNORECASE)
    alt = str(alt_match.group(1)) if alt_match else ''
    return alt


def cut_name(request: Request, name: str) -> str:
    """기본환경설정 > 이름(닉네임) 표시

    Args:
        request (Request): FastAPI Request
        name (str): 이름

    Returns:
        str: 자른 이름
    """
    config = request.state.config

    if not name:
        return ''

    return name[:config.cf_cut_name] if config.cf_cut_name else name


def delete_old_records():
    """
    설정일이 지난 데이터를 삭제
    """
    try:
        db = DBConnect().sessionLocal()
        config = db.scalar(select(Config))
        today = datetime.now()

        # 방문자 기록 삭제
        if config.cf_visit_del > 0:
            base_date = today - timedelta(days=config.cf_visit_del)
            if db.bind.dialect.name == "sqlite":
                visit_datetime = Visit.vi_date.concat(" ").concat(Visit.vi_time)
                concat_expr = func.strftime("%Y-%m-%d %H:%M:%S", visit_datetime)
            else:
                concat_expr = func.cast(func.concat(Visit.vi_date, " ", Visit.vi_time), DateTime)
            result = db.execute(
                delete(Visit).where(concat_expr < base_date)
            )
            print("방문자기록 삭제 기준일 : ", base_date, f"{result.rowcount}건 삭제")

        # 인기검색어 삭제
        if config.cf_popular_del > 0:
            from service.popular_service import PopularService

            base_date = today - timedelta(days=config.cf_popular_del)
            popular_service = PopularService(db)
            delete_count = popular_service.delete_populars(base_date.date())

            print("인기검색어 삭제 기준일 : ", base_date, f"{delete_count}건 삭제")

        # 최근게시물 삭제
        if config.cf_new_del > 0:
            base_date = today - timedelta(days=config.cf_new_del)
            result = db.execute(
                delete(BoardNew).where((BoardNew.bn_datetime != None) & (BoardNew.bn_datetime < base_date))
            )
            print("최근게시물 삭제 기준일 : ", base_date, f"{result.rowcount}건 삭제")

        # 쪽지 삭제
        if config.cf_memo_del > 0:
            base_date = today - timedelta(days=config.cf_memo_del)
            result = db.execute(
                delete(Memo).where(Memo.me_send_datetime < base_date)
            )
            print("쪽지 삭제 기준일 : ", base_date, f"{result.rowcount}건 삭제")

        # 탈퇴회원 자동 삭제
        if config.cf_leave_day > 0:
            # TODO: 회원삭제 처리 추가
            # query = update(Member).where(Member.mb_leave_date < datetime.now() - timedelta(days=config.cf_leave_day))
            # data = {}
            # result = db.execute(query, data)
            # print("회원 삭제 기준일 : ", datetime.now() - timedelta(days=config.cf_leave_day), f"{result}건 삭제")
            pass
        db.commit()
    except Exception as e:
        print(e)
    finally:
        db.close()


def is_possible_ip(request: Request, ip: str) -> bool:
    """IP가 접근허용된 IP인지 확인

    Args:
        request (Request): FastAPI Request 객체
        ip (str): IP

    Returns:
        bool: 허용된 IP이면 True, 아니면 False
    """
    cf_possible_ip = request.state.config.cf_possible_ip
    return check_ip_list(request, ip, cf_possible_ip, allow=True)


def is_intercept_ip(request: Request, ip: str) -> bool:
    """IP가 접근차단된 IP인지 확인

    Args:
        request (Request): FastAPI Request 객체
        ip (str): IP

    Returns:
        bool: 차단된 IP이면 True, 아니면 False
    """
    cf_intercept_ip = request.state.config.cf_intercept_ip
    return check_ip_list(request, ip, cf_intercept_ip, allow=False)


def check_ip_list(request: Request, current_ip: str, ip_list: str, allow: bool) -> bool:
    """IP가 특정 목록에 속하는지 확인하는 함수

    Args:
        request (Request): FastAPI Request 객체
        ip (str): IP
        ip_list (str): IP 목록 문자열
        allow (bool): True인 경우 허용 목록, False인 경우 차단 목록

    Returns:
        bool: 목록에 속하면 True, 아니면 False
    """
    if request.state.is_super_admin:
        return allow

    ip_list = ip_list.strip()
    if not ip_list:
        return allow

    ip_patterns = ip_list.split("\n")
    for pattern in ip_patterns:
        pattern = pattern.strip()
        if not pattern:
            continue
        pattern = pattern.replace(".", r"\.")
        pattern = pattern.replace("+", r"[0-9\.]+")
        if re.match(f"^{pattern}$", current_ip):
            return True

    return False


def filter_words(request: Request, contents: str) -> str:
    """글 내용에 필터링된 단어가 있는지 확인하는 함수

    Args:
        request (Request): FastAPI Request 객체
        contents (str): 글 내용

    Returns:
        str: 필터링된 단어가 있으면 해당 단어, 없으면 빈 문자열
    """
    cf_filter = request.state.config.cf_filter
    words = cf_filter.split(",")
    for word in words:
        word = word.strip()
        if not word:
            continue
        if word in contents:
            return word

    return ''


def read_version():
    """루트 디렉토리의 version.txt 파일을 읽어서 버전을 반환하는 함수
    Returns:
        str: 버전
    """
    with open("version.txt", "r", encoding="UTF-8") as file:
        return file.read().strip()


def read_license():
    """루트 디렉토리의 LICENSE 텍스트 파일을 읽어서 라이센스 내용 반환

    Returns:
        str: 라이센스 내용
    """
    with open("LICENSE", "r", encoding="UTF-8") as file:
        return file.read().strip()


def get_current_admin_menu_id(request: Request) -> Optional[str]:
    """현재 경로의 관리자 메뉴 아이디를 반환하는 함수

    Args:
        request (Request): FastAPI Request 객체

    Returns:
        Optional[str]: 관리자 메뉴 아이디
    """
    try:
        admin_menu = get_admin_menus()

        path = request.url.path
        routes = request.app.routes

        for route in routes:
            # 현재 경로가 router 형식에 맞다면
            if route.path_regex.match(path):
                tags = route.tags
                # 라우터의 태그와 일치하는 메뉴 아이디를 반환
                for tag in tags:
                    for menu_items in admin_menu.values():
                        item = next((item for item in menu_items if item.get("tag", "") == tag), None)
                        if item:
                            return item.get("id")
                break

        # 플러그인 관리자는 경로 기반으로 검색
        for route in routes:
            if route.path_regex.match(path):
                # 사용자가 정의하는 관리자 접두사는 접근이 복잡하므로 삭제후 비교
                parts = route.path.split('/')
                modified_path = '/' + '/'.join(parts[2:])
                if result_menu_id := get_admin_menu_id_by_path(modified_path):
                    return result_menu_id

        raise Exception("관리자 메뉴 아이디를 찾을 수 없습니다.")

    except Exception as e:
        logging.warning(e)
        return None


def remove_query_params(request: Request, keys: Union[str, list]) -> dict:
    """쿼리 파라미터에서 특정 키를 제거합니다.

    Args:
        request (Request): FastAPI Request 객체
        keys (Union[str, list]): 제거할 키

    Returns:
        dict: 쿼리 파라미터
    """
    query_params_dict = dict(request.query_params)

    if isinstance(keys, str):
        keys = [keys]

    for key in keys:
        query_params_dict.pop(key, None)

    return query_params_dict


def set_url_query_params(url: Union[str, URL], query_params: Any) -> str:
    """쿼리 파라미터가 포함된 URL을 반환합니다.

    Args:
        url (URL): URL 객체
        query_params (Any): 쿼리 파라미터

    Returns:
        URL: 쿼리 파라미터가 포함된 URL
    """
    if isinstance(url, str):
        url = URL(url)

    return url.replace_query_params(**query_params).__str__()


def safe_int_convert(string: str) -> int:
    """안전한 int 변환 함수"""
    try:
        return int(string)
    except (ValueError, TypeError):
        return 0


def get_paging_info(current_page: int, records_per_page: int, total_records: int) -> dict:
    """페이징 정보를 반환하는 함수

    Args:
        current_page (int): 현재 페이지
        records_per_page (int): 페이지당 레코드 수
        total_records (int): 전체 레코드 수

    Returns:
        dict: 페이징 정보
    """

    offset = (current_page - 1) * records_per_page
    return {
        "offset": offset,
        "total_records": total_records,
        "current_page": current_page,
        "total_pages": math.ceil(total_records / records_per_page),
    }


def hide_ip_address(ip: str) -> str:
    """IP 주소를 가려주는 함수"""
    return re.sub(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)",
                  "\\1.#.#.\\4", ip)
