from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.exception import AlertException
from core.models import Member
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import get_write, validate_token
from lib.pbkdf2 import validate_password
from lib.template_filters import default_if_none
from lib.token import create_session_token

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none


@router.get("/password/{action}/{bo_table}/{wr_id}", name="password_page")
async def password(
    request: Request,
    db: db_session,
    write: Annotated[WriteBaseModel, Depends(get_write)],
    action: str = Path(...),
    bo_table: str = Path(...),
):
    """
    게시글/댓글 비밀번호 확인 페이지
    """
    write.subject = write.wr_subject if not write.wr_is_comment else "비밀 댓글"

    context = {
        "request": request,
        "action": action,
        "bo_table": bo_table,
        "write": write,
    }
    return templates.TemplateResponse("/bbs/password.html", context)


@router.post("/password_check/{action}/{bo_table}/{wr_id}", dependencies=[Depends(validate_token)])
async def password_check(
    request: Request,
    db: db_session,
    write: Annotated[WriteBaseModel, Depends(get_write)],
    action: str = Path(...),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    wr_password: str = Form(...)
):
    """
    게시글/댓글 행동 시 비밀번호 확인
    """
    # 게시글/댓글 보기
    if "view" in action:
        # 비밀번호가 없는 회원 게시글은
        # 회원의 비밀번호로 게시글 비밀번호를 설정
        if not write.wr_password:
            write_member = db.scalar(select(Member).filter_by(mb_id=write.mb_id))
            write.wr_password = write_member.mb_password

    # 비밀번호 비교
    if not validate_password(wr_password, write.wr_password):
        raise AlertException(f"비밀번호가 일치하지 않습니다.", 403)

    # 비밀번호 검증 후 처리
    if action == "view":
        request.session[f"ss_secret_{bo_table}_{wr_id}"] = True
        redirect_url = f"/board/{bo_table}/{wr_id}?{request.query_params}"

    elif action == "comment-view":
        request.session[f"ss_secret_comment_{bo_table}_{wr_id}"] = True
        redirect_url = f"/board/{bo_table}/{write.wr_parent}?{request.query_params}#c_{wr_id}"

    elif action == "update":
        request.session[f"ss_edit_{bo_table}_{wr_id}"] = True
        redirect_url = f"/board/write/{bo_table}/{wr_id}?{request.query_params}"

    elif action == "delete":
        token = create_session_token(request)
        request.session[f"ss_delete_{bo_table}_{wr_id}"] = True
        redirect_url = f"/board/delete/{bo_table}/{wr_id}?token={token}&{request.query_params}"

    elif action == "comment-delete":
        token = create_session_token(request)
        request.session[f"ss_delete_comment_{bo_table}_{wr_id}"] = True
        redirect_url = f"/board/delete_comment/{bo_table}/{wr_id}?token={token}&{request.query_params}"

    return RedirectResponse(url=redirect_url, status_code=302)
