"""Q&A API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Request

from core.models import Member
from lib.common import get_paging_info
from lib.mail import send_qa_mail
from api.v1.dependencies.member import get_current_member
from api.v1.dependencies.qa import validate_data, validate_upload_file
from api.v1.lib.qa import QaFileServiceAPI, QaServiceAPI
from api.v1.models.response import responses
from api.v1.models.qa import QaContentModel, SearchQaContentModel

router = APIRouter()


@router.get("/qas",
            summary="Q&A 목록 조회",
            # response_model=ResponseMemberModel,
            responses={**responses})
async def read_qa_contents(
    qa_service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    search_data: Annotated[SearchQaContentModel, Depends()]
):
    """Q&A 목록을 조회합니다."""
    total_records = qa_service.fetch_total_records(member, **search_data.__dict__)
    paging_info = get_paging_info(search_data.page, search_data.per_page, total_records)
    qa_contents = qa_service.read_qa_contents(
        member, paging_info["offset"], search_data.per_page, **search_data.__dict__)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "qa_contents": qa_contents
    }


@router.get("/qas/{qa_id}",
            summary="Q&A 상세 조회",
            # response_model=ResponseMemberModel,
            responses={**responses})
async def read_qa(
    qa_service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    qa_id: Annotated[int, Path(..., title="Q&A ID")],
    search_data: Annotated[SearchQaContentModel, Depends()]
):
    """Q&A 1건을 조회합니다."""
    qa_content = qa_service.read_qa_content(member, qa_id)
    answer = qa_service.fetch_qa_answer(qa_id)
    prev_qa, next_qa = qa_service.fetch_prev_next_qa(member, qa_id, **search_data)
    related_qa_contents = qa_service.fetch_related_qa_contents(member, qa_id)

    return {
        "qa_content": qa_content,
        "answer": answer,
        "prev": prev_qa,
        "next": next_qa,
        "related": related_qa_contents,
    }


@router.post("/qas",
             name="create_qa_content",
             summary="Q&A 등록",
             # response_model=ResponseMemberModel,
             responses={**responses})
async def create_qa_content(
    request: Request,
    background_tasks: BackgroundTasks,
    member: Annotated[Member, Depends(get_current_member)],
    qa_service: Annotated[QaServiceAPI, Depends()],
    data: Annotated[QaContentModel, Depends(validate_data)],
):
    """
    Q&A를 등록합니다.
    - 질문 등록 시, 관리자에게 메일 발송
    - 답변글 등록 시, 사용자에게 메일 발송
    """
    qa_content = qa_service.create_qa_content(member, data)

    # Q&A 등록에 대한 안내메일 발송 처리(백그라운드)
    background_tasks.add_task(send_qa_mail, request, qa_content)

    # TODO: SMS 알림 옵션이 활성화 되어있을 경우, SMS 발송 기능 추가 필요
    # if qa_config.qa_use_sms:
    #     pass

    return HTTPException(status_code=200, detail="Q&A 등록이 완료되었습니다.")


@router.put("/qas/{qa_id}",
            summary="Q&A 수정",
            # response_model=ResponseMemberModel,
            responses={**responses})
async def update_qa_content(
    qa_service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    qa_id: Annotated[int, Path(..., title="Q&A ID")],
    data: Annotated[QaContentModel, Depends(validate_data)],
):
    """Q&A를 수정합니다."""
    qa_service.update_qa_content(member, qa_id, data)

    return HTTPException(status_code=200, detail="Q&A 수정이 완료되었습니다.")


# 파일 업로드 기능이 필요한 경우, 아래와 같이 추가
@router.put("/qas/{qa_id}/files",
            summary="Q&A 파일 업로드",
            # response_model=ResponseMemberModel,
            responses={**responses})
async def upload_qa_file(
    member: Annotated[Member, Depends(get_current_member)],
    qa_service: Annotated[QaServiceAPI, Depends()],
    file_service: Annotated[QaFileServiceAPI, Depends()],
    qa_id: Annotated[int, Path(..., title="Q&A ID")],
    data: Annotated[dict, Depends(validate_upload_file)],
):
    """Q&A에 파일을 업로드합니다."""
    qa_content = qa_service.read_qa_content(member, qa_id)
    file_service.upload_qa_file(qa_content, data)

    return HTTPException(status_code=200, detail="Q&A 파일 업로드가 완료되었습니다.")


@router.delete("/qas/{qa_id}",
               summary="Q&A 삭제",
               # response_model=ResponseMemberModel,
               responses={**responses})
async def delete_qa_content(
    qa_service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    qa_id: Annotated[int, Path(..., title="Q&A ID")],
):
    """Q&A를 삭제합니다."""
    qa_service.delete_qa_content(member, qa_id)

    return HTTPException(status_code=200, detail="Q&A 삭제가 완료되었습니다.")
