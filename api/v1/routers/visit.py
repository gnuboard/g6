"""방문자 API Router"""
from typing_extensions import Annotated
from fastapi import Depends, Request
from fastapi.routing import APIRouter

from api.v1.service.visit import VisitServiceAPI
from api.v1.models.response import MessageResponse, response_404, response_500
from api.v1.models.visit import VisitTotalResponse
from lib.visit import get_total_visit

router = APIRouter()


@router.get("/visit",
            summary="방문자 집계 조회",
            responses={**response_404, **response_500})
async def read_total_visit(
    request: Request,
) -> VisitTotalResponse:
    """
    현재까지의 방문자 수 집계를 조회합니다.
    - 캐시를 사용하여 10분 동안 캐시된 데이터를 반환합니다.
    - 방문자 수는 기본설정 테이블의 cf_visit 값을 사용합니다.
    """
    config_visit = getattr(request.state.config, "cf_visit", "")
    return get_total_visit(config_visit)


@router.post("/visit",
             summary="방문자 접속 이력 생성",
             responses={**response_404, **response_500})
async def create_visit_record(
    service: Annotated[VisitServiceAPI, Depends()],
) -> MessageResponse:
    """
    방문자 접속 이력을 추가합니다.
    - 이미 방문한 사용자인 경우, 추가되지 않습니다. (IP 중복 방지)

    ### 함께 처리되는 작업
    - 접속 이력 추가
    - 방문자 수 합계 테이블 갱신
    - 기본설정 테이블에 방문자 수 갱신
    """
    visit = service.create_visit_record()
    if not visit:
        return {"message": "이미 방문한 사용자입니다."}

    return {"message": "방문자 접속 이력이 추가되었습니다."}
