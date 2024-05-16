"""메뉴 API Router."""
from typing import List
from typing_extensions import Annotated
from fastapi import APIRouter, Depends

from api.v1.models.menu import MenuResponse
from api.v1.models.response import response_500
from service.menu_service import MenuService

router = APIRouter()


@router.get("/menus",
            summary="메뉴 목록 조회",
            responses={**response_500})
async def read_menus(
    menu_service: Annotated[MenuService, Depends()],
) -> List[MenuResponse]:
    """
    메인/서브 메뉴 목록을 조회합니다.
    - LRU(Least Recently Used)캐시를 사용하여 조회합니다.
    """
    return menu_service.fetch_menus()
