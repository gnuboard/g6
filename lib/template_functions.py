# Jinja2 Templates 관련 HTML 출력 함수
# ============================================================================
import os
from typing import Union

from fastapi import Request
from sqlalchemy import select

from core.database import DBConnect
from core.models import Group, Member


def editor_macro(request: Request) -> str:
    """설정한 에디터의 macros.html 파일경로를 반환하는 함수

    Args:
        request (Request): FastAPI Request 객체

    Returns:
        str: 에디터 macros.html 파일경로
    """
    # 에디터가 '사용안함' 설정이거나 에디터가 지정되지 않은 경우
    # textarea를 사용하도록 설정한다.
    editor_name = request.state.editor
    if not request.state.use_editor or not editor_name:
        editor_name = "textarea"

    return editor_name + "/macros.html"


def get_editor_select(id: str, selected: str) -> str:
    """DHTML 에디터 목록을 SELECT 형식으로 얻음

    Args:
        id (str): select 태그의 id 속성값
        selected (str): 기본적으로 선택되어야 할 에디터명

    Returns:
        str: select 태그의 HTML 코드
    """
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}">')

    if id == 'bo_select_editor':
        selected_attr = "selected" if selected == "" else ""
        html_code.append(f'<option value="" {selected_attr}>기본환경설정의 에디터 사용</option>')
    else:
        html_code.append(f'<option value="">사용안함</option>')

    editor_path = os.path.join("static", "plugin", "editor")
    for editor in os.listdir(editor_path):
        if (editor == 'textarea'
                or not os.path.isdir(os.path.join(editor_path, editor))):
            continue
        attr = get_selected(editor, selected)
        html_code.append(f'<option value="{editor}" {attr}>{editor}</option>')

    html_code.append('</select>')

    return ''.join(html_code)


def get_group_select(id: str, selected: str = "", attribute: str = "") -> str:
    """게시판 그룹 목록을 SELECT 형식으로 얻음

    Args:
        id (str): select 태그의 id 속성값
        selected (str, optional): 기본적으로 선택되어야 할 그룹명. Defaults to "".
        attribute (str, optional): select 태그의 추가 속성값. Defaults to "".

    Returns:
        str: select 태그의 HTML 코드
    """
    db = DBConnect().sessionLocal()
    groups = db.scalars(
        select(Group).order_by(Group.gr_order, Group.gr_id)
    ).all()
    db.close()

    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {attribute}>\n')
    html_code.append('<option value="">선택</option>')

    for group in groups:
        html_code.append(option_selected(
            group.gr_id, selected, group.gr_subject))

    html_code.append('</select>')

    return ''.join(html_code)


def get_member_id_select(id: str, level: int, selected: str, attribute=""):
    """회원아이디를 SELECT 형식으로 얻음

    Args:
        id (_type_): _description_
        level (_type_): _description_
        selected (_type_): _description_
        event (str, optional): _description_. Defaults to ''.

    Returns:
        _type_: _description_
    """
    db = DBConnect().sessionLocal()
    mb_ids = db.scalars(
        select(Member.mb_id)
        .where(Member.mb_level >= level)
    ).all()
    db.close()

    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {attribute}>')
    html_code.append('<option value="">선택하세요</option>')

    for mb_id in mb_ids:
        attr = get_selected(mb_id, selected)
        html_code.append(f'<option value="{mb_id}" {attr}>{mb_id}</option>')

    html_code.append('</select>')

    return ''.join(html_code)


def get_member_level_select(id: str, start: int, end: int,
                            selected: int, attribute: str = '') -> str:
    """회원레벨을 SELECT 형식으로 얻음

    Args:
        id (str): select 태그의 id 속성값
        start (int): 시작 레벨
        end (int): 종료 레벨
        selected (int): 기본적으로 선택되어야 할 레벨
        attribute (str, optional): select 태그의 추가 속성값. Defaults to "".

    Returns:
        str: _description_
    """
    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {attribute}>')

    for i in range(start, end + 1):
        attr = get_selected(i, selected)
        html_code.append(f'<option value="{i}" {attr}>{i}</option>')

    html_code.append('</select>')

    return ''.join(html_code)


