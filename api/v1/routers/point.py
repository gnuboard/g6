from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc

from core.models import Member

from api.v1.models import responses
from api.v1.dependencies.member import get_current_member
from api.v1.models.point import ResponsePointModel

router = APIRouter()


@router.get("/{mb_id}/points",
            summary="회원 포인트 내역 목록 조회",
            response_model=List[ResponsePointModel],
            responses={**responses})
async def read_member_points(
    mb_id: str,
    current_member: Annotated[Member, Depends(get_current_member)],
):
    """회원 포인트 내역을 조회합니다."""
    if mb_id != current_member.mb_id:
        raise HTTPException(status_code=403, detail="본인의 회원정보만 조회할 수 있습니다.")

    return current_member.points.order_by(desc("po_id")).all()