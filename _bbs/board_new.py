from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from common import *
from database import get_db
from models import BoardNew, Board

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["get_selected"] = get_selected
templates.env.globals["generate_token"] = generate_token


@router.get("/new")
def board_new_list(
    request: Request,
    db: Session = Depends(get_db),
    gr_id: str = Query(None),
    view: str = Query(None),
    mb_id: str = Query(None),
    current_page: int = Query(1, alias="page")
):
    """
    최신 게시글 목록
    """
    config = request.state.config
    query = db.query(BoardNew, Board).outerjoin(Board, BoardNew.bo_table == Board.bo_table).order_by(BoardNew.bn_id.desc())
    # 검색조건
    if gr_id:
        query = query.filter(Board.gr_id == gr_id)
    if mb_id:
        query = query.filter(BoardNew.mb_id == mb_id)
    if view == "write":
        query = query.filter(BoardNew.wr_parent == BoardNew.wr_id)
    elif view == "comment":
        query = query.filter(BoardNew.wr_parent != BoardNew.wr_id)

    # 페이지 번호에 따른 offset 계산
    page_rows = config.cf_mobile_page_rows if request.state.is_mobile and config.cf_mobile_page_rows else config.cf_page_rows
    offset = (current_page - 1) * page_rows
    # 최종 쿼리 결과를 가져옵니다.
    board_news = query.offset(offset).limit(page_rows).all()
    total_count = query.count()

    # 결과 데이터 설정
    for new, board in board_news:
        new.num = total_count - offset - (board_news.index((new, board)))
        # 게시글 정보 조회
        write_model = dynamic_create_write_table(new.bo_table)
        write = db.query(write_model).filter(write_model.wr_id == new.wr_id).first()

        # 댓글/게시글 구분
        if write.wr_is_comment:
            new.subject = "[댓글] " + write.wr_content[:100]
            new.add_link = f"#c_{write.wr_id}"
        else:
            new.subject = write.wr_subject

        # 작성자
        new.name = write.wr_name
        # 시간설정
        new.datetime = format_datetime(write.wr_datetime)

    context = {
        "request": request,
        "total_count": total_count,
        "board_news": board_news,
        "current_page": current_page,
        "paging": get_paging(request, current_page, total_count)
    }
    return templates.TemplateResponse(f"{request.state.device}/new/basic/new_list.html", context)


@router.post("/new_delete")
def new_delete(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Form(...),
        bn_ids: list = Form(..., alias="chk_bn_id[]"),
    ):
    """
    게시글을 삭제한다.
    """
    # 토큰 검증    
    if not compare_token(request, token, 'new_delete'):
        raise AlertException("잘못된 접근입니다.", 403)
    
    # 새글 정보 조회
    board_news = db.query(BoardNew).filter(BoardNew.bn_id.in_(bn_ids)).all()
    for new in board_news:
        write_model = dynamic_create_write_table(new.bo_table)
        write = db.query(write_model).filter(write_model.wr_id == new.wr_id).first()
        
        if write:
            if write.wr_is_comment == 0:
                # 게시글 삭제 
                # TODO: 게시글 삭제 공용함수 추가
                db.delete(write)
            else:
                # 댓글 삭제
                # TODO: 댓글 삭제 공용함수 추가
                db.delete(write)
        db.delete(new)

        # 최신글 캐시 삭제
        G6FileCache().delete_prefix(f'latest-{new.bo_table}')

    db.commit()
    
    return RedirectResponse(f"/bbs/new", status_code=303)


def format_datetime(wr_datetime: datetime):
    """
    당일인 경우 시간표시
    """
    current_datetime = datetime.now()

    if wr_datetime.date() == current_datetime.date():
        return wr_datetime.strftime("%H:%M")
    else:
        return wr_datetime.strftime("%y-%m-%d")