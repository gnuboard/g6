"""스크랩 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from core.database import db_session
from core.formclass import WriteCommentForm
from core.models import Board, Member, Scrap, WriteBaseModel
from lib.board_lib import insert_board_new, set_write_delay
from lib.common import get_paging_info

from api.v1.dependencies.board import get_board, get_write
from api.v1.dependencies.member import get_current_member
from api.v1.dependencies.scrap import (
    get_scrap, validate_create_scrap, validate_delete_scrap
)
from api.v1.lib.scrap import ScrapServiceAPI
from api.v1.models import ViewPageModel, responses
from api.v1.models.scrap import CreateScrapModel, ResponseScrapListModel
from service.board.update_post import CommentServiceAPI

router = APIRouter()


@router.get("/scraps",
            summary="회원 스크랩 목록 조회",
            response_model=ResponseScrapListModel,
            responses={**responses})
async def read_member_scraps(
    scrap_service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[ViewPageModel, Depends()]
):
    """회원 스크랩 목록을 조회합니다."""
    total_records = scrap_service.fetch_total_records(member)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    scraps = scrap_service.fetch_scraps(member,
                                        paging_info["offset"], data.per_page)
    scraps = scrap_service.set_subjects(scraps)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "scraps": scraps
    }


@router.get("/scraps/{bo_table}/{wr_id}",
            dependencies=[Depends(validate_create_scrap)],
            summary="회원 스크랩 등록 페이지 설정 조회")
async def scrap_form(
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
):
    """
    스크랩 등록 페이지의 정보를 조회합니다.
    """
    return {
        "board": board,
        "write": write,
    }


@router.post("/scraps/{bo_table}/{wr_id}",
             dependencies=[Depends(validate_create_scrap)],
             summary="회원 스크랩 등록",
             responses={**responses})
async def create_member_scrap(
    request: Request,
    db: db_session,
    scrap_service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    data: CreateScrapModel
):
    """
    회원 스크랩 등록
    """
    bo_table = board.bo_table
    wr_id = write.wr_id

    scrap_service.create_scrap(member, bo_table, wr_id)
    scrap_service.update_scrap_count(member)

    #댓글 생성
    if data.wr_content:
        comment_service = CommentServiceAPI(request, db, bo_table, member, wr_id)
        form = WriteCommentForm(w="w", wr_id=wr_id, wr_content=data.wr_content,
                                wr_name=None, wr_password=None, wr_secret=None,
                                comment_id=0)
        comment_service.validate_write_delay()
        comment_service.validate_comment_level()
        comment_service.validate_point()
        comment_service.validate_post_content(data.wr_content)
        comment = comment_service.save_comment(form, write)
        comment_service.add_point(comment)
        comment_service.send_write_mail_(comment, write)
        insert_board_new(bo_table, comment)
        set_write_delay(request)

    return {"detail": "스크랩을 추가하였습니다."}


@router.delete("/scraps/{ms_id}",
               dependencies=[Depends(validate_delete_scrap)],
               summary="회원 스크랩 삭제",
               responses={**responses})
async def delete_member_scrap(
    scrap_service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    scrap: Annotated[Scrap, Depends(get_scrap)]
):
    """회원 스크랩을 삭제합니다."""
    scrap_service.delete_scrap(scrap)
    scrap_service.update_scrap_count(member)

    return {"detail": "스크랩을 삭제하였습니다."}
