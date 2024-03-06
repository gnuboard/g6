from enum import Enum

from fastapi import APIRouter

from api.v1.routers import auth, member

class Tags(Enum):
    auth = "auth"
    members = "members"

# API 버전 1 라우터를 정의합니다.
router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, prefix="", tags=[Tags.auth])
router.include_router(member.router, prefix="/members", tags=[Tags.members])