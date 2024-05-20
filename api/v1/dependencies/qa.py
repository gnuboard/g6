"""Q&A API의 의존성을 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, File, Form, HTTPException, Path, Request, UploadFile

from core.models import Member
from lib.common import filter_words
from api.v1.dependencies.member import get_current_member
from api.v1.service.qa import QaFileServiceAPI, QaServiceAPI
from api.v1.models.qa import QaContent, QaContentData


def get_qa_content(
    service: Annotated[QaServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    qa_id: Annotated[int, Path(..., title="Q&A 아이디", description="Q&A 아이디")],
):
    """Q&A 정보를 조회합니다."""
    return service.read_qa_content(member, qa_id)


def get_qa_file(
    file_service: Annotated[QaFileServiceAPI, Depends()],
    qa: Annotated[QaContent, Depends(get_qa_content)],
    file_index: Annotated[int, Path(..., title="Q&A 파일 번호", description="조회할 Q&A 파일 번호")]
) -> dict:
    """Q&A 파일을 조회합니다."""
    return file_service.get_file(qa, file_index)


def validate_data(
    request: Request,
    data: QaContentData,
):
    """Q&A 등록/수정시 정보의 유효성을 검사합니다."""
    subject_filter_word = filter_words(request, data.qa_subject)
    content_filter_word = filter_words(request, data.qa_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise HTTPException(400, f"제목/내용에 금지단어({word})가 포함되어 있습니다.")

    return data


def get_upload_file_data(
    file_service: Annotated[QaFileServiceAPI, Depends()],
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
