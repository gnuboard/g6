import html as htmllib
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import query

from core.database import DBConnect, db_session
from core.exception import AlertException
from core.formclass import QaContentForm
from core.models import QaConfig, QaContent
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import (
    common_search_query_params, get_login_member,
    validate_super_admin, validate_token
)
from lib.template_filters import number_format, search_font
from lib.template_functions import get_paging

router = APIRouter()
templates = UserTemplates()
templates.env.filters["search_font"] = search_font

FILE_DIRECTORY = "data/qa/"


class QaConfigService:
    """Q&A 설정 서비스 클래스"""
    _instance = None
    qa_config = None

    def __new__(cls, request: Request) -> "QaConfigService":
        if not cls._instance:
            cls._instance = super(QaConfigService, cls).__new__(cls)
        return cls._instance

    def __init__(self, request: Request):
        self.model = QaConfig
        self.request = request
        self.config = request.state.config
        self.is_mobile = request.state.is_mobile
        self.qa_config = self.get()

    @property
    def page_rows(self) -> int:
        """Q&A 페이지당 출력할 행의 수를 반환.

        Returns:
            int: Q&A 페이지당 출력할 행의 수.
        """
        # 모바일 여부 확인
        qa_page_rows = self.qa_config.qa_mobile_page_rows if self.is_mobile else self.qa_config.qa_page_rows
        page_rows = self.config.cf_mobile_page_rows if self.is_mobile else self.config.cf_page_rows

        return qa_page_rows if qa_page_rows != 0 else page_rows

    def get(self):
        """Q&A 설정 조회

        Returns:
            QaConfig: Q&A 설정
        """
        db = DBConnect().sessionLocal()
        qa_config = db.scalar(select(self.model).order_by(self.model.id))
        db.close()
        if not qa_config:
            raise AlertException("Q&A 설정이 존재하지 않습니다.", 404)

        return qa_config

    def get_category_list(self) -> list:
        """Q&A 설정 카테고리 목록을 반환.

        Returns:
            list: Q&A 설정 카테고리 목록.
        """
        return self.qa_config.qa_category.split("|") if self.qa_config.qa_category else []

    def cut_write_subject(self, subject, cut_length: int = 0) -> str:
        """주어진 cut_length에 기반하여 subject 문자열을 자르고 필요한 경우 "..."을 추가합니다.

        Args:
            - subject: 자를 대상인 주제 문자열.
            - cut_length: subject 문자열의 최대 길이. Default: 0

        Returns:
            - str : 수정된 subject 문자열.
        """
        cut_length = cut_length or (self.qa_config.qa_mobile_subject_len if self.is_mobile else self.qa_config.qa_subject_len)

        if not cut_length:
            return subject

        return subject[:cut_length] + "..." if len(subject) > cut_length else subject


@router.get("/qalist")
async def qa_list(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    search_params: dict = Depends(common_search_query_params),
    qa_config_service: QaConfigService = Depends()
):
    """
    Q&A 목록 보기
    """
    # Q&A 설정 조회
    qa_config = qa_config_service.get()

    # Q&A 목록 조회
    query = select().where(QaContent.qa_type==0).order_by(QaContent.qa_id.desc())
    if not request.state.is_super_admin:
        query = query.where(QaContent.mb_id==member.mb_id)
    query = filter_query_by_search_params(query, search_params)

    # 페이징 변수
    current_page = search_params["current_page"]
    records_per_page = qa_config_service.page_rows
    total_count = db.scalar(query.add_columns(func.count()).order_by(None))
    offset = (current_page - 1) * records_per_page

    # Q&A 목록 조회 & 페이징
    qa_list = db.scalars(query.add_columns(QaContent).offset(offset).limit(records_per_page)).all()
    for qa in qa_list:
        qa.num = total_count - offset - (qa_list.index(qa))
        qa.subject = qa_config_service.cut_write_subject(qa.qa_subject)
        qa.icon_file = True if qa.qa_file1 or qa.qa_file2 else False

    context = {
        "request": request,
        "qa_config": qa_config,
        "qa_list": qa_list,
        "categories": qa_config_service.get_category_list(),
        "total_count": total_count,
        "current_page": current_page,
        "paging": get_paging(request, current_page, total_count, qa_config_service.page_rows),
    }

    return templates.TemplateResponse("/qa/qa_list.html", context)


