"""게시판 관련 의존성을 정의합니다."""
from typing_extensions import Annotated, Dict
from fastapi import Depends, HTTPException, Request, status, Path
from sqlalchemy import select

from core.database import db_session
from core.models import Member, Board, Group
from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.lib.member import MemberService
from api.v1.models.auth import TokenPayload


def get_current_member(
    request: Request,
    db: db_session,
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
    member_service = MemberService(request, db, mb_id)
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


def get_member_info(
    member: Member = Depends(get_current_member),
) -> Dict:
    """
    회원 정보를 딕셔너리 형태로 반환합니다.
    """
    mb_id = member.mb_id if member else None
    result = {
        'member': member,
        'mb_id': mb_id,
        'member_level': member.mb_level if member else 1,
    }
    return result


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


def get_group(
    db: db_session,
    gr_id: str = Path(...),
) -> Group:
    """
    게시판그룹 정보를 조회합니다.
    """
    group = db.get(Group, gr_id)
    if not group:
        raise HTTPException(status_code=404, detail="존재하지 않는 게시판그룹입니다.")
    return group