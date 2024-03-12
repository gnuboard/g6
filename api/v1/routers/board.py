from typing_extensions import Annotated, Dict

from fastapi import APIRouter, Depends, Request, Path, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from core.database import db_session
from core.models import Board, Group
from lib.member_lib import get_admin_type
from api.v1.dependencies.board import get_member_info, get_group


router = APIRouter()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

@router.get("/group/{gr_id}")
async def api_group_board_list(
    request: Request,
    db: db_session,
    member_info: Annotated[Dict, Depends(get_member_info)],
    gr_id: str = Path(...),
    group: Group = Depends(get_group),
) -> Dict:
    """
    게시판그룹의 모든 게시판 목록을 보여줍니다.
    """
    mb_id = member_info["mb_id"]
    member_level = member_info["member_level"]
    admin_type = get_admin_type(request, mb_id, group=group)

    # 그룹별 게시판 목록 조회
    query = (
        select(Board)
        .where(
            Board.gr_id == gr_id,
            Board.bo_list_level <= member_level,
            Board.bo_device != 'mobile'
        )
        .order_by(Board.bo_order)
    )
    # 인증게시판 제외
    if not admin_type:
        query = query.filter_by(bo_use_cert="")

    boards = db.scalars(query).all()
    return jsonable_encoder({"group": group, "boards": boards})