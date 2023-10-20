from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from common import *
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["generate_one_time_token"] = generate_one_time_token

VISIT_MENU_KEY = "200800"


@router.get("/visit_search")
def visit_search(request: Request, db: Session = Depends(get_db),
                 sst: str = Query(default=""),  # sort field (정렬 필드)
                 sod: str = Query(default=""),  # search order (검색 오름, 내림차순)
                 sfl: str = Query(default=""),  # search field (검색 필드)
                 stx: str = Query(default=""),  # search text (검색어)
                 current_page: int = Query(default=1, alias="page"),  # 페이지
                 ):
    """
    접속자 검색
    """
    request.session["menu_key"] = "200810"

    # 초기 쿼리 설정
    query = db.query(Visit)
    records_per_page = request.state.config.cf_page_rows

    # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    if sst is not None and sst != "":
        if sod == "desc":
            query = query.order_by(desc(getattr(Visit, sst)))
        else:
            query = query.order_by(asc(getattr(Visit, sst)))

    # sfl과 stx가 제공되면, 해당 열과 값으로 추가 필터링을 합니다.
    if sfl is not None and stx is not None:
        if hasattr(Visit, sfl):  # sfl이 models.Board에 존재하는지 확인
            if sfl in ["vi_ip", "vi_date"]:
                query = query.filter(getattr(Visit, sfl).like(f"{stx}%"))
            else:
                query = query.filter(getattr(Visit, sfl).like(f"%{stx}%"))

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 전체 레코드 개수 계산
    total_records = query.count()
    # 최종 쿼리 결과를 가져옵니다.
    result = query.offset(offset).limit(records_per_page).all()

    visits = []
    for i, row in enumerate(result):
        referer = row.vi_referer[:255] if row.vi_referer else ""
        title = referer.replace("<", "&lt;").replace(">", "&gt;")
        link = f'<a href="{row.vi_referer}" target="_blank" title="{title}">'
        visits.append({
            "browser": row.vi_browser,
            "os": row.vi_os,
            "device": row.vi_device,
            "referer": referer,
            "title": title,
            "link": link,
            "ip": row.vi_ip,
            "date": row.vi_date,
            "time": row.vi_time,
        })

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("visit_search.html", context)


@router.get("/visit_delete")
def visit_delete(request: Request, db: Session = Depends(get_db), ):
    '''
    접속자로그 삭제
    '''
    request.session["menu_key"] = "200820"

    min_date = db.query(func.min(Visit.vi_date).label('min_date')).scalar()
    min_year = min_date.year if min_date else None
    now_year = datetime.now().year
    if min_year is None:
        min_year = now_year

    return templates.TemplateResponse("visit_delete.html",
                                      {
                                          "request": request,
                                          "min_year": min_year,
                                          "now_year": now_year,
                                      })


@router.post("/visit_delete_update")
async def visit_delete_update(request: Request, db: Session = Depends(get_db),
                              token: str = Form(None),
                              year: str = Form(default=""),  # 년도
                              month: str = Form(default=""),  # 월
                              method: str = Form(default=""),  # 방법
                              admin_password: str = Query(default="", alias="pass"),  # 관리자 비밀번호                       
                              ):
    '''
    접속자로그 레코드 삭제
    '''

    if not validate_one_time_token(token, 'delete'):
        return templates.TemplateResponse("alert.html",
                                          {"request": request, "errors": ["토큰이 유효하지 않습니다. 새로고침후 다시 시도해 주세요."]})

    member = request.state.login_member
    if not member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["로그인 후 이용해 주세요."]})

    if not verify_password(admin_password, member.mb_password) is False:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["관리자 비밀번호가 일치하지 않습니다."]})

    if not year:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["년도를 선택해 주세요."]})

    if not month:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["월을 선택해 주세요."]})

    total_records = db.query(Visit).count()  # 전체 레코드 수
    deleted_records = 0  # 삭제된 레코드 수를 추적하는 변수
    year = int(year)
    month = int(month)

    if method == "before":
        # 이전 자료 삭제
        # delete 메서드에 synchronize_session=False 옵션을 추가하여 SQLAlchemy가 현재 세션(session)과 동기화하지 않도록 했습니다. 
        # 이렇게 하면 "Cannot evaluate Extract"과 같은 오류가 발생하지 않을 것입니다.
        deleted_records = db.query(Visit).filter(
            and_(
                extract('year', Visit.vi_date) < year,
                extract('month', Visit.vi_date) < month
            )
        ).delete(synchronize_session=False)
        db.commit()

    elif method == "specific":
        # 당월 자료만 삭제
        deleted_records = db.query(Visit).filter(
            and_(
                extract('year', Visit.vi_date) == year,
                extract('month', Visit.vi_date) == month
            )
        ).delete(synchronize_session=False)
        db.commit()

    return templates.TemplateResponse("alert.html",
                                      {
                                          "request": request,
                                          "errors": [f"총 {total_records}개의 자료 중 {deleted_records}개의 자료가 삭제되었습니다."],
                                          "goto_url": f"/admin/visit_delete",
                                      })


