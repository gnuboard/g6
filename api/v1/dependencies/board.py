"""게시판 관련 의존성을 정의합니다."""
from typing_extensions import Annotated
from fastapi import Depends, HTTPException, status, Path
from sqlalchemy import select

from core.database import db_session
from core.models import Member, Board
from lib.common import dynamic_create_write_table
from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.lib.member import MemberService
from api.v1.models.auth import TokenPayload


def get_current_member(
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    token: Annotated[str, Depends(oauth2_scheme)]
) -> Member:
    """
    현재 로그인한 회원 정보를 조회합니다.
    비회원 글쓰기의 경우 request headers를 {"Authorization": "Bearer Anonymous"}로 전송합니다.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token == "Anonymous":
        return None
    
    payload: TokenPayload = JWT.decode_token(
        token,
        SETTINGS.ACCESS_TOKEN_SECRET_KEY
    )

    mb_id: str = payload.sub
    if mb_id is None:
        raise credentials_exception

    member = db.scalar(select(Member).where(Member.mb_id == mb_id))
    if member is None:
        raise credentials_exception

    is_active, active_detail = member_service.is_activated(member)
    if not is_active:
        credentials_exception.detail = active_detail
        raise credentials_exception

    is_email_certified, email_detail = member_service.is_member_email_certified(member)
    if not is_email_certified:
        credentials_exception.detail = email_detail
        raise credentials_exception

    return member


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