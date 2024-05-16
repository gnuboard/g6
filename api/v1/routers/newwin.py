"""레이어 팝업 API Router"""
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends

from api.v1.service.newwin import NewwinServiceAPI
from api.v1.models.newwin import DeviceRequest, NewwinResponse
from api.v1.models.response import response_422, response_500

router = APIRouter()


@router.get("/newwins",
            summary="레이어 팝업 목록 조회",
            responses={**response_422, **response_500})
async def read_newwins(
    service: Annotated[NewwinServiceAPI, Depends(NewwinServiceAPI.async_init)],
    query: Annotated[DeviceRequest, Depends()],
) -> List[NewwinResponse]:
    """
    레이어 팝업 목록을 조회합니다.
    - 표시 기간 내에 있는 팝업만 조회합니다.
    - LFU(Least Frequently Used)캐시를 사용하여 조회합니다.
    """
    return service.fetch_newwins(query.device.value)
