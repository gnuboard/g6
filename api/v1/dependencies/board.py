"""게시판 관련 의존성을 정의합니다."""
from fastapi import HTTPException, Path

from core.database import db_session
from core.models import Board
from lib.common import dynamic_create_write_table


def get_board(
    db: db_session,
    bo_table: str = Path(...),
) -> Board:
    """
    게시판 정보를 조회합니다.
    """
    board = db.get(Board, bo_table)
    if not board:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시판입니다.")
    return board


def get_write(
    db: db_session,
    bo_table: str = Path(...),
    wr_id: str = Path(...),
):
    """
    게시글 정보를 조회합니다.
    """
    if not wr_id.isdigit():
        raise HTTPException(status_code=404, detail=f"{wr_id} : 올바르지 않은 게시글 번호입니다.")

    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시글입니다.")

    return write