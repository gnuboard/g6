"""Q&A 관련 기능을 제공하는 모듈입니다."""
import os

from typing import List
from typing_extensions import Annotated

from fastapi import Depends, Request, UploadFile
from sqlalchemy import func, select, Select

from core.database import db_session
from core.exception import AlertException
from core.models import Member, QaConfig, QaContent
from lib.common import delete_image, get_client_ip, make_directory, save_image
from lib.service import BaseService
from api.v1.models.qa import QaContentModel

FILE_DIRECTORY = "data/qa/"


class QaConfigService(BaseService):
    """Q&A 설정 서비스 클래스"""
    _instance = None
    qa_config: QaConfig = None

    def __new__(cls, request: Request, db: db_session) -> "QaConfigService":
        if cls._instance:
            return cls._instance
        cls._instance = super(QaConfigService, cls).__new__(cls)
        return cls._instance

    def __init__(self, request: Request, db: db_session):
        self.db = db
        self.request = request
        self.config = request.state.config
        self.is_mobile = request.state.is_mobile
        self.qa_config = self.get()

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    @property
    def page_rows(self) -> int:
        """Q&A 페이지당 출력할 행의 수를 반환.

        Returns:
            int: Q&A 페이지당 출력할 행의 수.
        """
        qa_page_rows = self.qa_config.qa_page_rows
        page_rows = self.config.cf_page_rows
        # 모바일 여부 확인
        if self.is_mobile:
            qa_page_rows = self.qa_config.qa_mobile_page_rows
            page_rows = self.config.cf_mobile_page_rows

        return qa_page_rows if qa_page_rows else page_rows

    @property
    def select_editor(self) -> str:
        """게시판에 사용할 에디터를 반환.

        Returns:
            str: 게시판에 사용할 에디터.
        """
        if not self.qa_config.qa_use_editor or not self.config.cf_editor:
            return "textarea"

        return self.config.cf_editor

    def get(self):
        """Q&A 설정 조회

        Returns:
            QaConfig: Q&A 설정
        """
        qa_config = self.db.scalar(select(QaConfig).order_by(QaConfig.id))
        if not qa_config:
            raise self.raise_exception(404, "Q&A 설정이 존재하지 않습니다.")

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
        cut_length = cut_length or (
            self.qa_config.qa_mobile_subject_len if self.is_mobile else self.qa_config.qa_subject_len)

        if not cut_length:
            return subject

        return subject[:cut_length] + "..." if len(subject) > cut_length else subject


