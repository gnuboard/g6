from typing_extensions import Annotated
from fastapi import Request, APIRouter, Depends, Path
from starlette.responses import JSONResponse

from core.formclass import AutoSaveForm
from core.models import Member
from service.ajax import AJAXService

router = APIRouter()


@router.get("/autosave_list")
async def autosave_list(
    request: Request,
    service: Annotated[AJAXService, Depends(AJAXService.async_init)],
):
    """
    자동저장 목록을 반환한다.

    Args:
        request (Request): Request 객체
        service (AJAXService): Ajax 서비스

    Returns:
        List[AutoSave]: 자동저장 목록
    """
    member: Member = request.state.login_member
    service.validate_login(member)
    save_list = service.get_autosave_list(member)
    return save_list


@router.get("/autosave_count")
async def autosave_count(
    request: Request,
    service: Annotated[AJAXService, Depends(AJAXService.async_init)]
):
    """
    자동저장글 개수를 반환한다.

    Args:
        request (Request): Request 객체
        service (AJAXService): Ajax 서비스

    Returns:
        dict: 자동저장글 개수
    """
    member: Member = request.state.login_member
    service.validate_login(member)
    return {"count": service.get_autosave_count(member.mb_id)}


@router.get("/autosave_load/{as_id}")
async def autosave_load(
    request: Request,
    service: Annotated[AJAXService, Depends(AJAXService.async_init)],
    as_id: int = Path(..., title="자동저장 ID")
):
    """
    자동저장 내용을 불러온다.

    Args:
        request (Request): Request 객체
        service (AJAXService): Ajax 서비스
        as_id (int, optional): 자동저장 ID.

    Returns:
        AutoSave: 자동저장 데이터

    Raises:
        JSONException: 로그인이 필요합니다
        JSONException: 저장된 글이 없을 경우
        JSONException: 접근 권한이 없을 경우
    """
    member: Member = request.state.login_member
    service.validate_login(member)
    save_data = service.get_autosave_content(as_id, member)
    return save_data


@router.post("/autosave")
async def autosave(
    request: Request,
    service: Annotated[AJAXService, Depends(AJAXService.async_init)],
    form_data: AutoSaveForm = Depends()
):
    """
    글 임시저장

    Args:
        request (Request): Request 객체
        service (AJAXService): Ajax 서비스
        form_data (AutoSaveForm, optional): 자동저장 데이터.

    Returns:
        JSONResponse: 임시저장글 개수

    Raises:
        JSONException: 로그인이 필요합니다
    """
    member: Member = request.state.login_member
    service.validate_login(member)
    service.autosave_save(member, form_data)
    count = service.get_autosave_count(member.mb_id)
    return JSONResponse(status_code=201, content={"count": count})


@router.delete("/autosave/{as_id}")
async def delete_autosave(
    request: Request,
    service: Annotated[AJAXService, Depends(AJAXService.async_init)],
    as_id: int = Path(..., title="자동저장 ID")
):
    """
    임시저장글 삭제

    Args:
        request (Request): Request 객체
        service (AJAXService): Ajax 서비스
        as_id (int, optional): 자동저장 ID.

    Returns:
        JSONResponse: 삭제되었습니다.

    Raises:
        JSONException: 로그인이 필요합니다
        JSONException: 저장된 글이 없을 경우
        JSONException: 접근 권한이 없을 경우
    """
    member: Member = request.state.login_member
    service.validate_login(member)
    service.autosave_delete(as_id, member)
    return JSONResponse(status_code=200, content="삭제되었습니다.")
