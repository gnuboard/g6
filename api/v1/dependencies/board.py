"""게시판 관련 의존성을 정의합니다."""
from typing_extensions import Annotated
from fastapi import Depends, HTTPException, Request, status, Path
from sqlalchemy import select

from core.database import db_session
from core.models import Member, Board, Group
from lib.common import filter_words, dynamic_create_write_table
from lib.board_lib import BoardConfig
from lib.html_sanitizer import content_sanitizer
from lib.pbkdf2 import create_hash
from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.lib.member import MemberService
from api.v1.models.auth import TokenPayload
from api.v1.models.board import WriteModel


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


def validate_write(
    request: Request,
    write: WriteModel,
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
):
    """
    게시글 작성시 게시글 정보의 유효성을 검사합니다.
    """
    board_config = BoardConfig(request, board)
    
    # 게시글 내용 검증
    subject_filter_word = filter_words(request, write.wr_subject)
    content_filter_word = filter_words(request, write.wr_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise HTTPException(status_code=400, detail=f"제목/내용에 금지단어({word})가 포함되어 있습니다.")

    # Stored XSS 방지
    write.wr_content = content_sanitizer.get_cleaned_data(write.wr_content)

    # 옵션 설정
    options = [opt for opt in [write.html, write.secret, write.mail] if opt]
    write.wr_option = ",".join(map(str, options))

    # 링크 설정
    if not member or board_config.board.bo_link_level > member.mb_level:
        write.wr_link1 = ""
        write.wr_link2 = ""

    write.wr_password = create_hash(write.wr_password) if write.wr_password else ""

    # 작성자명(wr_name) 설정
    if member:
        if board_config.board.bo_use_name:
            write.wr_name =  member.mb_name
        else:
            write.wr_name =  member.mb_nick
    elif not write.wr_name:
        raise HTTPException(status_code=400, detail="로그인 세션 만료, 비회원 글쓰기시 작성자 이름 미기재 등의 비정상적인 접근입니다.")

    write.wr_email = getattr(member, "mb_email", write.wr_email)
    write.wr_homepage = getattr(member, "mb_homepage", write.wr_homepage)

    return write