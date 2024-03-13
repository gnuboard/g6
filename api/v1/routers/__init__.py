from enum import Enum

from fastapi import APIRouter

from api.v1.routers import auth, member, memo, point, scrap, board


class Tags(Enum):
    auth = "인증"
    members = "회원"
    memos = "메모"
    points = "포인트"
    scraps = "스크랩"
    board = "게시판"


# API 버전 1 라우터를 정의합니다.
router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, prefix="", tags=[Tags.auth])
router.include_router(member.router, prefix="", tags=[Tags.members])
router.include_router(memo.router, prefix="/member", tags=[Tags.memos])
router.include_router(point.router, prefix="/member", tags=[Tags.points])
router.include_router(scrap.router, prefix="/member", tags=[Tags.scraps])
router.include_router(board.router, prefix="/board", tags=[Tags.board])