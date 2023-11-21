from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session

from common import *
from database import get_db
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from models import Popular

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['get_selected'] = get_selected
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["generate_token"] = generate_token

LIST_MENU_KEY = "300300"
RANK_MENU_KEY = "300400"


@router.get("/popular_list")
def popular_list(request: Request, db: Session = Depends(get_db),
                 search_params: dict = Depends(common_search_query_params)):
    '''
    인기검색어 목록
    '''
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


@router.post("/popular/delete")
def popular_delete(request: Request,
                    token: str = Form(None),
                    db: Session = Depends(get_db),
                    checks: List[int] = Form(..., alias="chk[]")):
    '''
    인기검색어 목록 삭제
    '''
    if not compare_token(request, token, 'delete'):
        raise AlertException(status_code=403, detail="토큰이 유효하지 않습니다.")

    # in 조건을 사용해서 일괄 삭제
    db.query(Popular).filter(Popular.pp_id.in_(checks)).delete()
    db.commit()

    # 기존 캐시 삭제
    popular_cache.update({"populars": None})
        
    query_string = generate_query_string(request)

    return RedirectResponse(f"/admin/popular_list?{query_string}", status_code=303)



@router.get("/popular_rank")
def popular_rank(request: Request,
                db: Session = Depends(get_db),
                fr_date: str = Query(default=str(datetime.now().date())),
                to_date: str = Query(default=str(datetime.now().date())),
                current_page: int = Query(default=1, alias="page")
                ):
    '''
    인기검색어 순위
    '''
    request.session["menu_key"] = RANK_MENU_KEY

    fr_date = re.sub(r'[^0-9 :\-]', '', fr_date)
    to_date = re.sub(r'[^0-9 :\-]', '', to_date)

    # 인기검색어 순위 데이터 출력
    # query = db.query(
    #         Popular.pp_word,
    #         func.count(Popular.pp_word).label('search_count'),
    #         func.rank().over(order_by=desc(text('search_count'))).label('ranking')
    #     ).filter(
    #     Popular.pp_word != '',
    #     Popular.pp_date >= fr_date,
    #     Popular.pp_date <= to_date
    # ).group_by(Popular.pp_word).order_by(desc('search_count'), Popular.pp_word)
    
    subquery = (
        db.query(
            Popular.pp_word,
            func.count(Popular.pp_word).label('search_count')
        )
        .filter(
            Popular.pp_word != '',
            Popular.pp_date >= fr_date,
            Popular.pp_date <= to_date
        )
        .group_by(Popular.pp_word)
        .subquery()
    )

    query = (
        db.query(
            subquery.c.pp_word,
            subquery.c.search_count,
            func.rank().over(order_by=desc(subquery.c.search_count)).label('ranking')
        )
        .order_by(desc(subquery.c.search_count), subquery.c.pp_word)
    )

    total_count = query.count()
    records_per_page = request.state.config.cf_page_rows
    offset = (current_page - 1) * records_per_page
    ranks = query.offset(offset).limit(records_per_page).all()

    context = {
        "request": request,
        "fr_date": fr_date,
        "to_date": to_date,
        "ranks": ranks,
        "total_count": total_count,
        "paging": get_paging(request, current_page, total_count),
    }
    return templates.TemplateResponse("popular_rank.html", context)
