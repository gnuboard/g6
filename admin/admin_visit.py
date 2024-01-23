from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy import extract, select, cast, String

from core.database import db_session
from core.exception import AlertException
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_super_admin, validate_token
from lib.pbkdf2 import validate_password
from lib.template_functions import get_paging

router = APIRouter()
templates = AdminTemplates()

VISIT_MENU_KEY = "200800"
VISIT_SEARCH_MENU_KEY = "200810"
VISIT_DELETE_MENU_KEY = "200820"


@router.get("/visit_search", tags=["admin_visit_search"])
async def visit_search(
    request: Request,
    db: db_session,
    sst: str = Query(default=""),  # sort field (정렬 필드)
    sod: str = Query(default=""),  # search order (검색 오름, 내림차순)
    sfl: str = Query(default=""),  # search field (검색 필드)
    stx: str = Query(default=""),  # search text (검색어)
    current_page: int = Query(default=1, alias="page"),  # 페이지
):
    """
    접속자 검색
    """
    request.session["menu_key"] = VISIT_SEARCH_MENU_KEY

    # 초기 쿼리 설정
    query = select()
    records_per_page = request.state.config.cf_page_rows

    # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    if sst is not None and sst != "":
        if sod == "desc":
            query = query.order_by(desc(getattr(Visit, sst)))
        else:
            query = query.order_by(asc(getattr(Visit, sst)))

    # sfl과 stx가 제공되면, 해당 열과 값으로 추가 필터링을 합니다.
    if sfl is not None and stx is not None:
        if hasattr(Visit, sfl):
            if sfl in ["vi_ip", "vi_date"]:
                query = query.where(cast(getattr(Visit, sfl), String).like(f"{stx}%"))
            else:
                query = query.where(getattr(Visit, sfl).like(f"%{stx}%"))

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page
    # 전체 레코드 개수 계산
    total_records = db.scalar(query.add_columns(func.count(Visit.vi_id)).order_by(None))
    # 최종 쿼리 결과를 가져옵니다.
    visits = db.scalars(query.add_columns(Visit).offset(offset).limit(records_per_page)).all()

    for visit in visits:
        visit.referer = visit.vi_referer[:255] if visit.vi_referer else ""
        if visit.referer:
            visit.title = visit.referer.replace("<", "&lt;").replace(">", "&gt;")
            visit.link = f'<a href="{visit.vi_referer}" target="_blank" title="{visit.title}">{visit.title}</a>'

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("visit_search.html", context)


@router.get("/visit_delete", tags=["admin_visit_delete"])
async def visit_delete(request: Request, db: db_session):
    """
    접속자로그 삭제 페이지
    """
    request.session["menu_key"] = VISIT_DELETE_MENU_KEY

    now_year = datetime.now().year
    min_date = db.scalar(select(func.min(Visit.vi_date).label('min_date')))
    min_year = min_date.year if min_date else now_year

    context = {
        "request": request,
        "min_year": min_year,
        "now_year": now_year,
    }
    return templates.TemplateResponse("visit_delete.html", context)


@router.post("/visit_delete_update",
             dependencies=[Depends(validate_token), Depends(validate_super_admin)],
             tags=["admin_visit_delete"])
async def visit_delete_update(
    request: Request,
    db: db_session,
    year: str = Form(...),
    month: str = Form(...),
    method: str = Form(...),
    admin_password: str = Form(..., alias="pass"),
):
    """
    접속자로그 레코드 삭제
    """
    member = request.state.login_member

    if not validate_password(admin_password, member.mb_password):
        raise AlertException("관리자 비밀번호가 일치하지 않습니다.")

    if not year:
        raise AlertException("년도를 선택해 주세요.")

    if not month:
        raise AlertException("월을 선택해 주세요.")

    total_records = db.scalar(select(func.count(Visit.vi_id)))
    year = int(year)
    month = int(month)
    delete_date = datetime(year, month, 1)

    query = delete(Visit)
    if method == "before":
        # 이전 자료 삭제
        query = query.where(Visit.vi_date < delete_date)

    elif method == "specific":
        # 당월 자료만 삭제
        query = query.where(
            extract('year', Visit.vi_date) == year,
            extract('month', Visit.vi_date) == month
        )
    else:
        raise AlertException("잘못된 요청입니다.", 400)

    result = db.execute(query)
    db.commit()

    raise AlertException(
        f"총 {total_records}개의 자료 중 {result.rowcount}개의 자료가 삭제되었습니다.",
        url="/admin/visit_delete"
    )


