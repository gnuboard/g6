"""API 1 Version Router Module."""
from fastapi import APIRouter, Depends

from lib.dependency.dependencies import check_use_api
from api.v1.models import Tags
from api.v1.routers import (
    auth, board, config, content, faq, member, memo, menu, point, poll, qa,
    scrap, search, board_new, ajax_good, ajax_autosave, visit
)


# API 버전 1 라우터를 정의합니다.
router = APIRouter(prefix="/api/v1", dependencies=[Depends(check_use_api)])
router.include_router(auth.router, tags=[Tags.AUTH])
router.include_router(board.router, prefix="/board", tags=[Tags.BOARD])
router.include_router(config.router, tags=[Tags.CONFIG])
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
router.include_router(ajax_autosave.router, prefix="/ajax", tags=[Tags.AJAX_AUTOSAVE])
router.include_router(visit.router, tags=[Tags.VISIT])
