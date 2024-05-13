"""Q&A 관련 기능을 제공하는 모듈입니다."""
import os
from typing import List, Tuple
from typing_extensions import Annotated

from fastapi import Depends, Request, UploadFile
from sqlalchemy import delete, func, select, Select

from core.database import db_session
from core.exception import AlertException
from core.models import Member, QaConfig, QaContent
from lib.common import get_client_ip, save_image
from service import BaseService

from api.v1.models.qa import QaContentData

# 상수 정의
DEFAULT_EDITOR = "textarea"
SEPARATOR = "|"
FILE_DIRECTORY = "data/qa/"


class QaConfigService(BaseService):
    """Q&A 설정 서비스 클래스."""

    def __init__(self, request: Request, db: db_session):
        self.db = db
        self.request = request
        self.config = request.state.config
        self.is_mobile = request.state.is_mobile
        self.qa_config = self.get_qa_config()

    @classmethod
    async def async_init(cls,  request: Request, db: db_session):
        instance = cls(request, db)
        return instance

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        """예외 발생 메소드. 주어진 상태 코드와 상세 내용으로 예외를 발생시킨다."""
        raise AlertException(detail, status_code, url)

    @property
    def page_rows(self) -> int:
        """Q&A 페이지당 출력할 행의 수를 반환한다"""
        qa_page_rows = self.qa_config.qa_page_rows
        page_rows = self.config.cf_page_rows
        if self.is_mobile:
            qa_page_rows = self.qa_config.qa_mobile_page_rows
            page_rows = self.config.cf_mobile_page_rows

        return qa_page_rows or page_rows

    @property
    def select_editor(self) -> str:
        """Q&A에서 사용할 에디터를 반환합니다."""
        if not self.qa_config.qa_use_editor or not self.config.cf_editor:
            return DEFAULT_EDITOR

        return self.config.cf_editor

    @property
    def subject_len(self) -> int:
        """Q&A 제목 길이를 반환합니다."""
        if self.is_mobile:
            return int(self.qa_config.qa_mobile_subject_len)
        return int(self.qa_config.qa_subject_len)

    def get_qa_config(self) -> QaConfig:
        """Q&A 설정 조회."""
        qa_config = self.db.scalar(select(QaConfig).order_by(QaConfig.id))
        if not qa_config:
            self.raise_exception(404, "Q&A 설정이 존재하지 않습니다.")

        return qa_config

    def get_category_list(self) -> List[str]:
        """카테고리 목록 조회."""
        return (self.qa_config.qa_category.split(SEPARATOR)
                if self.qa_config.qa_category else [])


class QaFileService(BaseService):
    """Q&A 파일 서비스 클래스"""

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db
        self.directory = FILE_DIRECTORY

    @classmethod
    async def async_init(cls, request: Request, db: db_session):
        instance = cls(request, db)
        return instance

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def upload_qa_file(self, qa: QaContent, data: dict) -> str:
        """
        Q&A 업로드 파일을 처리합니다.
        """
        self._process_file(qa, data, "1")
        self._process_file(qa, data, "2")
        self.db.commit()

    def _process_file(self, qa: QaContent, data: dict, key: str):
        """단일 파일 처리 로직"""
        file: UploadFile = data.get(f"file{key}")
        file_del = data.get(f"file_del{key}", False)

        # 파일 경로 생성
        os.makedirs(self.directory, exist_ok=True)

        # 파일 삭제
        if file_del:
            self._delete_file(getattr(qa, f"qa_file{key}"))
            setattr(qa, f"qa_file{key}", None)
            setattr(qa, f"qa_source{key}", None)

        if file and file.filename:
            self._validate_file(file)
            filename = self._generate_filename(file.filename)
            save_image(self.directory, filename, file)
            setattr(qa, f"qa_file{key}", str(self.directory + filename))
            setattr(qa, f"qa_source{key}", file.filename)

    def set_file_list(self, qa: QaContent = None) -> Tuple[List[str], List[dict]]:
        """이미지 파일과 첨부파일 목록을 설정

        Args:
            request (Request): Request 객체
            qa (QaContent, optional): Q&A 객체. Defaults to None.

        Returns:
            list, list: 이미지, 첨부파일 목록
        """
        image_extensions = self.request.state.config.cf_image_extension.split(SEPARATOR)
        images, files = [], []

        for i in range(1, 3):
            file_source = getattr(qa, f"qa_source{i}", None)
            if file_source:
                extension = file_source.split('.')[-1]
                file_path = getattr(qa, f"qa_file{i}", None)
                if extension in image_extensions:
                    images.append(file_path)
                else:
                    files.append({"name": file_source, "path": file_path})

        return images, files

    def _validate_file(self, file: UploadFile):
        """파일 유효성 검증"""
        # 여기에 파일 크기, 타입 검증 로직 추가

    def _generate_filename(self, original_filename: str) -> str:
        """안전한 파일명 생성"""
        extension = original_filename.split('.')[-1]
        return f"{os.urandom(16).hex()}.{extension}"

    def _delete_file(self, filepath: str):
        """파일 삭제"""
        if os.path.exists(filepath):
            os.remove(filepath)


