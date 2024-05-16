"""스크랩 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Path

from core.models import Board, Member, Scrap, WriteBaseModel
from lib.dependency.auth import get_login_member
from lib.dependency.board import get_board, get_write
from service.scrap_service import ScrapService, ValidateScrapService


def get_scrap(
    service: Annotated[ScrapService, Depends()],
    ms_id: Annotated[int, Path(..., title="스크랩 ID")]
):
    """스크랩 조회 의존성 함수"""
    return service.read_scrap(ms_id)


def validate_create_scrap(
    validate: Annotated[ValidateScrapService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
) -> None:
    """스크랩 생성 유효성 검사 의존성 함수"""
    validate.is_exists_scrap(member, board.bo_table, write.wr_id)


def validate_delete_scrap(
    validate: Annotated[ValidateScrapService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    scrap: Annotated[Scrap, Depends(get_scrap)],
) -> None:
    """스크랩 삭제 유효성 검사 의존성 함수"""
    validate.is_owner_scrap(scrap, member)
