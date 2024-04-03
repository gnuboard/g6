"""API 1 Version Router Module."""
from enum import Enum

from fastapi import APIRouter, Depends

from lib.dependencies import check_use_api
from api.v1.routers import (
    auth, board, content, faq, member, memo, menu, point, poll, qa, scrap,
    search, board_new, ajax_good
)


class Tags(Enum):
    """API 태그를 정의합니다."""
    AUTH = "인증"
    BOARD = "게시판"
    CONTENT = "컨텐츠"
    FAQ = "FAQ"
    MEMBER = "회원"
    MEMO = "쪽지"
    MENU = "메뉴"
    POINT = "포인트"
    POLL = "설문조사"
    QA = "Q&A"
    SCRAP = "스크랩"
    SEARCH = "검색"
    BOARD_NEW = "최신글"
    AJAX_GOOD = "좋아요/싫어요"


# API 버전 1 라우터를 정의합니다.
router = APIRouter(prefix="/api/v1", dependencies=[Depends(check_use_api)])
router.include_router(auth.router, tags=[Tags.AUTH])
router.include_router(board.router, prefix="/board", tags=[Tags.BOARD])
router.include_router(content.router, tags=[Tags.CONTENT])
router.include_router(faq.router, tags=[Tags.FAQ])
router.include_router(member.router, tags=[Tags.MEMBER])
router.include_router(memo.router, prefix="/member", tags=[Tags.MEMO])
router.include_router(menu.router, tags=[Tags.MENU])
router.include_router(point.router, prefix="/member", tags=[Tags.POINT])
router.include_router(poll.router, tags=[Tags.POLL])
router.include_router(qa.router, tags=[Tags.QA])
router.include_router(scrap.router, prefix="/member", tags=[Tags.SCRAP])
router.include_router(search.router, prefix="/search", tags=[Tags.SEARCH])
router.include_router(board_new.router, prefix="/board_new", tags=[Tags.BOARD_NEW])
router.include_router(ajax_good.router, prefix="/ajax", tags=[Tags.AJAX_GOOD])