@router.get("/visit_list", tags=["admin_visit_list"])
async def visit_list(
    request: Request,
    db: db_session,
    current_page: int = Query(default=1, alias="page"),  # 페이지
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    config = request.state.config
    request.state.time_ymd = datetime.now()
    if from_date:
        from_date = re.sub(r'[^0-9 :\-]', '', from_date)
    if to_date:
        to_date = re.sub(r'[^0-9 :\-]', '', to_date)

    if from_date == "":
        from_date = request.state.time_ymd.strftime("%Y-%m-%d")
    if to_date == "":
        to_date = request.state.time_ymd.strftime("%Y-%m-%d")

    datetime_from = datetime.strptime(from_date, "%Y-%m-%d")
    datetime_to = datetime.strptime(to_date, "%Y-%m-%d")

    if datetime_from > datetime_to:
        to_date = from_date

    # 초기 쿼리 설정
    query = select().where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))

    # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    sst = request.query_params.get("sst", "vi_datetime")
    sod = request.query_params.get("sod", "desc")
    if sst and sst != "":
        if sod == "desc":
            query = query.order_by(desc(sst))
        else:
            query = query.order_by(asc(sst))
    else:
        query = query.order_by(desc(sst))

    # 페이지 번호에 따른 offset 계산
    records_per_page = getattr(config, "cf_page_rows", 10)
    offset = (current_page - 1) * records_per_page
    # 전체 레코드 개수 계산
    total_records = db.scalar(query.add_columns(func.count(Visit.vi_id)).order_by(None))
    # 최종 쿼리 결과를 가져옵니다.
    if db.bind.dialect.name == 'sqlite':
        concat_expr = func.strftime('%Y-%m-%d %H:%M:%S', f'{Visit.vi_date} {Visit.vi_time}')
    else:
        concat_expr = func.concat(f'{Visit.vi_date} {Visit.vi_time}')
    visits = db.scalars(
        query.add_columns(Visit, concat_expr.label("vi_datetime"))
        .offset(offset)
        .limit(records_per_page)
    ).all()

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_list.html", context)


