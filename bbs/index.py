
"""메인 페이지 Template Router"""
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select

from core.database import db_session
from core.models import Board, Group
from core.template import UserTemplates
from lib.template_filters import default_if_none
from service.newwin_service import NewWinService

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none


@router.get("/",
         response_class=HTMLResponse,
         include_in_schema=False)
async def index(
    request: Request,
    db: db_session,
    newwin_service : Annotated[NewWinService, Depends(NewWinService.async_init)]
):
    """
    메인 페이지
    """
    # 게시판 목록 조회
    query_boards = (
        select(Board)
        .join(Board.group)
        .where(Board.bo_device != 'mobile')
        .order_by(
            Group.gr_order,
            Board.bo_order
        )
    )
    # 최고관리자가 아니라면 인증게시판 및 갤러리/공지사항 게시판은 제외
    if not request.state.is_super_admin:
        query_boards = query_boards.where(
            Board.bo_use_cert == '',
            Board.bo_table.notin_(['notice', 'gallery'])
        )
    boards = db.scalars(query_boards).all()

    # 레이어 팝업 목록
    newwins = newwin_service.get_newwins_except_cookie()

    context = {
        "request": request,
        "newwins": newwins,
        "boards": boards,
    }
    return templates.TemplateResponse("/index.html", context)