@router.get("/qawrite", dependencies=[Depends(get_login_member)])
async def qa_form_write(
    request: Request,
    db: db_session,
    qa_related: int = Query(None),
    qa_config_service: QaConfigService = Depends()
):
    """
    Q&A 작성하기
    """
    # Q&A 설정 조회
    qa_config = qa_config_service.get()
    content = qa_config.qa_insert_content

    # 추가질문 작성 시, 원본질문 조회
    related = None
    if qa_related:
        related = db.get(QaContent, qa_related)
        if not related:
            raise AlertException(f"{qa_related} : 연관된 Q&A아이디가 존재하지 않습니다.", 404)
        # 이전 답변내용 추가
        line_break = "<br>" if qa_config.qa_use_editor else "\n"
        content = f"====== 이전 답변내용 ======={line_break}" + related.qa_content

    context = {
        "request": request,
        "qa_config": qa_config,
        "categories": qa_config_service.get_category_list(),
        "qa": None,
        "related": related,
        "content": content,
    }

    return templates.TemplateResponse("/qa/qa_form.html", context)


@router.get("/qawrite/{qa_id}")
async def qa_form_edit(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    qa_id: int = Path(...),
    qa_config_service: QaConfigService = Depends()
):
    """
    Q&A 수정하기
    """
    # Q&A 설정 조회
    qa_config = qa_config_service.get()

    # Q&A 상세 조회
    qa = db.get(QaContent, qa_id)
    if not qa:
        raise AlertException(f"{qa_id} : Q&A 아이디가 존재하지 않습니다.", 404)
    if not request.state.is_super_admin and member.mb_id != qa.mb_id:
        raise AlertException("수정 권한이 없습니다.", 403)

    context = {
        "request": request,
        "qa_config": qa_config,
        "categories": qa_config_service.get_category_list(),
        "qa": qa,
        "content": qa.qa_content
    }

    return templates.TemplateResponse("/qa/qa_form.html", context)


@router.post("/qawrite_update", dependencies=[Depends(validate_token)])
async def qa_write_update(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    form_data: QaContentForm = Depends(),
    qa_id: int = Form(None),
    qa_parent: str = Form(None),
    qa_related: int = Form(None),
    file1: UploadFile = File(None),
    file2: UploadFile = File(None),
    qa_file_del1: int = Form(None),
    qa_file_del2: int = Form(None),
    qa_config_service: QaConfigService = Depends()
):
    """
    1:1문의 설정 등록/수정 처리
    """
    config = request.state.config

    # Q&A 설정 조회
    qa_config = qa_config_service.get()

    # Q&A 내용 검증
    subject_filter_word = filter_words(request, form_data.qa_subject)
    content_filter_word = filter_words(request, form_data.qa_content)
    if subject_filter_word or content_filter_word:
        word = subject_filter_word if subject_filter_word else content_filter_word
        raise AlertException(f"제목/내용에 금지단어({word})가 포함되어 있습니다.", 400)
    
    # Stored XSS 방지
    form_data.qa_subject = htmllib.escape(form_data.qa_subject)
    
    # Q&A 업로드파일 크기 검증
    if not request.state.is_super_admin:
        if file1.size > 0 and file1.size > qa_config.qa_upload_size:
            raise AlertException(f"첨부파일1의 최대 크기는 {number_format(qa_config.qa_upload_size)}byte입니다.", 400)
        if file2.size > 0 and file2.size > qa_config.qa_upload_size:
            raise AlertException(f"첨부파일2의 최대 크기는 {number_format(qa_config.qa_upload_size)}byte입니다.", 400)

    # 수정
    if qa_id:
        qa = db.get(QaContent, qa_id)
        if not qa:
            raise AlertException(f"{qa_id} : Q&A 아이디가 존재하지 않습니다.", 404)

        if not request.state.is_super_admin and member.mb_id != qa.mb_id:
            raise AlertException("수정 권한이 없습니다.", 403)
        
        for field, value in form_data.__dict__.items():
            setattr(qa, field, value)
        db.commit()
    # 등록
    else:
        form_data.qa_related = qa_related
        form_data.qa_type = 1 if qa_parent else 0
        form_data.qa_parent = qa_parent if qa_parent else 0
        form_data.mb_id = member.mb_id
        form_data.qa_name = member.mb_nick
        form_data.qa_datetime = datetime.now()
        form_data.qa_ip = get_client_ip(request)

        qa = QaContent(**form_data.__dict__)
        db.add(qa)

        # 답변글
        # TODO : 메일 발송 템플릿 적용필요
        if qa_parent:
            parent = db.get(QaContent, qa_parent)
            # 원본글의 답변여부를 1로 변경
            parent.qa_status = 1
            # 답변 알림메일 발송
            if parent.qa_email_recv and parent.qa_email:
                subject = f"[{config.cf_title}] {qa_config.qa_title} 답변 알림 메일"
                content = form_data.qa_subject + "<br><br>" + form_data.qa_content
                mailer(parent.qa_email, subject, content)
        else:
            # 문의 등록메일 발송
            if qa_config.qa_admin_email:
                subject = f"[{config.cf_title}] {qa_config.qa_title} 질문 알림 메일"
                content = form_data.qa_subject + "<br><br>" + form_data.qa_content
                mailer(qa_config.qa_admin_email, subject, content)

        db.commit()

    # 파일 경로체크 및 생성
    make_directory(FILE_DIRECTORY)
    # 파일 삭제
    filename1 = qa.qa_file1.split("/")[-1] if qa.qa_file1 else None
    filename2 = qa.qa_file2.split("/")[-1] if qa.qa_file2 else None
    delete_image(FILE_DIRECTORY, f"{filename1}", qa_file_del1)
    delete_image(FILE_DIRECTORY, f"{filename2}", qa_file_del2)

    # 파일 및 데이터 저장
    if file1.size > 0:
        filename1 = os.urandom(16).hex() + "." + file1.filename.split(".")[-1]
        qa.qa_file1 = FILE_DIRECTORY + filename1
        qa.qa_source1 = file1.filename
        save_image(FILE_DIRECTORY, f"{filename1}", file1)
    elif qa_file_del1:
        qa.qa_source1 = None
        qa.qa_file1 = None
    if file2.size > 0:
        filename2 = os.urandom(16).hex() + "." + file2.filename.split(".")[-1]
        qa.qa_file2 = FILE_DIRECTORY + filename2
        qa.qa_source2 = file2.filename
        save_image(FILE_DIRECTORY, f"{filename2}", file2)
    elif qa_file_del2:
        qa.qa_source2 = None
        qa.qa_file2 = None
    db.commit()

    # SMS 알림 옵션이 활성화 되어있을 경우
    if qa_config.qa_use_sms:
        # TODO: SMS 발송 기능 추가 필요
        # 1. 답변글 등록 시, 질문 등록자에게 전송
        # 2. 문의글 등록 시, 관리자에게 발송
        pass


    if qa.qa_type == 1:
        return RedirectResponse(url=f"/bbs/qaview/{qa.qa_parent}", status_code=302)
    else:
        return RedirectResponse(url=f"/bbs/qaview/{qa.qa_id}", status_code=302)
    