class QaService(BaseService):
    """Q&A 종속성 주입 서비스 클래스"""

    def __init__(self, request: Request, db: db_session,
                 config_service: Annotated[QaConfigService, Depends()],
                 file_service: Annotated[QaFileService, Depends()]):
        self.request = request
        self.db = db
        self.config_service = config_service
        self.file_service = file_service

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        config_service: Annotated[QaConfigService, Depends(QaConfigService.async_init)],
        file_service: Annotated[QaFileService, Depends(QaFileService.async_init)]
    ):
        instance = cls(request, db, config_service, file_service)
        return instance

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def create_qa_content(self, member: Member, data: QaContentData) -> QaContent:
        """
        Q&A를 등록합니다.
        """
        if data.qa_parent:
            self._validate_create_permission(member)

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
        """
        query = self._base_qa_contents_query(member, **kwargs)
        return self.db.scalars(
            query.add_columns(QaContent)
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

    def fetch_prev_next_qa(self, member: Member,
                           qa_id: int, **kwargs) -> Tuple[QaContent, QaContent]:
        """
        이전/다음 Q&A를 데이터베이스에서 조회합니다.
        """
        query = self._base_qa_contents_query(member, **kwargs)
        query = query.add_columns(QaContent).where(QaContent.qa_parent != 0)
        prev_qa = self.db.scalar(query.where(QaContent.qa_id < qa_id))
        next_qa = self.db.scalar(query.where(QaContent.qa_id > qa_id))
        return prev_qa, next_qa

    def fetch_related_qa_contents(self, member: Member, qa_id: int) -> List[QaContent]:
        """
        연관 Q&A 목록을 데이터베이스에서 조회합니다.
        """
        config = self.request.state.config
        query = select(QaContent).where(
            QaContent.qa_parent != 0,
            QaContent.qa_related == qa_id
        ).order_by(QaContent.qa_id.desc())

        if not member.mb_id == config.cf_admin:
            query = query.where(QaContent.mb_id == member.mb_id)

        return self.db.scalars(query).all()

    def read_qa_contents(self, member: Member,
                         offset: int, records_per_page: int, **kwargs) -> List[QaContent]:
        """
        Q&A 목록을 조회합니다.
        """
        return self.fetch_qa_contents(member, offset, records_per_page, **kwargs)

    def read_qa_content(self, member: Member, qa_id: int) -> QaContent:
        """
        Q&A 1건을 조회합니다.
        """
        qa = self.fetch_qa_content(qa_id)
        if not qa:
            self.raise_exception(404, f"{qa_id} : Q&A가 존재하지 않습니다.")
        self._validate_access_permission(member, qa)

        qa.image, qa.file = self.file_service.set_file_list(qa)
        return qa

    def read_qa_answer(self, qa_id: int) -> QaContent:
        """
        Q&A 답변글을 조회합니다.
        """
        answer = self.fetch_qa_answer(qa_id)
        if not answer:
            self.raise_exception(404, f"{qa_id} : 답변글이 존재하지 않습니다.")

        answer.image, answer.file = self.file_service.set_file_list(answer)

        return answer

    def update_qa_content(self, qa: QaContent,
                          data: QaContentData) -> QaContent:
        """
        Q&A를 수정합니다.
        """
        for key, value in data.__dict__.items():
            setattr(qa, key, value)
        self.db.commit()
        self.db.refresh(qa)
        return qa

    def delete_qa_content(self, qa: QaContent) -> None:
        """
        Q&A를 삭제합니다.
        """
        self.db.delete(qa)
        self.db.commit()

    def delete_qa_contents(self, qa_ids: List[int]) -> None:
        """
        Q&A 목록을 삭제합니다.
        """
        self._validate_delete_permission()

        query = delete(QaContent).where(QaContent.qa_id.in_(qa_ids))
        self.db.execute(query)
        self.db.commit()

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
            "sfl": kwargs.get("sfl", None)}

        query = (select()
                 .where(QaContent.qa_parent == 0)
                 .order_by(QaContent.qa_id.desc()))
        if not member.mb_id == config.cf_admin:
            query = query.where(QaContent.mb_id == member.mb_id)

        if search_params["sca"]:
            query = query.where(QaContent.qa_category == search_params["sca"])
        if search_params["stx"] and search_params["sfl"] in search_fields:
            query = query.where(
                getattr(QaContent, search_params["sfl"])
                .like(f"%{search_params['stx']}%"))

        return query

    def _validate_access_permission(self, member: Member, qa_content: QaContent):
        """Q&A 접근 권한을 검증합니다."""
        config = self.request.state.config
        if config.cf_admin != member.mb_id and not qa_content.mb_id == member.mb_id:
            self.raise_exception(403, "접근 권한이 없습니다.")

    def _validate_create_permission(self, member: Member):
        """Q&A 작성 권한을 검증합니다."""
        config = self.request.state.config
        if member.mb_level != 10 or config.cf_admin != member.mb_id:
            self.raise_exception(400, "답변글은 관리자만 작성할 수 있습니다.")

    def _validate_delete_permission(self):
        """Q&A 삭제 권한을 검증합니다."""
        if not self.request.state.is_super_admin:
            self.raise_exception(403, "최고관리자만 접근할 수 있습니다.")