@router.get("/visit_domain", tags=["admin_visit_list"])
async def visit_domain(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    도메인별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    site_url = f"{request.base_url.scheme}://{request.base_url.hostname}"
    if request.base_url.port:
        site_url += f":{request.base_url.port}"
    # referer에서 도메인 필터링
    filtered_visits = []
    total_records = 0
    for visit in visits:
        # http or https
        match = re.search(r'^http[s]*\S+', visit.vi_referer)
        if not match:
            continue

        match_group = match.group()
        if match_group:
            referer: str = re.sub(r"^(www\.|search\.|dirsearch\.|dir\.search\.|dir\.|kr\.search\.|myhome\.)(.*)",
                                  "\\2", match_group)
            filtered_visits.append({
                "vi_referer": '직접' if referer.startswith(site_url) else referer,
                "count": 1,
            })

            total_records += 1

    visits = count_by_field(filtered_visits, "vi_referer")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_domain.html", context)


@router.get("/visit_browser", tags=["admin_visit_list"])
async def visit_browser(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    브라우저별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    # 브라우저별 접속자집계
    filtered_visits = []
    total_records = 0
    for visit in visits:
        filtered_visits.append({
            "vi_browser": visit.vi_browser or get_browser(visit.vi_agent),
            "count": 1,
        })

        total_records += 1

    visits = count_by_field(filtered_visits, "vi_browser")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_browser.html", context)


@router.get("/visit_os", tags=["admin_visit_list"])
async def visit_os(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    OS별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    # OS별 접속자집계
    filtered_visits = []
    total_records = 0
    for visit in visits:
        filtered_visits.append({
            "vi_os": visit.vi_os or get_os(visit.vi_agent),
            "count": 1,
        })

        total_records += 1

    visits = count_by_field(filtered_visits, "vi_os")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_os.html", context)


@router.get("/visit_device")
async def visit_device(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    접속기기별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    # 접속기기별 접속자집계
    filtered_visits = []
    total_records = 0
    for visit in visits:
        filtered_visits.append({
            "vi_device": visit.vi_device,
            "count": 1,
        })

        total_records += 1

    visits = count_by_field(filtered_visits, "vi_device")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_device.html", context)


@router.get("/visit_hour")
async def visit_hour(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    시간별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    dialect = db.bind.dialect.name
    from_date, to_date = validate_time(from_date, to_date)

    query = select().where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    # 합계
    total_count = db.scalar(query.add_columns(func.count(Visit.vi_id)))
    # 시간별 접속자집계
    # TODO: postgresql는 테스트가 안되어 있음
    if dialect == 'mysql':
        query = query.add_columns(func.hour(Visit.vi_time).label('hour'))
    elif dialect == 'postgresql':
        query = query.add_columns(func.to_char(Visit.vi_time, 'HH24').label('hour'))
    elif dialect == 'sqlite':
        query = query.add_columns(func.strftime('%H', Visit.vi_time).label('hour'))
    query_result = db.execute(
        query.add_columns(Visit.vi_time, func.count().label('hour_count'))
        .group_by('hour')
    ).all()

    # 00 ~ 23 시간별 접속자집계
    visits = {f"{hour:02d}": {"count": 0, "rate": 0} for hour in range(24)}

    for result in query_result:
        result_hour = int(result.hour)
        visits[f"{result_hour:02d}"]["count"] = result.hour_count
        visits[f"{result_hour:02d}"]["rate"] = round(result.hour_count / total_count * 100, 2)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_count,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_hour.html", context)


@router.get("/visit_weekday", tags=["admin_visit_list"])
async def visit_weekday(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    요일별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    dialect = db.bind.dialect.name
    from_date, to_date = validate_time(from_date, to_date)

    query = select().where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    # 합계
    total_count = db.scalar(query.add_columns(func.count(Visit.vi_id)))
    # 요일별 접속자집계
    # TODO: postgresql는 테스트가 안되어 있음
    if dialect == 'mysql':
        query = query.add_columns(func.dayofweek(Visit.vi_date).label('dow'))
    elif dialect == 'postgresql':
        query = query.add_columns(func.to_char(Visit.vi_date, 'D').label('dow'))
    elif dialect == 'sqlite':
        query = query.add_columns(func.strftime('%w', Visit.vi_date).label('dow'))
    query_result = db.execute(
        query.add_columns(Visit.vi_date, func.count().label('dow_count'))
        .group_by('dow')
    ).all()

    # 요일별 접속자집계
    day_of_week = {
        "Mon": "월",
        "Tue": "화",
        "Wed": "수",
        "Thu": "목",
        "Fri": "금",
        "Sat": "토",
        "Sun": "일",
    }
    visits = {value: {"count": 0, "rate": 0} for value in day_of_week.values()}

    for result in query_result:
        # 데이터베이스 별로 요일(day of week)을 출력하는 기준이 다르기 때문에
        # 요일을 python 기준으로 다시한번 변경한다.
        dow = day_of_week[result.vi_date.strftime("%a")]
        visits[dow]["count"] = result.dow_count
        visits[dow]["rate"] = round(result.dow_count / total_count * 100, 2)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_count,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_weekday.html", context)


@router.get("/visit_date", tags=["admin_visit_list"])
async def visit_date(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    일별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    # 접속자집계
    filtered_visits = []
    total_records = 0
    for visit in visits:
        filtered_visits.append({
            "visit_date": visit.vi_date.strftime("%Y-%m-%d"),
            "count": 1,
        })

        total_records += 1

    visits = count_by_field(filtered_visits, "visit_date")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_date.html", context)


@router.get("/visit_month", tags=["admin_visit_list"])
async def visit_month(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    월별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    # 접속자집계
    filtered_visits = []
    total_records = 0
    for visit in visits:
        filtered_visits.append({
            "visit_month": visit.vi_date.strftime("%Y-%m"),
            "count": 1,
        })

        total_records += 1

    visits = count_by_field(filtered_visits, "visit_month")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_month.html", context)


@router.get("/visit_year", tags=["admin_visit_list"])
async def visit_year(
    request: Request,
    db: db_session,
    from_date: str = Query(default="", alias="fr_date"),  # 시작일
    to_date: str = Query(default=""),  # 종료일
):
    """
    연도별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    visits = db.scalars(
        select(Visit)
        .where(Visit.vi_date.between(from_date, to_date + " 23:59:59"))
    ).all()

    # 접속자집계
    filtered_visits = []
    total_records = 0
    for visit in visits:
        filtered_visits.append({
            "visit_year": visit.vi_date.strftime("%Y"),
            "count": 1,
        })

        total_records += 1

    visits = count_by_field(filtered_visits, "visit_year")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_year.html", context)


def count_by_field(list: list, field_name: str) -> list:
    """기존 리스트를 field_name 기준으로 합산합니다.
    Args:
        list (list): 접속자 리스트
    """
    temp = {}
    for item in list:
        referer = item[field_name]
        count = item["count"]

        if referer in temp:
            temp[referer] += count
        else:
            temp[referer] = count
    return [{field_name: key, "count": value} for key, value in temp.items()]


def add_percent_field(list: [dict]) -> list:
    """기존 리스트에 백분율을 계산하여 percent 필드를 추가합니다.
    Args:
        list (list): 접속자 리스트 (count 필드가 있어야 함)
    """
    key_exists = any('count' in key for key in list)
    if not key_exists:
        return list

    total_count = sum([item["count"] for item in list])
    for item in list:
        item["percent"] = round(item["count"] / total_count * 100, 2)
    return list


def get_browser(user_agent):
    """브라우저이름을 반환합니다.
    """
    user_agent = user_agent.lower()

    browsers = {
        'MSIE': r"msie ([1-9][0-9]\.[0-9]+)",
        'FireFox': r"firefox",
        'Chrome': r"chrome",
        'Netscape': r"x11",
        'Opera': r"opera",
        'Gecko': r"gec",
        'Robot': r"bot|slurp",
        'IE': r"internet explorer",
        'Mozilla': r"mozilla"
    }

    for browser_name, pattern in browsers.items():
        if re.search(pattern, user_agent):
            return browser_name

    return "other"  # todo 다국어


def get_os(user_agent):
    user_agent = user_agent.lower()

    os_patterns = {
        "Windows10": r"windows nt 10\.0",
        "Windows8.1": r"windows nt 6\.3",
        "Windows8": r"windows nt 6\.2",
        "Windows7": r"windows nt 6\.1",
        "Vista": r"windows nt 6\.0",
        "XP": r"windows nt 5\.1",
        "2003": r"windows nt 5\.2",
        "NT": r"windows nt 4\.[0-9]*",
        "ME": r"windows 9x",
        "CE": r"windows ce",
        "MAC": r"mac",
        "Android": r"android",
        "Phone": r"phone",
        "Robot": r"bot|Yeti|Baidu|Daumoa|Yandex|slurp",
        "Linux": r"linux",
        "sunOS": r"sunos",
        "IE": r"internet explorer",
        "Mozilla": r"mozilla",
        "IRIX": r"irix"
    }

    # Iterate through the patterns and return the first matching OS
    for os_name, pattern in os_patterns.items():
        if re.search(pattern, user_agent):
            return os_name

    return "other"


def validate_time(from_date, to_date):
    if from_date:
        from_date = re.sub(r'[^0-9 :\-]', '', from_date)
    if to_date:
        to_date = re.sub(r'[^0-9 :\-]', '', to_date)

    today_date = datetime.now().strftime("%Y-%m-%d")
    if from_date == "":
        from_date = today_date
    if to_date == "":
        to_date = today_date

    datetime_from = datetime.strptime(from_date, "%Y-%m-%d")
    datetime_to = datetime.strptime(to_date, "%Y-%m-%d")

    if datetime_from > datetime_to:
        to_date = from_date

    return from_date, to_date