@router.get("/qadelete/{qa_id}", dependencies=[Depends(validate_token)])
async def qa_delete(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    qa_id: int = Path(...),
):
    """
    Q&A 삭제하기
    """
    # Q&A 삭제
    qa = db.get(QaContent, qa_id)
    if not qa:
        raise AlertException(f"{qa_id} : Q&A 아이디가 존재하지 않습니다.", 404)
    if not request.state.is_super_admin and member.mb_id != qa.mb_id:
        raise AlertException("삭제 권한이 없습니다.", 403)

    db.delete(qa)
    db.commit()

    url = "/bbs/qalist"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 302)


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

    # Q&A 조회
    qa = db.get(QaContent, qa_id)
    if not qa:
        raise AlertException(f"{qa_id} : Q&A 아이디가 존재하지 않습니다.", 404)
    qa.image, qa.file = set_file_list(request, qa)

    # Q&A 답변글 조회
    answer = db.scalar(select(QaContent).where(QaContent.qa_type==1, QaContent.qa_parent==qa_id))
    if answer:
        answer.image, answer.file = set_file_list(request, answer)

    # 연관질문 목록 조회
    related_query = select(QaContent).where(QaContent.qa_type==0, QaContent.qa_related==qa_id)
    if not request.state.is_super_admin:
        related_query = related_query.where(QaContent.mb_id==member.mb_id)
    related_list = db.scalars(related_query.order_by(QaContent.qa_id.desc())).all()

    # 이전글, 다음글 검색조건 추가
    query = select(QaContent)
    if not request.state.is_super_admin:
        query = query.where(QaContent.mb_id==member.mb_id)
    query = filter_query_by_search_params(query, search_params)

    prev = db.scalar(query.where(QaContent.qa_type==0, QaContent.qa_id<qa_id).order_by(QaContent.qa_id.desc()))
    next = db.scalar(query.where(QaContent.qa_type==0, QaContent.qa_id>qa_id).order_by(QaContent.qa_id.asc()))

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


def filter_query_by_search_params(query: query, search_params: dict) -> query:
    if search_params["sca"]:
        query = query.where(QaContent.qa_category==search_params["sca"])
    if search_params["stx"] and search_params["sfl"] in ["qa_subject", "qa_content", "qa_name", "mb_id"]:
        query = query.where(getattr(QaContent, search_params["sfl"]).like(f"%{search_params['stx']}%"))
    return query