"""Q&A Template Router"""
import textwrap
from typing import List
from typing_extensions import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, Path, Query, Request,
    UploadFile
)
from fastapi.responses import RedirectResponse

from core.exception import AlertException
from core.formclass import QaContentForm
from core.models import Member
from core.template import UserTemplates
from lib.common import filter_words, get_paging_info, set_url_query_params
from lib.dependency.dependencies import (
    common_search_query_params, validate_super_admin, validate_token
)
from lib.dependency.auth import get_login_member
from lib.html_sanitizer import content_sanitizer, subject_sanitizer
from lib.mail import send_qa_mail
from lib.template_filters import search_font
from lib.template_functions import get_paging
from service.qa_service import QaConfigService, QaFileService, QaService

router = APIRouter()
templates = UserTemplates()
templates.env.filters["search_font"] = search_font


@router.get("/qalist")
async def qa_list(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    config_service: Annotated[QaConfigService, Depends(QaConfigService.async_init)],
    qa_service: Annotated[QaService, Depends(QaService.async_init)],
    search_params: dict = Depends(common_search_query_params),
):
    """
    Q&A 목록 보기
    """
    # Q&A 설정 조회
    qa_config = config_service.get_qa_config()

    # Q&A 목록 조회
    current_page = search_params["current_page"]
    page_rows = config_service.page_rows

    total_records = qa_service.fetch_total_records(member, **search_params)
    paging_info = get_paging_info(current_page, page_rows, total_records)
    qa_contents = qa_service.read_qa_contents(
        member, paging_info["offset"], page_rows, **search_params)

    # Q&A 목록 조회 결과 설정
    for qa in qa_contents:
        qa.num = total_records - paging_info["offset"] - (qa_contents.index(qa))
        qa.subject = textwrap.shorten(
            qa.qa_subject,
            width=config_service.subject_len,
            placeholder="...")
        qa.icon_file = bool(qa.qa_file1 or qa.qa_file2)

    context = {
        "request": request,
        "qa_config": qa_config,
        "qa_list": qa_contents,
        "categories": config_service.get_category_list(),
        "total_count": total_records,
        "current_page": current_page,
        "paging": get_paging(request, current_page, total_records, page_rows),
    }
    return templates.TemplateResponse("/qa/qa_list.html", context)


@router.get("/qawrite")
async def qa_form_write(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    config_service: Annotated[QaConfigService, Depends()],
    qa_service: Annotated[QaService, Depends()],
    qa_related: Annotated[int, Query()] = None,
):
    """
    Q&A 등록 폼 페이지
    """
    categories = config_service.get_category_list()
    initial_content = qa_service.init_qa_content(member, qa_related)

    context = {
        "request": request,
        "qa_config": config_service.qa_config,
        "categories": categories,
        "qa": None,
        "content": initial_content,
    }
    return templates.TemplateResponse("/qa/qa_form.html", context)


@router.get("/qawrite/{qa_id}")
async def qa_form_edit(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    config_service: Annotated[QaConfigService, Depends()],
    qa_service: Annotated[QaService, Depends()],
    qa_id: Annotated[int, Path(...)],
):
    """
    Q&A 수정 폼 페이지
    """
    categories = config_service.get_category_list()
    qa = qa_service.read_qa_content(member, qa_id)

    context = {
        "request": request,
        "qa_config": config_service.qa_config,
        "categories": categories,
        "qa": qa,
        "content": qa.qa_content
    }
    return templates.TemplateResponse("/qa/qa_form.html", context)


@router.post("/qawrite_update",
             dependencies=[Depends(validate_token)])
async def qa_write_update(
    request: Request,
    background_tasks: BackgroundTasks,
    member: Annotated[Member, Depends(get_login_member)],
    qa_service: Annotated[QaService, Depends()],
    file_service: Annotated[QaFileService, Depends()],
    form: QaContentForm = Depends(),
    qa_id: int = Form(None),
    qa_parent: str = Form(None),
    qa_related: int = Form(None),
    file1: UploadFile = File(None),
    file2: UploadFile = File(None),
    file_del1: int = Form(None),
    file_del2: int = Form(None),
):
    """
    1:1문의 설정 등록/수정 처리
    """
    # Q&A 내용 검증
    subject_filter_word = filter_words(request, form.qa_subject)
    content_filter_word = filter_words(request, form.qa_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise AlertException(f"제목/내용에 금지단어({word})가 포함되어 있습니다.", 400)

    # Stored XSS 방지
    form.qa_subject = subject_sanitizer.get_cleaned_data(form.qa_subject)
    form.qa_content = content_sanitizer.get_cleaned_data(form.qa_content)

    # 수정
    if qa_id:
        qa = qa_service.read_qa_content(member, qa_id)
        qa = qa_service.update_qa_content(qa, form)
    # 등록
    else:
        form.qa_related = qa_related
        form.qa_parent = qa_parent if qa_parent else 0

        qa = qa_service.create_qa_content(member, form)
        # Q&A 등록에 대한 안내메일 발송 처리(백그라운드)
        background_tasks.add_task(send_qa_mail, request, qa)

    file_data = {
        "file1": file1,
        "file2": file2,
        "file_del1": file_del1,
        "file_del2": file_del2,
    }
    file_service.upload_qa_file(qa, file_data)

    # TODO: SMS 알림 옵션이 활성화 되어있을 경우, SMS 발송 기능 추가 필요
    # if qa_config.qa_use_sms:
    #     pass
    return_id = qa.qa_parent or qa.qa_id
    return RedirectResponse(url=f"/bbs/qaview/{return_id}", status_code=302)


@router.get("/qadelete/{qa_id}",
            dependencies=[Depends(validate_token)])
async def qa_delete(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    qa_service: Annotated[QaService, Depends()],
    qa_id: Annotated[int, Path()],
):
    """
    Q&A 삭제하기
    """
    qa = qa_service.read_qa_content(member, qa_id)
    qa_service.delete_qa_content(qa)

    return RedirectResponse(
        status_code=302,
        url=set_url_query_params("/bbs/qalist", request.query_params)
    )


@router.post("/qadelete/list",
             dependencies=[Depends(validate_token),
                           Depends(validate_super_admin)])
async def qa_delete_list(
    request: Request,
    qa_service: Annotated[QaService, Depends()],
    checks: List[int] = Form(..., alias="chk_qa_id[]")
):
    """
    Q&A 목록 일괄삭제
    """
    qa_service.delete_qa_contents(checks)

    return RedirectResponse(
        set_url_query_params("/bbs/qalist", request.query_params), 303)


@router.get("/qaview/{qa_id}")
async def qa_view(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    config_service: Annotated[QaConfigService, Depends()],
    qa_service: Annotated[QaService, Depends()],
    qa_id: Annotated[int, Path(...)],
    search_params: dict = Depends(common_search_query_params),
):
    """
    Q&A 상세보기
    """
    # Q&A 에디터 설정 조회
    request.state.editor = config_service.select_editor

    qa_content = qa_service.read_qa_content(member, qa_id)
    answer = qa_service.fetch_qa_answer(qa_id)
    prev_qa, next_qa = qa_service.fetch_prev_next_qa(member, qa_id, **search_params)
    related_qa_contents = qa_service.fetch_related_qa_contents(member, qa_id)

    context = {
        "request": request,
        "qa_config": config_service.get_qa_config(),
        "qa": qa_content,
        "answer": answer,
        "related_list": related_qa_contents,
        "prev": prev_qa,
        "next": next_qa
    }
    return templates.TemplateResponse("/qa/qa_view.html", context)
