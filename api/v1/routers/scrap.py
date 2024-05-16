"""스크랩 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from core.database import db_session
from core.formclass import WriteCommentForm
from core.models import Board, Member, Scrap, WriteBaseModel
from lib.board_lib import insert_board_new, set_write_delay
from lib.common import get_paging_info

from api.v1.service.point import PointServiceAPI
from api.v1.dependencies.board import get_board, get_write
from api.v1.dependencies.member import get_current_member
from api.v1.dependencies.scrap import (
    get_scrap, validate_create_scrap, validate_delete_scrap
)
from api.v1.service.scrap import ScrapServiceAPI
from api.v1.service.board import CommentServiceAPI
from api.v1.models.pagination import PagenationRequest
from api.v1.models.response import (
    MessageResponse, response_401, response_403, response_404, response_409,
    response_422, response_500,
)
from api.v1.models.scrap import CreateScrap, ScrapFormResponse, ScrapListResponse

router = APIRouter()


@router.get("/scraps",
            summary="회원 스크랩 목록 조회",
            responses={**response_401, **response_403,
                       **response_422, **response_500})
async def read_member_scraps(
    service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[PagenationRequest, Depends()]
) -> ScrapListResponse:
    """회원 스크랩 목록을 조회합니다."""
    total_records = service.fetch_total_records(member)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    scraps = service.fetch_scraps(member,data.offset, data.per_page)
    scraps = service.set_subjects(scraps)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "scraps": scraps
    }


@router.get("/scraps/{bo_table}/{wr_id}",
            dependencies=[Depends(get_current_member),
                          Depends(validate_create_scrap)],
            summary="회원 스크랩 등록 페이지 설정 조회",
            responses={**response_403, **response_404, **response_409})
async def scrap_form_api(
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
) -> ScrapFormResponse:
    """
    스크랩 등록 페이지의 정보를 조회합니다.
    - 게시판 정보
    - 게시글 정보
    """
    return {
        "board": board,
        "write": write,
    }


@router.post("/scraps/{bo_table}/{wr_id}",
             dependencies=[Depends(validate_create_scrap)],
             summary="회원 스크랩 등록",
             responses={**response_401, **response_403,
                        **response_409, **response_422})
async def create_member_scrap(
    request: Request,
    db: db_session,
    service: Annotated[ScrapServiceAPI, Depends()],
    point_service: Annotated[PointServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    data: CreateScrap
) -> MessageResponse:
    """
    회원 스크랩을 등록합니다.
    - 스크랩을 등록하면 스크랩 카운트가 증가합니다.
    - 댓글을 작성하면 댓글도 함께 등록됩니다.

    ### Request Body
    - **wr_content**: 스크랩 추가 시, 함께 등록할 댓글 내용
    """
    bo_table = board.bo_table
    wr_id = write.wr_id

    service.create_scrap(member, bo_table, wr_id)
    service.update_scrap_count(member)

    #댓글 생성
    if data.wr_content:
        db.refresh(member)
        comment_service = CommentServiceAPI(request, db, point_service, bo_table, wr_id, member)
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

    return {"message": "스크랩을 추가하였습니다."}


@router.delete("/scraps/{ms_id}",
               dependencies=[Depends(validate_delete_scrap)],
               summary="회원 스크랩 삭제",
               responses={**response_401, **response_403, **response_404})
async def delete_member_scrap(
    service: Annotated[ScrapServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    scrap: Annotated[Scrap, Depends(get_scrap)]
) -> MessageResponse:
    """
    회원 스크랩을 삭제합니다.
    - 스크랩을 삭제하면 스크랩 카운트가 감소합니다.
    """
    service.delete_scrap(scrap)
    service.update_scrap_count(member)

    return {"message": "스크랩을 삭제하였습니다."}