class QaService(BaseService):
    """
    FAQ 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self,
                 request: Request,
                 db: db_session,
                 config_service: Annotated[QaConfigService, Depends()]):
        self.request = request
        self.db = db
        self.config_service = config_service

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def create_qa_content(self, member: Member, data: QaContentModel) -> QaContent:
        """
        Q&A를 등록합니다.
        """
        config = self.request.state.config
        if data.qa_parent:
            if member.mb_level != 10 or config.cf_admin != member.mb_id:
                return self.raise_exception(400, "답변글은 관리자만 작성할 수 있습니다.")

        qa = QaContent(**data.__dict__)
        qa.qa_ip = get_client_ip(self.request)
        qa.mb_id = member.mb_id
        qa.qa_name = member.mb_nick

        self.db.add(qa)
        self.db.commit()
        self.db.refresh(qa)

        return qa

    def fetch_total_records(self, member: Member, **kwargs) -> int:
        """
        Q&A 목록의 총 개수를 데이터베이스에서 조회합니다.
        """
        query = self._base_qa_contents_query(member, **kwargs)
        return self.db.scalar(query.add_columns(func.count()).select_from(QaContent))

    def fetch_qa_contents(
            self, member: Member,
            offset: int = 0, records_per_page: int = 10, **kwargs) -> List[QaContent]:
        """
        Q&A 목록을 데이터베이스에서 조회합니다.
        TODO : QaConfig 적용해야함
        """
        query = self._base_qa_contents_query(member, **kwargs)
        return self.db.scalars(
            query.add_columns(QaContent)
            .order_by(QaContent.qa_id.desc())
            .offset(offset).limit(records_per_page)
        ).all()

    def fetch_qa_content(self, qa_id: int) -> QaContent:
        """
        Q&A 1건을 데이터베이스에서 조회합니다.
        """
        return self.db.get(QaContent, qa_id)
    
    def fetch_qa_answer(self, qa_id: int) -> QaContent:
        """
        Q&A 답변글을 데이터베이스에서 조회합니다.
        """
        return self.db.scalar(
            select(QaContent).where(QaContent.qa_parent == qa_id))

    def read_qa_content(self, member: Member, qa_id: int) -> QaContent:
        """
        Q&A 1건을 조회합니다.
        """
        qa_content = self.fetch_qa_content(qa_id)
        if not qa_content:
            self.raise_exception(404, f"{qa_id} : Q&A가 존재하지 않습니다.")
        if not member.mb_id == self.request.state.config.cf_admin:
            if not qa_content.mb_id == member.mb_id:
                self.raise_exception(403, "접근 권한이 없습니다.")
        return qa_content

    def read_qa_contents(self, member: Member,
                         offset: int, records_per_page: int, **kwargs) -> List[QaContent]:
        """
        Q&A 목록을 조회합니다.
        """
        return self.fetch_qa_contents(member, offset, records_per_page, **kwargs)

    def update_qa_content(self, member: Member, qa_id: int, data: QaContentModel) -> QaContent:
        """
        Q&A를 수정합니다.
        """
        qa = self.read_qa_content(member, qa_id)
        for key, value in data.__dict__.items():
            setattr(qa, key, value)
        self.db.commit()
        return qa
    
    def delete_qa_content(self, member: Member, qa_id: int) -> QaContent:
        """
        Q&A를 삭제합니다.
        """
        qa = self.read_qa_content(member, qa_id)
        self.db.delete(qa)
        self.db.commit()
        return qa

    def init_qa_content(self, member: Member, qa_related: int = None) -> str:
        """
        초기 Q&A내용 입력값을 초기화합니다.
        - Template에서만 사용됨.
        """
        qa_config = self.config_service.qa_config
        content = qa_config.qa_insert_content
        line_break = "<br>" if qa_config.qa_use_editor else "\n"
        contour = f"====== 이전 질문내용 ======={line_break}"

        # 추가질문 작성 시, 연관질문 내용으로 초기화
        if qa_related:
            related = self.read_qa_content(member, qa_related)
            content = contour + related.qa_content

        return content
    
    def _base_qa_contents_query(self, member: Member, **kwargs) -> Select:
        """
        Q&A 목록을 조회하는 기본 쿼리를 반환합니다.
        """
        config = self.request.state.config
        search_fields = ["qa_subject", "qa_content", "qa_name", "mb_id"]
        search_params = {
            "sca": kwargs.get("sca", None),
            "stx": kwargs.get("stx", None),
            "sfl": kwargs.get("sfl", None)
        }

        query = select().where(QaContent.qa_type == 0)
        if not member.mb_id == config.cf_admin:
            query = query.where(QaContent.mb_id == member.mb_id)

        if search_params["sca"]:
            query = query.where(QaContent.qa_category == search_params["sca"])
        if search_params["stx"] and search_params["sfl"] in search_fields:
            query = query.where(getattr(QaContent, search_params["sfl"]).like(
                f"%{search_params['stx']}%"))

        return query

    def upload_qa_file(self, qa_id: int, member: Member, data: dict) -> str:
        """
        Q&A 업로드 파일을 처리합니다.
        """
        qa = self.read_qa_content(member, qa_id)
        file1: UploadFile = data.get("file1", None)
        file2: UploadFile = data.get("file2", None)
        file_del1: int = data.get("qa_file_del1", 0)
        file_del2: int = data.get("qa_file_del2", 0)

        # 파일 경로체크 및 생성
        make_directory(FILE_DIRECTORY)
        # 파일 삭제
        filename1 = qa.qa_file1.split("/")[-1] if qa.qa_file1 else None
        filename2 = qa.qa_file2.split("/")[-1] if qa.qa_file2 else None
        delete_image(FILE_DIRECTORY, f"{filename1}", file_del1)
        delete_image(FILE_DIRECTORY, f"{filename2}", file_del2)

        # 파일 및 데이터 저장
        if file1.size > 0:
            filename1 = os.urandom(16).hex() + "." + file1.filename.split(".")[-1]
            qa.qa_file1 = FILE_DIRECTORY + filename1
            qa.qa_source1 = file1.filename
            save_image(FILE_DIRECTORY, f"{filename1}", file1)
        elif file_del1:
            qa.qa_source1 = None
            qa.qa_file1 = None
        if file2.size > 0:
            filename2 = os.urandom(16).hex() + "." + file2.filename.split(".")[-1]
            qa.qa_file2 = FILE_DIRECTORY + filename2
            qa.qa_source2 = file2.filename
            save_image(FILE_DIRECTORY, f"{filename2}", file2)
        elif file_del2:
            qa.qa_source2 = None
            qa.qa_file2 = None
        self.db.commit()
