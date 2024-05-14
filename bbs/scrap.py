"""스크랩 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.formclass import WriteCommentForm
from core.models import Board, Member, Scrap, WriteBaseModel
from core.template import UserTemplates
from lib.board_lib import insert_board_new, set_write_delay
from lib.common import get_paging_info, remove_query_params, set_url_query_params
from lib.dependency.board import get_board, get_write
from lib.dependency.dependencies import validate_token
from lib.dependency.auth import get_login_member
from lib.dependency.scrap import (
    get_scrap, validate_create_scrap, validate_delete_scrap
)
from lib.template_filters import datetime_format
from lib.template_functions import get_paging
from service.point_service import PointService
from service.scrap_service import ScrapService
from service.board.update_post import CommentService

router = APIRouter()
templates = UserTemplates()
templates.env.filters["datetime_format"] = datetime_format


@router.get("/scrap_popin/{bo_table}/{wr_id}",
            dependencies=[Depends(validate_create_scrap)])
async def scrap_form(
    request: Request,
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
):
    """
    스크랩 등록 폼(팝업창)
    """
    context = {
        "request": request,
        "bo_table": board.bo_table,
        "write": write,
    }
    return templates.TemplateResponse("bbs/scrap_popin.html", context)


@router.post("/scrap_popin_update/{bo_table}/{wr_id}",
             dependencies=[Depends(validate_create_scrap),
                           Depends(validate_token)])
async def scrap_form_update(
    request: Request,
    db: db_session,
    point_service: Annotated[PointService, Depends()],
    scrap_service: Annotated[ScrapService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    wr_content: str = Form(None),
):
    """
    회원 스크랩 등록
    """
    bo_table = board.bo_table
    wr_id = write.wr_id

    scrap_service.create_scrap(member, bo_table, wr_id)
    scrap_service.update_scrap_count(member)

    #댓글 생성
    if wr_content:
        comment_service = CommentService(request, db, point_service, bo_table, wr_id)
        form = WriteCommentForm(w="w", wr_id=wr_id, wr_content=wr_content,
                                wr_name=None, wr_password=None, wr_secret=None,
                                comment_id=0)
        comment_service.validate_write_delay()
        comment_service.validate_comment_level()
        comment_service.validate_point()
        comment_service.validate_post_content(wr_content)
        comment = comment_service.save_comment(form, write)
        comment_service.add_point(comment)
        comment_service.send_write_mail_(comment, write)
        insert_board_new(bo_table, comment)
        set_write_delay(request)

    return RedirectResponse(request.url_for('scrap_list'), 302)


@router.get("/scrap")
async def scrap_list(
    request: Request,
    scrap_service: Annotated[ScrapService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    current_page: int = Query(default=1, alias="page")
):
    """
    스크랩 목록
    """
    config = request.state.config
    page_rows = getattr(config, "cf_page_rows", 10)

    total_records = scrap_service.fetch_total_records(member)
    paging_info = get_paging_info(current_page, page_rows, total_records)
    scraps = scrap_service.fetch_scraps(member,
                                        paging_info["offset"], page_rows)
    scraps = scrap_service.set_subjects(scraps)

    for scrap in scraps:
        scrap.num = (total_records
                     - paging_info["offset"]
                     - (scraps.index(scrap)))

    context = {
        "request": request,
        "scraps": scraps,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("bbs/scrap_list.html", context)


@router.get("/scrap_delete/{ms_id}",
            dependencies=[Depends(validate_delete_scrap),
                          Depends(validate_token)])
async def scrap_delete(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    scrap_service: Annotated[ScrapService, Depends()],
    scrap: Annotated[Scrap, Depends(get_scrap)],
):
    """
    스크랩 삭제
    """
    scrap_service.delete_scrap(scrap)
    scrap_service.update_scrap_count(member)

    url = request.url_for('scrap_list').path
    query_params = remove_query_params(request, "token")
    return RedirectResponse(set_url_query_params(url, query_params), 302)
