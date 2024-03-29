"""Q&A API의 의존성을 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile

from lib.common import filter_words
from lib.template_filters import number_format
from api.v1.lib.qa import QaConfigServiceAPI
from api.v1.models.qa import QaContentModel


def validate_data(
    request: Request,
    data: QaContentModel,
):
    """Q&A 등록/수정시 정보의 유효성을 검사합니다."""
    subject_filter_word = filter_words(request, data.qa_subject)
    content_filter_word = filter_words(request, data.qa_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise HTTPException(400, f"제목/내용에 금지단어({word})가 포함되어 있습니다.")

    return data


def validate_upload_file(
    request: Request,
    config_service: Annotated[QaConfigServiceAPI, Depends()],
    file1: Annotated[UploadFile, File(title="첨부파일1")],
    file2: Annotated[UploadFile, File(title="첨부파일2")],
    qa_file_del1: Annotated[int, Form(title="첨부파일1 삭제 여부")] = 0,
    qa_file_del2: Annotated[int, Form(title="첨부파일2 삭제 여부")] = 0,
) -> dict:
    """Q&A 업로드 파일의 유효성을 검사합니다."""
    qa_config = config_service.qa_config
    limit_size = qa_config.qa_upload_size

    # Q&A 업로드파일 크기 검증
    if not request.state.is_super_admin:
        if file1.size > 0 and file1.size > limit_size:
            raise HTTPException(
                f"파일 업로드는 {number_format(limit_size)}byte 까지 가능합니다.", 400)
        if file2.size > 0 and file2.size > limit_size:
            raise HTTPException(
                f"파일 업로드는 {number_format(limit_size)}byte 까지 가능합니다.", 400)

    return {
        "file1": file1,
        "file2": file2,
        "qa_file_del1": qa_file_del1,
        "qa_file_del2": qa_file_del2,
    }
