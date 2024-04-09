"""스크랩 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends

from core.models import Board, Member, WriteBaseModel
from lib.dependencies import get_board, get_write
from lib.dependency.auth import get_login_member
from lib.service.scrap_service import ValidateScrapService


def validate_create_scrap(
    member: Annotated[Member, Depends(get_login_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    validate: Annotated[ValidateScrapService, Depends()]
) -> None:
    """스크랩 생성 유효성 검사"""
    validate.is_exists_scrap(member, board.bo_table, write.wr_id)
