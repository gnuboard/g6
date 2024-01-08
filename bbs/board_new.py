from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.models import BoardNew, Board
from core.template import UserTemplates
from lib.board_lib import *
from lib.common import *
from lib.dependencies import validate_token
from lib.point import delete_point, insert_point
from lib.template_functions import get_group_select, get_paging

router = APIRouter()
templates = UserTemplates()
templates.env.globals["get_group_select"] = get_group_select


@router.get("/new")
async def board_new_list(
    request: Request,
    db: db_session,
    gr_id: str = Query(None),
    view: str = Query(None),
    mb_id: str = Query(None),
    current_page: int = Query(1, alias="page")
):
    """
    최신 게시글 목록
    """
    config = request.state.config
    query = select().join(BoardNew.board).order_by(BoardNew.bn_id.desc())
    # 검색조건
    if gr_id:
        query = query.where(Board.gr_id == gr_id)
    if mb_id:
        query = query.where(BoardNew.mb_id == mb_id)
    if view == "write":
        query = query.where(BoardNew.wr_parent == BoardNew.wr_id)
    elif view == "comment":
        query = query.where(BoardNew.wr_parent != BoardNew.wr_id)

    # 페이지 번호에 따른 offset 계산
    page_rows = config.cf_mobile_page_rows if request.state.is_mobile and config.cf_mobile_page_rows else config.cf_new_rows
    offset = (current_page - 1) * page_rows
    # 최종 쿼리 결과를 가져옵니다.
    board_news = db.scalars(query.add_columns(BoardNew).offset(offset).limit(page_rows)).all()
    total_count = db.scalar(query.add_columns(func.count(BoardNew.bn_id)).order_by(None))

    # 결과 데이터 설정
    for new in board_news:
        new.num = total_count - offset - (board_news.index((new)))
        # 게시글 정보 조회
        write_model = dynamic_create_write_table(new.bo_table)
        write = db.get(write_model, new.wr_id)
        if write:
            # 댓글/게시글 구분
            if write.wr_is_comment:
                new.subject = "[댓글] " + write.wr_content[:100]
                new.link = f"/board/{new.bo_table}/{new.wr_parent}#c_{write.wr_id}"
            else:
                new.subject = write.wr_subject
                new.link = f"/board/{new.bo_table}/{new.wr_id}"

            # 작성자
            new.name = cut_name(request, write.wr_name)
            # 시간설정
            new.datetime = format_datetime(write.wr_datetime)

    context = {
        "request": request,
        "total_count": total_count,
        "board_news": board_news,
        "current_page": current_page,
        "paging": get_paging(request, current_page, total_count, page_rows)
    }
    return templates.TemplateResponse("/new/basic/new_list.html", context)


@router.post("/new_delete", dependencies=[Depends(validate_token)])
async def new_delete(
    request: Request,
    db: db_session,
    bn_ids: list = Form(..., alias="chk_bn_id[]"),
):
    """
    게시글을 삭제한다.
    """
    # 새글 정보 조회
    board_news = db.scalars(select(BoardNew).where(BoardNew.bn_id.in_(bn_ids))).all()
    for new in board_news:
        board = db.get(Board, new.bo_table)
        write_model = dynamic_create_write_table(new.bo_table)
        write = db.get(write_model, new.wr_id)

        if write:
            if write.wr_is_comment == 0:
                # 게시글 삭제
                # TODO: 게시글 삭제 공용함수 추가
                db.delete(write)

                # 원글 포인트 삭제
                if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "쓰기"):
                    insert_point(request, write.mb_id, board.bo_write_point * (-1), f"{board.bo_subject} {write.wr_id} 글 삭제")
            else:
                # 댓글 삭제
                # TODO: 댓글 삭제 공용함수 추가
                db.delete(write)

                # 댓글 포인트 삭제
                if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "댓글"):
                    insert_point(request, write.mb_id, board.bo_comment_point * (-1), f"{board.bo_subject} {write.wr_parent}-{write.wr_id} 댓글 삭제")

            # 파일 삭제
            BoardFileManager(board, write.wr_id).delete_board_files()

        # 새글 삭제
        db.delete(new)

        # 최신글 캐시 삭제
        FileCache().delete_prefix(f'latest-{new.bo_table}')

    db.commit()

    url = "/bbs/new"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


def format_datetime(wr_datetime: datetime):
    """
    당일인 경우 시간표시
    """
    current_datetime = datetime.now()

    if wr_datetime.date() == current_datetime.date():
        return wr_datetime.strftime("%H:%M")
    else:
        return wr_datetime.strftime("%y-%m-%d")
