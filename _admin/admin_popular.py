from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession
from database import get_db
from common import *

import models

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['get_selected'] = get_selected
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["generate_one_time_token"] = generate_one_time_token

LIST_MENU_KEY = "300300"
RANK_MENU_KEY = "300400"


@router.get("/popular_list")
def popular_list(request: Request, db: DBSession = Depends(get_db),
                 search_params: dict = Depends(common_search_query_params)):
    '''
    인기검색어 목록
    '''
    request.session["menu_key"] = LIST_MENU_KEY

    # 인기검색어 목록 데이터 출력
    keywords = select_query(
        request,
        models.Popular,
        search_params,
        default_sst="pp_id",
        default_sod="desc",
    )

    query_string = generate_query_string(request)
    total_count = keywords['total_count']
    context = {
        "request": request,
        "keywords": keywords['rows'],
        "total_count": total_count,
        "paging": get_paging(request, search_params['current_page'], total_count, f"/admin/popular_list?{query_string}&page="),
    }
    return templates.TemplateResponse("popular_list.html", context)


@router.post("/popular/delete")
def popular_delete(request: Request,
                        db: DBSession = Depends(get_db),
                        checks: List[int] = Form(..., alias="chk[]")):
    '''
    인기검색어 목록 삭제
    '''
    # in 조건을 사용해서 일괄 삭제
    db.query(models.Popular).filter(models.Popular.pp_id.in_(checks)).delete()
    db.commit()
        
    query_string = generate_query_string(request)

    return RedirectResponse(f"/admin/popular_list?{query_string}", status_code=303)



@router.get("/popular_rank")
def popular_rank(request: Request,
                db: DBSession = Depends(get_db),
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
    query_string = f"fr_date={fr_date}&to_date={to_date}"

    # 인기검색어 순위 데이터 출력
    query = db.query(
            models.Popular.pp_word,
            func.count(models.Popular.pp_word).label('search_count'),
            func.rank().over(order_by=desc(text('search_count'))).label('ranking')
        ).filter(
        models.Popular.pp_word != '',
        models.Popular.pp_date >= fr_date,
        models.Popular.pp_date <= to_date
    ).group_by(models.Popular.pp_word).order_by(desc('search_count'), models.Popular.pp_word)

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
        "paging": get_paging(request, current_page, total_count, f"/admin/popular_rank?{query_string}&page="),
    }
    return templates.TemplateResponse("popular_rank.html", context)
