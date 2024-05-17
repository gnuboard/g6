"""Q&A 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Path

from api.v1.models.qa import QaContent
from core.models import Member
from lib.dependency.auth import get_login_member
from service.qa_service import QaFileService, QaService


def get_qa_content(
    service: Annotated[QaService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    qa_id: Annotated[int, Path(..., title="Q&A 아이디", description="조회할 Q&A 아이디")],
):
    """Q&A 정보를 조회합니다."""
    return service.read_qa_content(member, qa_id)


def get_qa_file(
    file_service: Annotated[QaFileService, Depends()],
    qa: Annotated[QaContent, Depends(get_qa_content)],
    file_index: Annotated[int, Path()]
) -> dict:
    """Q&A 파일을 조회합니다."""
    return file_service.get_file(qa, file_index)
