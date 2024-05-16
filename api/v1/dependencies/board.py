"""게시판 관련 의존성을 정의합니다."""
from typing_extensions import Annotated
from fastapi import HTTPException, Path, UploadFile, File, Form

from core.database import db_session
from core.models import Board
from lib.common import dynamic_create_write_table


def get_board(
    db: db_session,
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
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
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
    wr_id: int = Path(..., title="글 아이디", description="글 아이디"),
):
    """
    게시글 정보를 조회합니다.
    """
    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시글입니다.")

    return write


def arange_file_data(
    file1: Annotated[UploadFile, File(title="첨부파일1")] = None,
    file2: Annotated[UploadFile, File(title="첨부파일2")] = None,
    file_content1: Annotated[str, Form(title="첨부파일1 내용")] = None,
    file_content2: Annotated[str, Form(title="첨부파일2 내용")] = None,
    file_del1: Annotated[int, Form(title="첨부파일1 삭제 여부")] = None,
    file_del2: Annotated[int, Form(title="첨부파일2 삭제 여부")] = None,
) -> dict:
    """업로드 파일의 데이터를 딕셔너리 형태로 반환합니다."""
    return {
        "files": [file1, file2],
        "file_contents": [file_content1, file_content2],
        "file_dels": [file_del1, file_del2],
    }