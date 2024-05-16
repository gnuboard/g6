"""Q&A API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from core.models import Member, QaContent
from lib.common import get_paging_info
from lib.mail import send_qa_mail
from api.v1.dependencies.member import get_current_member
from api.v1.dependencies.qa import get_qa_content, validate_data, validate_upload_file
from api.v1.service.qa import QaConfigServiceAPI, QaFileServiceAPI, QaServiceAPI
from api.v1.models.response import (
    MessageResponse, response_401, response_403, response_404, response_422, response_500
)
from api.v1.models.qa import (
    QaConfigResponse, QaContentData, QaContentListResponse, QaContentList, QaContentResponse
)

router = APIRouter()


@router.get("/qa/config",
            summary="Q&A 설정 조회",
            responses={**response_500})
async def read_qa_config(
    service: Annotated[QaConfigServiceAPI, Depends()]
) -> QaConfigResponse:
    """Q&A 페이지에서 필요한 설정을 조회합니다."""
    return service.qa_config


@router.get("/qas",
            summary="Q&A 목록 조회",
            responses={**response_401, **response_403, **response_422})
async def read_qa_contents(
    service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    search: Annotated[QaContentList, Depends()]
) -> QaContentListResponse:
    """인증된 회원의 Q&A 목록을 조회합니다."""
    total_records = service.fetch_total_records(member, **search.__dict__)
    paging_info = get_paging_info(search.page, search.per_page, total_records)
    qa_contents = service.read_qa_contents(member, search.offset,
                                           search.per_page, **search.__dict__)
    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "qa_contents": qa_contents
    }


@router.get("/qas/{qa_id}",
            summary="Q&A 상세 조회",
            responses={**response_401, **response_403,
                       **response_404, **response_422})
async def read_qa(
    service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    qa_content: Annotated[QaContent, Depends(get_qa_content)],
    search: Annotated[QaContentList, Depends()]
) -> QaContentResponse:
    """인증된 회원의 Q&A 1건을 조회합니다."""
    qa_id = qa_content.qa_id
    answer = service.fetch_qa_answer(qa_id)
    prev_qa, next_qa = service.fetch_prev_next_qa(member, qa_id, **search.__dict__)
    related_qa_contents = service.fetch_related_qa_contents(member, qa_id)

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
             responses={**response_401, **response_403, **response_422})
async def create_qa_content(
    request: Request,
    background_tasks: BackgroundTasks,
    member: Annotated[Member, Depends(get_current_member)],
    service: Annotated[QaServiceAPI, Depends()],
    data: Annotated[QaContentData, Depends(validate_data)],
) -> MessageResponse:
    """
    Q&A를 등록합니다.
    - 질문 등록 시, 관리자에게 메일 발송
    - 답변글 등록 시, 사용자에게 메일 발송

    ### Request Body
    - **qa_subject**: 제목
    - **qa_content**: 내용
    - **qa_related**: 관련 Q&A ID
    - **qa_email**: 이메일 주소
    - **qa_hp**: 휴대폰 번호
    - **qa_email_recv**: 이메일 수신 여부 
    - **qa_sms_recv**: SMS 수신 여부
    - **qa_html**: HTML 사용 여부
    - **qa_1**: 여분필드1
    - **qa_2**: 여분필드2
    - **qa_3**: 여분필드3
    - **qa_4**: 여분필드4
    - **qa_5**: 여분필드5
    """
    qa_content = service.create_qa_content(member, data)

    # Q&A 등록에 대한 안내메일 발송 처리(백그라운드)
    background_tasks.add_task(send_qa_mail, request, qa_content)

    # TODO: SMS 알림 옵션이 활성화 되어있을 경우, SMS 발송 기능 추가 필요
    # if qa_config.qa_use_sms:
    #     pass

    return {
        "message": "Q&A 등록이 완료되었습니다.",
    }


@router.put("/qas/{qa_id}",
            summary="Q&A 수정",
            responses={**response_401, **response_403,
                       **response_404, **response_422})
async def update_qa_content(
    service: Annotated[QaServiceAPI, Depends()],
    qa_content: Annotated[QaContent, Depends(get_qa_content)],
    data: Annotated[QaContentData, Depends(validate_data)],
) -> MessageResponse:
    """
    Q&A를 수정합니다.

    ### Request Body
    - **qa_subject**: 제목
    - **qa_content**: 내용
    - **qa_related**: 관련 Q&A ID
    - **qa_email**: 이메일 주소
    - **qa_hp**: 휴대폰 번호
    - **qa_email_recv**: 이메일 수신 여부 
    - **qa_sms_recv**: SMS 수신 여부
    - **qa_html**: HTML 사용 여부
    - **qa_1**: 여분필드1
    - **qa_2**: 여분필드2
    - **qa_3**: 여분필드3
    - **qa_4**: 여분필드4
    - **qa_5**: 여분필드5
    """
    service.update_qa_content(qa_content, data)

    return {
        "message": "Q&A 수정이 완료되었습니다.",
    }


@router.put("/qas/{qa_id}/files",
            summary="Q&A 파일 업로드",
            responses={**response_401, **response_403,
                       **response_404, **response_422})
async def upload_qa_file(
    service: Annotated[QaFileServiceAPI, Depends()],
    qa_content: Annotated[QaContent, Depends(get_qa_content)],
    data: Annotated[dict, Depends(validate_upload_file)],
) -> MessageResponse:
    """
    Q&A에 파일을 업로드합니다.

    ### Request Body
    - **file1**: 첨부파일1
    - **file2**: 첨부파일2
    - **file_del1**: 첨부파일1 삭제 여부
    - **file_del2**: 첨부파일2 삭제 여부
    """
    service.upload_qa_file(qa_content, data)

    return {
        "message": "Q&A 파일 업로드가 완료되었습니다.",
    }


@router.delete("/qas/{qa_id}",
               summary="Q&A 삭제",
               responses={**response_401, **response_403, **response_404})
async def delete_qa_content(
    service: Annotated[QaServiceAPI, Depends()],
    qa_content: Annotated[QaContent, Depends(get_qa_content)],
) -> MessageResponse:
    """Q&A를 삭제합니다."""
    service.delete_qa_content(qa_content)

    return {
        "message": "Q&A 삭제가 완료되었습니다.",
    }
