"""Q&A Template Router"""
from typing import List
from typing_extensions import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form,
    Path, Query, Request, UploadFile
)
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select, Select

from core.database import db_session
from core.exception import AlertException
from core.formclass import QaContentForm
from core.models import Member, QaContent
from core.template import UserTemplates
from lib.common import filter_words, get_paging_info, set_url_query_params
from lib.dependencies import (
    common_search_query_params, get_login_member,
    validate_super_admin, validate_token
)
from lib.html_sanitizer import content_sanitizer, subject_sanitizer
from lib.mail import send_qa_mail
from lib.service.qa_service import QaConfigService, QaService
from lib.template_filters import search_font
from lib.template_functions import get_paging

router = APIRouter()
templates = UserTemplates()
templates.env.filters["search_font"] = search_font


@router.get("/qalist")
async def qa_list(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    config_service: Annotated[QaConfigService, Depends()],
    qa_service: Annotated[QaService, Depends()],
    search_params: dict = Depends(common_search_query_params),
):
    """
    Q&A 목록 보기
    """
    # Q&A 설정 조회
    qa_config = config_service.get()

    # Q&A 목록 조회
    current_page = search_params["current_page"]
    page_rows = config_service.page_rows
    total_records = qa_service.fetch_total_records(member, **search_params)
    paging_info = get_paging_info(current_page, page_rows, total_records)
    qa_contents = qa_service.read_qa_contents(
        member, paging_info["offset"], page_rows, **search_params)
    # Q&A 목록 조회 결과 설정
    for qa in qa_contents:
        qa.num = total_records - \
            paging_info["offset"] - (qa_contents.index(qa))
        qa.subject = config_service.cut_write_subject(qa.qa_subject)
        qa.icon_file = bool(qa.qa_file1 or qa.qa_file2)

    context = {
        "request": request,
        "qa_config": qa_config,
        "qa_list": qa_contents,
        "categories": config_service.get_category_list(),
        "total_count": total_records,
        "current_page": current_page,
        "paging": get_paging(request, search_params["current_page"], total_records, page_rows),
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
    # 여기 작업할 것
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
    form_data: QaContentForm = Depends(),
    qa_id: int = Form(None),
    qa_parent: str = Form(None),
    qa_related: int = Form(None),
    file1: UploadFile = File(None),
    file2: UploadFile = File(None),
    qa_file_del1: int = Form(None),
    qa_file_del2: int = Form(None),
):
    """
    1:1문의 설정 등록/수정 처리
    """
    # Q&A 내용 검증
    subject_filter_word = filter_words(request, form_data.qa_subject)
    content_filter_word = filter_words(request, form_data.qa_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise AlertException(f"제목/내용에 금지단어({word})가 포함되어 있습니다.", 400)

    # Stored XSS 방지
    form_data.qa_subject = subject_sanitizer.get_cleaned_data(
        form_data.qa_subject)
    form_data.qa_content = content_sanitizer.get_cleaned_data(
        form_data.qa_content)

    # 수정
    if qa_id:
        qa = qa_service.update_qa_content(member, qa_id, form_data)
    # 등록
    else:
        form_data.qa_related = qa_related
        form_data.qa_parent = qa_parent if qa_parent else 0
        # form_data.qa_type = 1 if qa_parent else 0

        qa = qa_service.create_qa_content(member, form_data)
        # Q&A 등록에 대한 안내메일 발송 처리(백그라운드)
        background_tasks.add_task(send_qa_mail, request, qa)

    file_data = {
        "file1": file1,
        "file2": file2,
        "qa_file_del1": qa_file_del1,
        "qa_file_del2": qa_file_del2,
    }
    qa_service.upload_qa_file(qa_id, member, file_data)

    # TODO: SMS 알림 옵션이 활성화 되어있을 경우, SMS 발송 기능 추가 필요
    # if qa_config.qa_use_sms:
    #     pass

    if qa.qa_type == 1:
        return RedirectResponse(url=f"/bbs/qaview/{qa.qa_parent}", status_code=302)
    else:
        return RedirectResponse(url=f"/bbs/qaview/{qa.qa_id}", status_code=302)


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
    qa_service.delete_qa_content(member, qa_id)

    return RedirectResponse(
        status_code=302,
        url=set_url_query_params("/bbs/qalist", request.query_params)
    )


@router.post("/qadelete/list",
             dependencies=[Depends(validate_token), Depends(validate_super_admin)])
async def qa_delete_list(
    request: Request,
    db: db_session,
    checks: List[int] = Form(..., alias="chk_qa_id[]")
):
    """
    Q&A 목록 일괄삭제
    """
    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근할 수 있습니다.", 403)

    # Q&A 삭제
    db.execute(delete(QaContent).where(QaContent.qa_id.in_(checks)))
    db.commit()

    url = "/bbs/qalist"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/qaview/{qa_id}")
async def qa_view(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    qa_id: int = Path(...),
    search_params: dict = Depends(common_search_query_params),
    qa_config_service: QaConfigService = Depends()
):
    """
    Q&A 상세보기
    """
    # Q&A 설정 조회
    qa_config = qa_config_service.get()
    request.state.editor = qa_config_service.select_editor

    # Q&A 조회
    qa = db.get(QaContent, qa_id)
    if not qa:
        raise AlertException(f"{qa_id} : Q&A 아이디가 존재하지 않습니다.", 404)
    qa.image, qa.file = set_file_list(request, qa)

    # Q&A 답변글 조회
    answer = db.scalar(select(QaContent).where(
        QaContent.qa_type == 1, QaContent.qa_parent == qa_id))
    if answer:
        answer.image, answer.file = set_file_list(request, answer)

    # 연관질문 목록 조회
    related_query = select(QaContent).where(
        QaContent.qa_type == 0, QaContent.qa_related == qa_id)
    if not request.state.is_super_admin:
        related_query = related_query.where(QaContent.mb_id == member.mb_id)
    related_list = db.scalars(
        related_query.order_by(QaContent.qa_id.desc())).all()

    # 이전글, 다음글 검색조건 추가
    query = select(QaContent)
    if not request.state.is_super_admin:
        query = query.where(QaContent.mb_id == member.mb_id)
    query = filter_query_by_search_params(query, search_params)

    prev = db.scalar(query
                     .where(QaContent.qa_type == 0, QaContent.qa_id < qa_id)
                     .order_by(QaContent.qa_id.desc()))
    next = db.scalar(query
                     .where(QaContent.qa_type == 0, QaContent.qa_id > qa_id)
                     .order_by(QaContent.qa_id.asc()))

    context = {
        "request": request,
        "qa_config": qa_config,
        "qa": qa,
        "answer": answer,
        "related_list": related_list,
        "prev": prev,
        "next": next
    }

    return templates.TemplateResponse("/qa/qa_view.html", context)


def set_file_list(request: Request, qa: QaContent = None):
    """이미지 파일과 첨부파일 목록을 설정

    Args:
        request (Request): Request 객체
        qa (QaContent, optional): Q&A 객체. Defaults to None.

    Returns:
        list, list: 이미지, 첨부파일 목록
    """
    config = request.state.config
    image = []
    file = []

    if qa:
        if qa.qa_source1:
            ext1 = qa.qa_source1.split('.')[-1]
            if ext1 in config.cf_image_extension:
                image.append(qa.qa_file1)
            else:
                file.append({"name": qa.qa_source1, "path": qa.qa_file1})
        if qa.qa_source2:
            ext2 = qa.qa_source2.split('.')[-1]
            if ext2 in config.cf_image_extension:
                image.append(qa.qa_file2)
            else:
                file.append({"name": qa.qa_source2, "path": qa.qa_file2})

    return image, file


def filter_query_by_search_params(query: Select, search_params: dict) -> Select:
    if search_params["sca"]:
        query = query.where(QaContent.qa_category == search_params["sca"])
    if search_params["stx"] and search_params["sfl"] in ["qa_subject", "qa_content", "qa_name", "mb_id"]:
        query = query.where(getattr(QaContent, search_params["sfl"]).like(
            f"%{search_params['stx']}%"))
    return query
