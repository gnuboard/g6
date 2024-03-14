from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc

from core.models import Member

from api.v1.models import responses
from api.v1.dependencies.member import get_current_member
from api.v1.models.point import ResponsePointModel

router = APIRouter()


@router.get("/points",
            summary="회원 포인트 내역 목록 조회",
            response_model=List[ResponsePointModel],
            responses={**responses})
async def read_member_points(
    current_member: Annotated[Member, Depends(get_current_member)],
):
    """회원 포인트 내역을 조회합니다."""
    return current_member.points.order_by(desc("po_id")).all()
