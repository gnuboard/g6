"""API 1 Version Router Module."""
from enum import Enum

from fastapi import APIRouter, Depends

from lib.dependencies import check_use_api
from api.v1.routers import (
    auth, board, member, memo, menu, point, scrap
)


class Tags(Enum):
    """API 태그를 정의합니다."""
    AUTH = "인증"
    MEMBER = "회원"
    MEMO = "쪽지"
    MENU = "메뉴"
    POINT = "포인트"
    SCRAP = "스크랩"
    BOARD = "게시판"


# API 버전 1 라우터를 정의합니다.
router = APIRouter(prefix="/api/v1", dependencies=[Depends(check_use_api)])
router.include_router(auth.router, prefix="", tags=[Tags.AUTH])
router.include_router(member.router, prefix="", tags=[Tags.MEMBER])
router.include_router(memo.router, prefix="/member", tags=[Tags.MEMO])
router.include_router(point.router, prefix="/member", tags=[Tags.POINT])
router.include_router(scrap.router, prefix="/member", tags=[Tags.SCRAP])
router.include_router(board.router, prefix="/board", tags=[Tags.BOARD])
router.include_router(menu.router, prefix="", tags=[Tags.MENU])