def get_skin_select(skin_gubun: str, id: str, selected: str,
                    attribute: str = "", device: str = "") -> str:
    """skin_gubun(new, search, connect, faq 등)에 따른 스킨을
    SELECT 형식으로 얻음

    Args:
        skin_gubun (str): 테마 내부의 폴더명(기능)
        id (str): select 태그의 id 속성값
        selected (str): 기본적으로 선택되어야 할 스킨명
        attribute (str, optional): select 태그의 추가 속성값. Defaults to "".
        device (str, optional): 디바이스별 폴더명(mobile). Defaults to "".
            PC는 추가 경로 없음 (ex: /templates/{theme}/board/{skin_gubun})

    Returns:
        str: select 태그의 HTML 코드
    """
    # Lazy import
    from core.template import TEMPLATES_DIR

    skin_path = TEMPLATES_DIR + f"/{device}/{skin_gubun}"

    html_code = []
    html_code.append(f'<select id="{id}" name="{id}" {attribute}>')
    html_code.append('<option value="">선택</option>')

    for skin in os.listdir(skin_path) if os.path.isdir(skin_path) else []:
        if os.path.isdir(f"{skin_path}/{skin}"):
            attr = get_selected(skin, selected)
            html_code.append(f'<option value="{skin}" {attr}>{skin}</option>')

    html_code.append('</select>')

    return ''.join(html_code)


def get_selected(field_value, value):
    """필드에 저장된 값과 기본 값을 비교하여 selected 를 반환합니다.

    Args:
        field_value: 필드에 저장된 값
        value: 기본 값

    Returns:
        str: 값이 일치하면 'selected="selected"', 그렇지 않으면 ''
    """
    if ((field_value is None or field_value == '')
            or (value is None or value == '')):
        return ''

    return ' selected="selected"' if str(field_value) == str(value) else ''


def option_selected(value: str, selected: str, text = ''):
    """option 태그를 생성하여 반환

    Args:
        value (str): value 속성값
        selected (str): selected 속성값
        text (str, optional): _description_. Defaults to ''.

    Returns:
        str: option 태그
    """
    if not text:
        text = value

    select_attr = get_selected(value, selected)

    return f'<option value="{value}" {select_attr}>{text}</option>\n'


def option_array_checked(option: str, arr: Union[list, str] = []) -> str:
    """option이 arr에 포함되어 있으면 checked="checked"를 반환

    Args:
        option (str): _description_
        arr (Union[list, str], optional): 체크할 값들. Defaults to [].

    Returns:
        str: 'checked="checked"' 또는 ''
    """
    if not isinstance(arr, list):
        arr = arr.split(',')

    if arr and option in arr:
        return 'checked="checked"'

    return ''


def get_paging(request: Request,
               current_page: int, total_count: int, page_rows: int = 0,
               add_url: str = ""):
    """페이지 출력 함수

    그누보드5 get_paging() 함수와 다른점
    1. 인수에서 write_pages 삭제
    2. 인수에서 total_page 대신 total_count 를 사용함

    Args:
        request (Request): FastAPI Request 객체
        current_page (int): 현재 페이지
        total_count (int): 전체 레코드 수
        page_rows (int, optional): 한 페이지당 라인수. Defaults to 0.
        add_url (str, optional): 페이지 링크의 추가 URL. Defaults to "".

    Returns:
        str: 페이징 HTML 코드
    """
    config = request.state.config
    url_prefix = request.url

    try:
        current_page = int(current_page)
    except ValueError:
        # current_page가 정수로 변환할 수 없는 경우 기본값으로 1을 사용하도록 설정
        current_page = 1
    total_count = int(total_count)

    # 한 페이지당 라인수
    if not page_rows:
        page_rows = config.cf_mobile_page_rows if request.state.is_mobile and config.cf_mobile_page_rows else config.cf_page_rows
    # 페이지 표시수
    page_count = config.cf_mobile_pages if request.state.is_mobile and config.cf_mobile_pages else config.cf_write_pages

    # 올바른 total_pages 계산 (올림처리)
    total_pages = (total_count + page_rows - 1) // page_rows

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


def subject_sort_link(request: Request,
                      column: str, query_string: str = '', flag: str = 'asc') -> str:
    """현재 페이지에서 컬럼을 기준으로 정렬하는 링크를 생성한다.

    Args:
        request (Request): FastAPI Request 객체
        column (str): 정렬할 컬럼명
        query_string (str, optional): 쿼리 문자열. Defaults to ''.
        flag (str, optional): 정렬 방식. Defaults to 'asc'.

    Returns:
        str: 정렬 링크
    """
    sst = request.query_params.get("sst", "")
    sod = request.query_params.get("sod", "")
    sfl = request.query_params.get("sfl", "")
    stx = request.query_params.get("stx", "")
    sca = request.query_params.get("sca", "")
    fr_date = request.query_params.get("fr_date", "")
    to_date = request.query_params.get("to_date", "")
    page = request.query_params.get("page", "")

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

    # sfl, stx, sca, fr_date, to_date, page 값이 None이 아닌 경우, 각각의 값을 arr_query에 추가한다.
    if sfl is not None:
        arr_query.append(f'sfl={sfl}')
    if stx is not None:
        arr_query.append(f'stx={stx}')
    if sca is not None:
        arr_query.append(f'sca={sca}')
    if fr_date:
        arr_query.append(f'fr_date={fr_date}')
    if to_date:
        arr_query.append(f'to_date={to_date}')
    if page:
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
