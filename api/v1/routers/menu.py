"""메뉴 API Router."""
from typing import List
from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from lib.menu import get_menus
from api.v1.models.menu import MenuResponse
from api.v1.models.response import response_500

router = APIRouter()


@router.get("/menus",
            summary="메뉴 목록 조회",
            responses={**response_500})
async def read_menus() -> List[MenuResponse]:
    """
    메인/서브 메뉴 목록을 조회합니다.
    - LRU(Least Recently Used)캐시를 사용하여 조회합니다.
    """
    try:
        return get_menus()
    except SQLAlchemyError as e:
        return HTTPException(status_code=500, detail=str(e))
