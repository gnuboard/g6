from typing_extensions import Annotated
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
from response_handlers.board_new import BoardNewService

router = APIRouter()
templates = UserTemplates()
templates.env.globals["get_group_select"] = get_group_select


@router.get("/new")
async def board_new_list(
    board_new_service: Annotated[BoardNewService, Depends()],
    gr_id: str = Query(None),
    view: str = Query(None),
    mb_id: str = Query(None),
    current_page: int = Query(1, alias="page")
):
    """
    최신 게시글 목록
    """
    query = board_new_service.get_query(gr_id, mb_id, view)
    offset = board_new_service.get_offset(current_page)
    board_news = board_new_service.get_board_news(query, offset)
    total_count = board_new_service.get_total_count(query)
    board_new_service.arrange_borad_news_data(board_news, total_count, offset)

    context = {
        "request": board_new_service.request,
        "total_count": total_count,
        "board_news": board_news,
        "current_page": current_page,
        "paging": get_paging(board_new_service.request, current_page, total_count, board_new_service.page_rows)
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