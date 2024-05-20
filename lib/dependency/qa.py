"""Q&A 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, File, Form, Path, UploadFile

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


def get_upload_file_data(
    file_service: Annotated[QaFileService, Depends()],
    file1: Annotated[UploadFile, File(title="첨부파일1")] = None,
    file2: Annotated[UploadFile, File(title="첨부파일2")] = None,
    file_del1: Annotated[int, Form(title="첨부파일1 삭제 여부")] = 0,
    file_del2: Annotated[int, Form(title="첨부파일2 삭제 여부")] = 0,
) -> dict:
    """Q&A 업로드 파일의 유효성을 검사합니다."""
    if file1:
        file_service.validate_upload_file(file1)
    if file2:
        file_service.validate_upload_file(file2)

    return {
        "file1": file1,
        "file2": file2,
        "file_del1": file_del1,
        "file_del2": file_del2,
    }
