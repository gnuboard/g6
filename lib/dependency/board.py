import os
from typing_extensions import Annotated

from fastapi import Depends, Form, Path
from core.database import db_session
from core.exception import AlertException
from core.models import Board
from lib.common import dynamic_create_write_table


def get_variery_board(
        board_path: Annotated[str, Path(alias="bo_table")] = None,
        board_form: Annotated[str, Form(alias="bo_table")] = None,
):
    """
    요청 매개변수의 유형별 bo_table을 수신, 하나의 bo_table 값만 반환
    - 함수의 매개변수 순서대로 우선순위를 가짐
    """
    return board_path or board_form


def get_board(db: db_session, bo_table: Annotated[str, Depends(get_variery_board)]):
    """게시판 존재 여부 검사 & 반환"""
    board = db.get(Board, bo_table)
    if not board:
        raise AlertException(f"{bo_table} : 존재하지 않는 게시판입니다.", 404)

    return board


def get_variery_wr_id(
        wr_id_path: Annotated[str, Path(alias="wr_id")] = None,
        wr_id_form: Annotated[str, Form(alias="wr_id")] = None,
):
    """
    요청 매개변수의 유형별 wr_id를 수신, 하나의 wr_id 값만 반환
    - 함수의 매개변수 순서대로 우선순위를 가짐
    """
    return wr_id_path or wr_id_form


async def get_write(db: db_session, 
              bo_table: Annotated[str, Path(...)],
              wr_id: Annotated[int, Depends(get_variery_wr_id)]):
    """게시글 존재 여부 검사 & 반환"""
    if not wr_id.isdigit():
        raise AlertException(f"{wr_id} : 올바르지 않은 게시글 번호입니다.", 404)

    write_model = dynamic_create_write_table(bo_table)
    write = db.get(write_model, wr_id)
    if not write:
        raise AlertException(f"{wr_id} : 존재하지 않는 게시글입니다.", 404)

    return write