@router.get("/visit_list")
async def visit_list(request: Request, db: Session = Depends(get_db),
                     current_page: int = Query(default=1, alias="page"),  # 페이지
                     from_date: str = Query(default="", alias="fr_date"),  # 시작일
                     to_date: str = Query(default=""),  # 종료일
                     ):
    """
    접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
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
    query = db.query(Visit)
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_list.html", context)


@router.get("/visit_domain")
async def visit_domain(request: Request, db: Session = Depends(get_db),
                       current_page: int = Query(default=1, alias="page"),  # 페이지
                       from_date: str = Query(default="", alias="fr_date"),  # 시작일
                       to_date: str = Query(default=""),  # 종료일
                       ):
    """
    도메인별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    site_url = f"{request.base_url.scheme}://{request.base_url.hostname}"
    if request.base_url.port:
        site_url += f":{request.base_url.port}"
    # referer에서 도메인 필터링
    filtered_visits = []

    for visit in visits:
        # http or https
        match = re.search(r'^http[s]*\S+', visit.vi_referer)
        if not match:
            continue
        if match_group := match.group():
            referer: str = re.sub(r"^(www\.|search\.|dirsearch\.|dir\.search\.|dir\.|kr\.search\.|myhome\.)(.*)",
                                  "\\2", match_group)
            filtered_visits.append({
                "vi_referer": '직접' if referer.startswith(site_url) else referer,
                "count": 1,
            })

    visits = count_by_field(filtered_visits, "vi_referer")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_domain.html", context)


@router.get("/visit_browser")
async def visit_browser(request: Request, db: Session = Depends(get_db),
                        current_page: int = Query(default=1, alias="page"),  # 페이지
                        from_date: str = Query(default="", alias="fr_date"),  # 시작일
                        to_date: str = Query(default=""),  # 종료일
                        ):
    """
    브라우저별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 브라우저별 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "vi_browser": get_browser(visit.vi_agent),
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "vi_browser")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_browser.html", context)


@router.get("/visit_os")
def visit_os(request: Request, db: Session = Depends(get_db),
             current_page: int = Query(default=1, alias="page"),  # 페이지
             from_date: str = Query(default="", alias="fr_date"),  # 시작일
             to_date: str = Query(default=""),  # 종료일
             ):
    """
    브라우저별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 브라우저별 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "vi_os": get_os(visit.vi_agent),
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "vi_os")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_os.html", context)


@router.get("/visit_device")
def visit_device(request: Request, db: Session = Depends(get_db),
                 current_page: int = Query(default=1, alias="page"),  # 페이지
                 from_date: str = Query(default="", alias="fr_date"),  # 시작일
                 to_date: str = Query(default=""),  # 종료일
                 ):
    """
    브라우저별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 브라우저별 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "vi_device": visit.vi_device,
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "vi_device")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_device.html", context)


@router.get("/visit_hour")
def visit_device(request: Request, db: Session = Depends(get_db),
                 current_page: int = Query(default=1, alias="page"),  # 페이지
                 from_date: str = Query(default="", alias="fr_date"),  # 시작일
                 to_date: str = Query(default=""),  # 종료일
                 ):
    """
    시간 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 브라우저별 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "visit_hour": visit.vi_time.strftime("%H"),
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "visit_hour")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_hour.html", context)


@router.get("/visit_weekday")
def visit_device(request: Request, db: Session = Depends(get_db),
                 current_page: int = Query(default=1, alias="page"),  # 페이지
                 from_date: str = Query(default="", alias="fr_date"),  # 시작일
                 to_date: str = Query(default=""),  # 종료일
                 ):
    """
    요일 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 요일별 접속자집계
    korean_week_day = {
        "Mon": "월",
        "Tue": "화",
        "Wed": "수",
        "Thu": "목",
        "Fri": "금",
        "Sat": "토",
        "Sun": "일",
    }
    # todo 다국어 적용시 삭제
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "visit_weekday": korean_week_day[visit.vi_date.today().strftime("%a")],
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "visit_weekday")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_weekday.html", context)


@router.get("/visit_date")
def visit_date(request: Request, db: Session = Depends(get_db),
               current_page: int = Query(default=1, alias="page"),  # 페이지
               from_date: str = Query(default="", alias="fr_date"),  # 시작일
               to_date: str = Query(default=""),  # 종료일
               ):
    """
    일별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "visit_date": visit.vi_date.strftime("%Y-%m-%d"),
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "visit_date")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_date.html", context)


@router.get("/visit_month")
def visit_month(request: Request, db: Session = Depends(get_db),
                current_page: int = Query(default=1, alias="page"),  # 페이지
                from_date: str = Query(default="", alias="fr_date"),  # 시작일
                to_date: str = Query(default=""),  # 종료일
                ):
    """
    월별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "visit_month": visit.vi_date.strftime("%Y-%m"),
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "visit_month")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
        "fr_date": from_date,
        "to_date": to_date,
    }

    return templates.TemplateResponse("visit_month.html", context)


@router.get("/visit_year")
def visit_year(request: Request, db: Session = Depends(get_db),
               current_page: int = Query(default=1, alias="page"),  # 페이지
               from_date: str = Query(default="", alias="fr_date"),  # 시작일
               to_date: str = Query(default=""),  # 종료일
               ):
    """
    월별 접속자집계 목록
    """
    request.session["menu_key"] = VISIT_MENU_KEY
    from_date, to_date = validate_time(from_date, to_date)

    # 초기 쿼리 설정
    query = db.query(Visit).filter(and_(Visit.vi_date > from_date, Visit.vi_date < to_date))
    records_per_page = request.state.config.cf_page_rows
    records_per_page = records_per_page if records_per_page else 10

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()

    # 접속자집계
    filtered_visits = []
    for visit in visits:
        filtered_visits.append({
            "visit_year": visit.vi_date.strftime("%Y"),
            "count": 1,
        })

    visits = count_by_field(filtered_visits, "visit_year")
    visits = add_percent_field(visits)

    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records),
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
