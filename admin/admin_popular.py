from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import aliased

from core.database import db_session
from core.models import Popular
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import common_search_query_params, validate_token
from lib.template_functions import get_paging

router = APIRouter()
templates = AdminTemplates()

LIST_MENU_KEY = "300300"
RANK_MENU_KEY = "300400"


@router.get("/popular_list", tags=["admin_popular_list"])
async def popular_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    인기검색어 목록
    """
    request.session["menu_key"] = LIST_MENU_KEY

    # 인기검색어 목록 데이터 출력
    keywords = select_query(
        request,
        Popular,
        search_params,
        default_sst="pp_id",
        default_sod="desc",
    )

    total_count = keywords['total_count']
    context = {
        "request": request,
        "keywords": keywords['rows'],
        "total_count": total_count,
        "paging": get_paging(request, search_params['current_page'], total_count),
    }
    return templates.TemplateResponse("popular_list.html", context)


@router.post("/popular/delete", dependencies=[Depends(validate_token)], tags=["admin_popular_list"])
async def popular_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(..., alias="chk[]")
):
    """
    인기검색어 목록 삭제
    """
    # in 조건을 사용해서 일괄 삭제
    db.execute(delete(Popular).where(Popular.pp_id.in_(checks)))
    db.commit()

    # 기존 캐시 삭제
    popular_cache.update({"populars": None})

    url = "/admin/popular_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/popular_rank", tags=["admin_popular_rank"])
async def popular_rank(
    request: Request,
    db: db_session,
    fr_date: str = Query(default=str(datetime.now().date())),
    to_date: str = Query(default=str(datetime.now().date())),
    current_page: int = Query(default=1, alias="page")
):
    """
    인기검색어 순위
    """
    request.session["menu_key"] = RANK_MENU_KEY
    config = request.state.config

    records_per_page = getattr(config, "cf_page_rows", 10)
    fr_date = re.sub(r'[^0-9 :\-]', '', fr_date)
    to_date = re.sub(r'[^0-9 :\-]', '', to_date)

    # 인기검색어 순위 데이터 출력
    # 인라인 뷰를 사용해서 인기검색어 순위를 구함
    inline_view = aliased(
        select(
            Popular.pp_word,
            func.count(Popular.pp_word).label('search_count')
        )
        .where(
            Popular.pp_word != '',
            Popular.pp_date >= fr_date,
            Popular.pp_date <= to_date
        )
        .group_by(Popular.pp_word)
        .subquery()
    )
    query = select().order_by(
        desc(inline_view.columns.search_count),
        inline_view.columns.pp_word
    )

    # 페이징 처리
    total_count = db.scalar(query.add_columns(func.count(inline_view.columns.pp_word)).order_by(None))
    offset = (current_page - 1) * records_per_page
    ranks = db.execute(
        query.add_columns(
            inline_view,
            func.dense_rank().over(order_by=desc(inline_view.columns.search_count)).label('ranking')  # 순위
        ).offset(offset).limit(records_per_page)
    ).all()

    context = {
        "request": request,
        "fr_date": fr_date,
        "to_date": to_date,
        "ranks": ranks,
        "total_count": total_count,
        "paging": get_paging(request, current_page, total_count),
    }
    return templates.TemplateResponse("popular_rank.html", context)
