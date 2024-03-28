"""게시판 관련 의존성을 정의합니다."""
from typing_extensions import Annotated, Dict
from fastapi import Depends, HTTPException, Request, status, Path
from sqlalchemy import select

from core.database import db_session
from core.models import Member, Board, Group, WriteBaseModel
from lib.common import filter_words, dynamic_create_write_table
from lib.board_lib import BoardConfig, is_owner
from lib.member_lib import get_admin_type
from lib.html_sanitizer import content_sanitizer
from lib.pbkdf2 import create_hash
from lib.g5_compatibility import G5Compatibility
from lib.template_filters import number_format
from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.lib.member import MemberService
from api.v1.models.auth import TokenPayload
from api.v1.models.board import WriteModel, CommentModel
from api.v1.lib.board import is_possible_level, is_possible_point


def get_current_member(
    request: Request,
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


def get_member_info(
    member: Annotated[Member, Depends(get_current_member)]
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


def validate_update_write(
    member_info: Annotated[Dict, Depends(get_member_info)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
):
    mb_id = member_info["mb_id"]
    if not mb_id:
        raise HTTPException(status_code=403, detail="로그인 후 이용해주세요.")
    
    if not is_owner(write, mb_id):
        raise HTTPException(status_code=403, detail="글을 수정할 권한이 없습니다.")

    return write


def validate_upload_file_write(
    request: Request,
    member_info: Annotated[Dict, Depends(get_member_info)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    board: Annotated[Board, Depends(get_board)],
):
    mb_id = member_info["mb_id"]

    if not mb_id:
        raise HTTPException(status_code=403, detail="로그인 후 이용해주세요.")

    if mb_id != write.mb_id:
        raise HTTPException(status_code=403, detail="자신의 글에만 파일을 업로드할 수 있습니다.")

    if not is_possible_level(request, member_info, board, "bo_upload_level"):
        raise HTTPException(status_code=403, detail="파일 업로드 권한이 없습니다.")

    return write


def get_parent_write(
    db: db_session,
    wr_parent: int = Path(...),
    bo_table: str = Path(...),
):
    write_model = dynamic_create_write_table(bo_table)
    parent_write = db.get(write_model, wr_parent)
    if not parent_write:
        raise HTTPException(status_code=404, detail=f"{wr_parent} : 존재하지 않는 게시글입니다.")
    return parent_write


def validate_comment(
    request: Request,
    db: db_session,
    comment: CommentModel,
    member_info: Annotated[Dict, Depends(get_member_info)],
    parent_write: Annotated[WriteBaseModel, Depends(get_parent_write)],
    board: Annotated[Board, Depends(get_board)],
    bo_table: str = Path(...),
    wr_parent: int = Path,
):
    config = request.state.config
    board_config = BoardConfig(request, board)
    compatible_instance = G5Compatibility(db)
    member = member_info['member']
    mb_id = member_info['mb_id'] or ""
    admin_type = get_admin_type(request, mb_id, board=board)

    if not any([
        admin_type,
        is_possible_level(request, member_info, board, "bo_comment_level"),
    ]):
        raise HTTPException(status_code=403, detail="댓글을 작성할 권한이 없습니다.")
    
    # 포인트 검사
    comment_point = board.bo_comment_point
    if config.cf_use_point:
        if not any([
            admin_type,
            is_possible_point(member_info, comment_point),
        ]):
            point = number_format(abs(comment_point))
            message = f"댓글 작성에 필요한 포인트({point})가 부족합니다."
            if not member:
                message += f"로그인 후 다시 시도해주세요."
            raise HTTPException(status_code=403, detail=message)

    write_model = dynamic_create_write_table(bo_table)
    now = compatible_instance.get_wr_last_now(write_model.__tablename__)

    filter_word = filter_words(request, comment.wr_content)
    if filter_word:
        raise HTTPException(status_code=400, detail=f"내용에 금지단어({filter_word})가 포함되어 있습니다.")

    # 작성자명(wr_name), 비밀번호(wr_password) 설정
    if member:
        if board_config.board.bo_use_name:
            comment.wr_name =  member.mb_name
        else:
            comment.wr_name =  member.mb_nick
    elif not comment.wr_name:
        raise HTTPException(status_code=400, detail="wr_name: 비회원 글쓰기시 작성자 이름을 기재해야 합니다.")
    elif not comment.wr_password:
        raise HTTPException(status_code=400, detail="wr_password: 비회원 글쓰기시 비밀번호를 기재해야 합니다.")
    
    comment.ca_name = parent_write.ca_name
    comment.wr_num = parent_write.wr_num
    comment.wr_parent = wr_parent
    # Stored XSS 방지
    comment.wr_content = content_sanitizer.get_cleaned_data(comment.wr_content)
    comment.mb_id = mb_id
    comment.wr_password = create_hash(comment.wr_password) if comment.wr_password else ""
    comment.wr_email = getattr(member, "mb_email", "")
    comment.wr_homepage = getattr(member, "mb_homepage", "")
    comment.wr_datetime = comment.wr_last = now
    comment.wr_ip = request.client.host

    return comment


def validate_update_comment(
    request: Request,
    db: db_session,
    comment_data: CommentModel,
    member_info: Annotated[Dict, Depends(get_member_info)],
    bo_table: str = Path(...),
    wr_id: int = Path,
):
    member = member_info['member']

    write_model = dynamic_create_write_table(bo_table)

    filter_word = filter_words(request, comment_data.wr_content)
    if filter_word:
        raise HTTPException(status_code=400, detail=f"내용에 금지단어({filter_word})가 포함되어 있습니다.")

    # 작성자명(wr_name), 비밀번호(wr_password) 설정
    if not member:
        raise HTTPException(status_code=400, detail="wr_name: 비회원은 댓글 수정이 불가능합니다.")
    
    comment = db.get(write_model, wr_id)
    if not comment:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 댓글입니다.")
    
    writer_id = comment.mb_id
    if member.mb_id != writer_id:
        raise HTTPException(status_code=403, detail="댓글을 수정할 권한이 없습니다.")
    
    comment_data.wr_content = content_sanitizer.get_cleaned_data(comment_data.wr_content)

    return comment_data


def validate_delete_comment(
    db: db_session,
    bo_table: str = Path(...),
    wr_id: str = Path(...),
):
    write_model = dynamic_create_write_table(bo_table)
    comment = db.get(write_model, wr_id)
    if not comment:
        raise HTTPException(status_code=404, detail=f"{wr_id} : 존재하지 않는 댓글입니다.")
    
    if not comment.wr_is_comment:
        raise HTTPException(status_code=400, detail=f"{wr_id} : 댓글이 아닌 게시글입니다.")

    return comment