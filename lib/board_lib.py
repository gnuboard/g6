# 게시판/게시글 함수 모음 (임시)
import bleach

from datetime import datetime, timedelta
from fastapi import Request
from sqlalchemy import and_, distinct, or_, literal, select
from sqlalchemy.orm import Query as SqlQuery

from lib.common import *
from common.database import SessionLocal
from common.models import Board, BoardNew, Scrap, WriteBaseModel


class BoardConfig():
    """게시판 설정 정보를 담는 클래스."""
    def __init__(self, request: Request, board: Board) -> None:
        self.board = board
        self.config = request.state.config
        self.is_mobile = request.state.is_mobile
        self.request = request
        group = board.group if board else None

        self.login_member = request.state.login_member
        self.login_member_id = getattr(self.login_member, "mb_id", None)
        self.login_member_level = get_member_level(request)
        self.login_member_admin_type = get_admin_type(self.request, self.login_member_id, group=group, board=self.board)

    @classmethod
    def create_by_table(cls, request: Request, db: Session, bo_table: str):
        """게시판 테이블명으로 BoardConfig 객체를 생성한다.

        Args:
            request (Request): Request 객체
            db (Session): DB 세션
            bo_table (str): 게시판 테이블명

        Returns:
            BoardConfig: BoardConfig 객체
        """
        board = db.get(Board, bo_table)
        return cls(request, board)

    @property
    def gallery_width(self) -> int:
        """갤러리 목록 이미지 가로 크기를 반환.

        Returns:
            int: 갤러리 이미지 가로 크기.
        """
        return (self.board.bo_mobile_gallery_width if self.is_mobile else self.board.bo_gallery_width) or 200

    @property
    def gallery_height(self) -> int:
        """갤러리 목록 이미지 세로 크기를 반환.

        Returns:
            int: 갤러리 이미지 세로 크기.
        """
        return (self.board.bo_mobile_gallery_height if self.is_mobile else self.board.bo_gallery_height) or 150

    @property
    def image_width(self) -> int:
        """게시판 상세페이지에서 보여줄 이미지 가로 크기를 반환.

        Returns:
            int: 이미지 가로 크기.
        """
        return self.board.bo_image_width or None

    @property
    def page_rows(self) -> int:
        """게시판 페이지당 출력할 행의 수를 반환.

        Returns:
            int: 게시판 페이지당 출력할 행의 수.
        """
        # 모바일 여부 확인
        bo_page_rows = self.board.bo_mobile_page_rows if self.is_mobile else self.board.bo_page_rows
        page_rows = self.config.cf_mobile_page_rows if self.is_mobile else self.config.cf_page_rows

        return bo_page_rows if bo_page_rows != 0 else page_rows
    
    @property
    def table_width(self) -> int:
        """게시판 테이블의 가로 크기를 반환.

        Returns:
            int: 게시판 테이블의 가로 크기.
        """
        return self.board.bo_table_width or 100
    
    @property
    def get_table_width(self) -> str:
        """게시판 테이블의 가로 크기를 단위와 함께 반환.

        Returns:
            str: 게시판 테이블의 가로 크기.
        """
        unit = "px" if self.table_width > 100 else "%"

        return f"{self.table_width}{unit}"

    @property
    def select_editor(self) -> str:
        """게시판에 사용할 에디터를 반환.

        Returns:
            str: 게시판에 사용할 에디터.
        """
        return self.board.bo_select_editor or self.config.cf_editor

    @property
    def subject(self) -> str:
        """게시판 제목을 반환.

        Returns:
            str: 게시판 제목.
        """
        if self.request.state.is_mobile and self.board.bo_mobile_subject:
            return self.board.bo_mobile_subject
        else:
            return self.board.bo_subject

    @property
    def use_captcha(self) -> bool:
        """게시판에 캡차 사용 여부를 반환.

        Returns:
            bool: 게시판에 캡차 사용 여부.
        """
        if self.login_member_admin_type:
            return False

        if not self.login_member or self.board.bo_use_captcha:
            return True

        return False

    @property
    def use_email(self) -> bool:
        """게시판에 이메일 사용 여부를 반환.

        Returns:
            bool: 게시판에 이메일 사용 여부.
        """
        return self.config.cf_email_use and self.board.bo_use_email

    @property
    def write_min(self) -> int:
        """게시글 등록 최소 글수 제한"""
        return self._get_write_text_limit(self.board.bo_write_min)

    @property
    def write_max(self) -> int:
        """게시글 등록 최대 글수 제한"""
        return self._get_write_text_limit(self.board.bo_write_max)

    def cut_write_subject(self, subject, cut_length: int = 0) -> str:
        """주어진 cut_length에 기반하여 subject 문자열을 자르고 필요한 경우 "..."을 추가합니다.

        Args:
            - subject: 자를 대상인 주제 문자열.
            - cut_length: subject 문자열의 최대 길이. Default: 0

        Returns:
            - str : 수정된 subject 문자열.
        """
        cut_length = cut_length or (self.board.bo_mobile_subject_len if self.is_mobile else self.board.bo_subject_len)
        
        if not cut_length:
            return subject

        return subject[:cut_length] + "..." if len(subject) > cut_length else subject

    def get_category_list(self) -> list:
        """게시판 카테고리 목록을 반환.

        Returns:
            list: 게시판 카테고리 목록.
        """
        return self.board.bo_category_list.split("|") if self.board.bo_use_category else []

    def get_display_ip(self, ip: str) -> str:
        """IP 주소를 표시형식으로 변환
        Args:
            ip (str): IP 주소
        """
        if self.login_member_admin_type:
            return ip

        if self.board.bo_use_ip_view:
            return re.sub(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)", "\\1.#.#.\\4", ip)
        else:
            return ""

    def get_member_signature(self, mb_id: str = None) -> str:
        """게시판에서 서명보이기를 사용 중이면 회원의 서명을 반환한다.

        Args:
            mb_id (str): 회원 아이디. Defaults to None.

        Returns:
            str: 회원 서명
        """
        if self.board.bo_use_signature and mb_id:
            db = SessionLocal()
            member = db.query(Member).filter(Member.mb_id == mb_id).first()
            db.close()
            return member.mb_signature
        else:
            return ""

    def get_notice_list(self) -> list:
        """게시판 공지글 번호 목록을 반환.

        Returns:
            list: 게시판 공지글 번호 목록.
        """
        if not self.board.bo_notice:
            return []
        return self.board.bo_notice.split(",")

    def get_list_sort_query(self, model: WriteBaseModel, query: SqlQuery) -> SqlQuery:
        """게시글 목록의 정렬을 포함한 query를 반환.

        Args:
            query (SqlQuery): 게시글 목록 쿼리

        Returns:
            SqlQuery: 게시글 목록 쿼리
        """
        if self.board.bo_sort_field:
            sort_fields = self.board.bo_sort_field.split(",")
            for field in sort_fields:
                field_parts = field.strip().split(" ")
                sort_field = getattr(model, field_parts[0])
                if not sort_field:
                    continue
                sort_order = asc(sort_field) if len(field_parts) == 1 or field_parts[1].lower() == "asc" else desc(sort_field)
                query = query.order_by(sort_order)
        else:
            query = query.order_by(model.wr_num, model.wr_reply)

        return query

    def is_list_level(self) -> bool:
        """게시글 목록을 볼 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_list_level)

    def is_read_level(self) -> bool:
        """게시글을 읽을 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_read_level)

    def is_write_level(self) -> bool:
        """게시글을 작성 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_write_level)

    def is_reply_level(self) -> bool:
        """게시글을 답변 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_reply_level)

    def is_comment_level(self) -> bool:
        """댓글을 작성 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_comment_level)

    def is_link_level(self) -> bool:
        """게시글 작성 시, 링크를 추가 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_link_level)

    def is_upload_level(self) -> bool:
        """게시글 작성 시, 파일을 업로드 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_upload_level)

    def is_download_level(self) -> bool:
        """게시글의 첨부파일을 다운로드 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_download_level)

    def is_html_level(self) -> bool:
        """게시글 작성 시, HTML을 추가할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_html_level)

    def is_icon_hot(self, hit: int) -> bool:
        """인기글 아이콘 출력 여부를 반환.

        Args:
            hit (int): 조회수.

        Returns:
            bool: 인기글 아이콘 출력 여부.
        """
        return hit >= self.board.bo_hot if self.board.bo_hot > 0 else False

    def is_icon_new(self, reg_date: datetime) -> bool:
        """새글 아이콘 출력 여부를 반환.

        Args:
            reg_date (str): 등록일.

        Returns:
            bool: 새글 아이콘 출력 여부.
        """
        result = False
        if self.board.bo_new > 0:
            result = reg_date > (datetime.now() - timedelta(hours=int(self.board.bo_new)))
        
        return result

    def is_board_notice(self, wr_id: int) -> bool:
        """게시글이 공지글인지 확인한다.

        Args:
            wr_id (int): 게시글 아이디

        Returns:
            bool: 공지글 여부
        """
        return str(wr_id) in self.board.bo_notice.split(",")

    def is_modify_by_comment(self, wr_id: int) -> bool:
        """댓글 수에 따라 게시글 수정이 가능한지"""
        return self._can_action_by_comment_count(wr_id, self.board.bo_count_modify)

    def is_delete_by_comment(self, wr_id: int) -> bool:
        """댓글 수에 따라 게시글 삭제가 가능한지"""
        return self._can_action_by_comment_count(wr_id, self.board.bo_count_delete)

    def set_board_notice(self, wr_id: int, insert: bool = False) -> str:
        """게시판의 공지글 정보(`,`구분자 문자열)를 수정한다.

        Args:
            wr_id (int): _description_
            insert (bool, optional): _description_. Defaults to False.

        Returns:
            str: _description_
        """
        notice_ids = list(self.board.bo_notice.split(","))
        exist = self.is_board_notice(wr_id)

        if insert and not exist:
            notice_ids.append(str(wr_id))
        elif not insert and exist:
            notice_ids.remove(str(wr_id))

        return ",".join(map(str, notice_ids))

    def set_wr_name(self, member: Member = None, default_name: str = "") -> str:
        """실명사용 여부를 확인 후 실명이면 이름을, 아니면 닉네임을 반환한다.

        Args:
            board (Board): 게시판 object
            member (Member): 회원 object 

        Returns:
            str: 이름 또는 닉네임
        """
        if member:
            if self.board.bo_use_name:
                return member.mb_name
            else:
                return member.mb_nick
        else:
            return default_name

    def _can_action_by_level(self, level: int) -> bool:
        """회원 레벨에 따라 행동 가능 여부를 판단한다.

        Args:
            level (int): 권한 레벨

        Returns:
            bool: 행동 가능 여부
        """
        if self.login_member_admin_type:
            return True
        else:
            return level <= self.login_member_level

    def _can_action_by_comment_count(self, wr_id: int, limit: int) -> bool:
        """댓글 수에 따라 행동 가능 여부를 판단한다.

        Args:
            request (Request): Request 객체
            wr_id (int): 게시글 아이디
            limit (int): 제한할 댓글 수

        Returns:
            bool: 수정 가능 여부
        """
        if self.login_member_admin_type:
            return True

        db = SessionLocal()

        write_model = dynamic_create_write_table(self.board.bo_table)
        comment_count = db.query(write_model).filter_by(
            wr_parent=wr_id,
            wr_is_comment=1
        ).count()

        db.close()

        if limit and limit <= comment_count:
            return False
        else:
            return True

    def _get_write_text_limit(self, limit: int) -> int:
        """게시글/댓글 작성 제한 글 수를 반환.

        Args:
            limit (int): 게시글 작성 제한 글 수.

        Returns:
            int: 게시글 작성 제한 글 수.
        """
        if self.login_member_admin_type or self.board.bo_use_dhtml_editor:
            return 0
        else:
            return limit


class BoardFileManager():
    model = BoardFile

    def __init__(self, board: Board, wr_id: int = None):
        self.board = board
        self.bo_table = board.bo_table
        self.wr_id = wr_id
        self.db = SessionLocal()

    def is_exist(self, bo_table: str = None, wr_id: int = None):
        """게시글에 파일이 있는지 확인

        Returns:
            bool: 파일이 존재하면 True, 없으면 False
        """
        bo_table = bo_table or self.bo_table
        wr_id = wr_id or self.wr_id

        query = self.db.query(self.model).filter_by(bo_table=bo_table, wr_id=wr_id)

        return self.db.query(literal(True)).filter(query.exists()).scalar()
    
    def is_upload_extension(self, request: Request, file: UploadFile) -> bool:
        """업로드 파일 확장자를 확인한다.

        Args:
            file (UploadFile): 업로드 파일

        Returns:
            bool: 파일 확장자가 업로드 가능하면 True, 아니면 False
        """
        config = request.state.config
        ext = file.filename.split(".")[-1]
        content = file.content_type

        if (("image" in content and not ext in config.cf_image_extension)
            or ("x-shockwave-flash" in content and not ext in config.cf_flash_extension)
            or (("audio" in content or "video" in content) and not ext in config.cf_movie_extension)):
            return False
        
        return True

    def is_upload_size(self, file: UploadFile) -> bool:
        """업로드 파일 사이즈를 확인한다.

        Args:
            file (UploadFile): 업로드 파일

        Returns:
            bool: 업로드 파일 사이즈가 설정된 값보다 작으면 True, 크면 False
        """
        if file.size <= 0:
            return False

        if not self.board.bo_upload_size:
            return True

        return file.size <= self.board.bo_upload_size

    def get_board_files(self):
        """업로드된 파일 목록을 가져온다.

        Returns:
            list[BoardFile]: 업로드된 파일 목록
        """
        return self.db.query(self.model).filter_by(
            bo_table=self.bo_table,
            wr_id=self.wr_id
        ).all()

    def get_board_files_by_form(self):
        """입력/수정 폼에서 사용할 파일 목록을 가져온다.

        Returns:
            list[BoardFile]: 업로드된 파일 목록 
        """
        config_count = int(self.board.bo_upload_count) or 0
        if self.wr_id:
            query = self.db.query(self.model).filter_by(bo_table=self.bo_table, wr_id=self.wr_id)
            uploaded_count = query.count()
            uploaded_files = query.all()
            # 파일 카운트는 업로드된 파일 수와 설정된 값 중 큰 수로 설정한다.
            upload_count = (uploaded_count if uploaded_count > config_count else config_count) - uploaded_count
        else:
            uploaded_files = []
            upload_count = config_count

        # 업로드 파일 + 빈 객체
        files = uploaded_files + [self.model() for _ in range(upload_count)]

        return files

    def get_board_files_by_type(self, request: Request):
        """업로드된 파일 목록을 파일과 이미지로 분리한다.

        Args:
            request (Request): Request 객체

        Returns:
            list[BoardFile]: 파일 목록
            list[BoardFile]: 이미지 목록
        """
        config = request.state.config
        board_files = self.get_board_files()
        images = []
        files = []
        for file in board_files:
            ext = file.bf_source.split('.')[-1]
            if ext in config.cf_image_extension:
                images.append(file)
            else:
                files.append(file)

        return images, files

    def get_board_file(self, bf_no: int):
        """업로드된 파일을 가져온다.

        Args:
            bf_no (int): 파일 순번

        Returns:
            BoardFile: 업로드된 파일
        """
        return self.db.query(self.model).filter_by(bo_table=self.bo_table, wr_id=self.wr_id, bf_no=bf_no).first()

    def get_filename(self, filename: str):
        """파일이름을 생성한다.

        Args:
            filename (str): 업로드 파일이름

        Returns:
            str: 파일이름
        """
        return os.urandom(16).hex() + "." + filename.split(".")[-1]

    def insert_board_file(self, bf_no: int, directory: str, filename: str, file: UploadFile, content: str = "", bo_table: str = None, wr_id: int = None):
        """게시글의 파일을 추가한다.

        Args:
            bf_no (int): 파일 순번
            directory (str): 파일 저장 경로
            file (UploadFile): 업로드 파일
            content (str, optional): 파일 설명. Defaults to "".
            bo_table (str, optional): 게시판 테이블명. Defaults to None.
            wr_id (int, optional): 게시글 아이디. Defaults to None.
        """
        board_file = self.model()
        board_file.bo_table = bo_table or self.bo_table
        board_file.wr_id = wr_id or self.wr_id
        board_file.bf_no = bf_no
        board_file.bf_source = file.filename
        board_file.bf_file = f"{directory}/{filename}"
        board_file.bf_download = 0
        board_file.bf_content = content
        board_file.bf_filesize = file.size
        self.db.add(board_file)
        self.db.commit()

    def update_board_file(self, board_file: model, directory: str, filename: str, file: UploadFile, content: str = "", bo_table: str = None, wr_id: int = None):
        """게시글의 파일을 수정한다.

        Args:
            board_file (model): BoardFile 모델
            directory (str): 파일 저장 경로
            file (UploadFile): 업로드 파일
            content (str, optional): 파일 설명. Defaults to "".
        """
        if bo_table:
            board_file.bo_table = bo_table
        if wr_id:
            board_file.wr_id = wr_id
        board_file.bf_source = file.filename
        board_file.bf_file = f"{directory}/{filename}"
        board_file.bf_download = 0
        board_file.bf_content = content
        board_file.bf_filesize = file.size
        self.db.commit()

    def update_download_count(self, board_file: model):
        """다운로드 횟수를 증가시킨다.

        Args:
            board_file (model): BoardFile 모델
        """
        board_file.bf_download += 1
        self.db.commit()

    def move_board_files(self, directory: str, target_bo_table: str, target_wr_id: int):
        """게시글의 파일을 이동한다.

        Args:
            target_bo_table (str): 이동할 게시판 테이블명
            target_wr_id (int): 이동할 게시글 아이디
        """
        directory = os.path.join(directory, target_bo_table)
        make_directory(directory)

        if self.wr_id and target_wr_id:
            board_files = self.get_board_files()
            for board_file in board_files:
                file = self.create_upload_file_from_path(board_file.bf_file)
                file.filename = board_file.bf_source
                file.size = board_file.bf_filesize
                filename = self.get_filename(file.filename)

                # 파일 이동 및 정보 업데이트
                self.move_file(board_file.bf_file, f"{directory}/{filename}")
                self.update_board_file(board_file, directory, filename, file, board_file.bf_content, target_bo_table, target_wr_id)
                board_file.bo_table = target_bo_table
                board_file.wr_id = target_wr_id

            self.db.commit()

    def copy_board_files(self, directory: str, target_bo_table: str, target_wr_id: int):
        """게시글의 파일을 복사한다.

        Args:
            target_bo_table (str): 복사할 게시판 테이블명
            target_wr_id (int): 복사할 게시글 아이디
        """
        directory = os.path.join(directory, target_bo_table)
        make_directory(directory)

        if self.wr_id and target_wr_id:
            board_files = self.get_board_files()
            for board_file in board_files:
                file = self.create_upload_file_from_path(board_file.bf_file)
                file.filename = board_file.bf_source
                file.size = board_file.bf_filesize
                filename = self.get_filename(file.filename)

                # 파일 복사 및 정보 추가
                self.copy_file(board_file.bf_file, f"{directory}/{filename}")
                self.insert_board_file(board_file.bf_no, directory, filename, file, board_file.bf_content, target_bo_table, target_wr_id)
        
    def delete_board_file(self, bf_no: int):
        """게시글의 파일을 삭제한다.

        Args:
            bf_no (int): 파일 순번
        """
        if self.wr_id and bf_no:
            board_file = self.get_board_file(bf_no)
            self.remove_file(board_file.bf_file)
            self.db.delete(board_file)
            self.db.commit()

    def delete_board_files(self):
        """게시글의 파일 전부를 삭제한다.
        """
        if self.wr_id:
            board_files = self.get_board_files()
            for board_file in board_files:
                # 파일 삭제
                self.remove_file(board_file.bf_file)
                # 동일한 경로에 있는 파일 중 파일이름으로 끝나는 파일들 삭제
                dir = os.path.dirname(board_file.bf_file)
                filename = os.path.basename(board_file.bf_file)
                for file in os.listdir(dir):
                    if file.endswith(filename):
                        self.remove_file(os.path.join(dir, file))
                # 파일 정보 삭제
                self.db.delete(board_file)
            self.db.commit()

    def upload_file(self, directory: str, filename: str, file: UploadFile):
        """파일을 업로드한다.

        Args:
            directory (str): 파일 저장 경로
            filename (str): 파일이름
            file (UploadFile): 업로드 파일
        """
        if file and file.filename:
            with open(f"{directory}/{filename}", "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

    def move_file(self, origin: str, target: str):
        """파일을 이동한다.

        Args:
            origin (str): 원본 파일 경로
            target (str): 이동할 파일 경로
        """
        if os.path.exists(origin):
            shutil.move(origin, target)

    def copy_file(self, origin: str, target: str):
        """파일을 복사한다.

        Args:
            origin (str): 원본 파일 경로
            target (str): 복사할 파일 경로
        """
        if os.path.exists(origin):
            shutil.copy(origin, target)

    def remove_file(self, path: str):
        """파일을 삭제한다.

        Args:
            path (str): 파일 경로
        """
        if os.path.exists(path):
            os.remove(path)

    def create_upload_file_from_path(self, path: str):
        """파일 경로로 UploadFile 객체를 생성한다.

        Args:
            path (str): 파일 경로

        Returns:
            UploadFile: 업로드 파일
        """
        with open(path, "rb") as f:
            return UploadFile(f, filename=os.path.basename(path))


def write_search_filter(
        request: Request,
        model: WriteBaseModel,
        category: str = None,
        search_field: str = None,
        keyword: str = None,
        operator: str = "or") -> SqlQuery:
    """게시판 검색 필터를 적용합니다.
    - 그누보드5의 get_sql_search와 동일한 기능을 합니다.

    Args:
        request (Request): FastAPI Request 객체.
        model (WriteBaseModel): 검색할 모델(게시글).
        category (str, optional): 검색할 분류. Defaults to None.
        fields (str, optional): 검색할 필드. Defaults to None.
        keyword (str, optional): 검색할 문자열. Defaults to None.
        operator (str, optional): 검색 조건. Defaults to None.

    Returns:
        Query: 필터가 적용된 쿼리.
    """
    db = SessionLocal()
    fields = []
    is_comment = False

    query = db.query(model)
    # 분류
    if category:
        query = query.filter_by(ca_name=category)

    # 검색 필드 및 단어 설정
    # 검색어를 단어로 분리하여 operator에 따라 필터를 생성
    word_filters = []
    words = keyword.split(" ")
    if search_field:
        tmp = search_field.split(",")
        fields = tmp[0].split("||")
        is_comment = (tmp[1] == "0") if len(tmp) > 1 else False

        # 패스워드 필드 제거
        if "wr_password" in fields:
            fields.remove("wr_password")

        # 필드검색 필터 생성 (or 조건)
        for word in words:
            if not word.strip():
                continue
            word_filters.append(or_(*[getattr(model, field).like(f"%{word}%") for field in fields]))

            # 단어별 인기검색어 등록
            insert_popular(request, fields, word)

    # 분리된 단어 별 검색필터에 or 또는 and를 적용
    if operator == "and":
        query = query.filter(and_(*word_filters))
    else:
        query = query.filter(or_(*word_filters))

    # 댓글 검색
    if is_comment:
        query = query.filter_by(wr_is_comment=1)
        # 원글만 조회해야하므로, wr_parent 목록을 가져와서 in조건으로 재필터링
        query = db.query(model).filter(model.wr_id.in_([row.wr_parent for row in query.all()]))

    return query


def get_next_num(bo_table: str):
    """
    게시판의 다음글 번호를 얻는다.
    """
    db = SessionLocal()
    Write = dynamic_create_write_table(bo_table)
    row = db.query(func.min(Write.wr_num).label("min_wr_num")).first()

    return (int(row.min_wr_num) if row.min_wr_num else 0) - 1


def get_list(request: Request, write: WriteBaseModel, board_config: BoardConfig, subject_len: int = 0):
    """게시글 목록의 출력에 필요한 정보를 추가합니다.
    - 그누보드5의 get_list와 동일한 기능을 합니다.

    Args:
        request (Request): FastAPI Request 객체.
        write (WriteBaseModel): 게시글 객체.
        board (Board): 게시판 객체.
        subject_len (int, optional): 게시글 제목 길이. Defaults to 0.

    Returns:
        WriteBaseModel: 게시글 목록.
    """
    write.subject = board_config.cut_write_subject(write.wr_subject, subject_len)
    write.name = cut_name(request, write.wr_name)
    write.email = StringEncrypt().encrypt(write.wr_email)
    write.datetime = write.wr_datetime.strftime("%y-%m-%d")

    write.is_notice = board_config.is_board_notice(write.wr_id)
    write.icon_secret = "secret" in write.wr_option
    write.icon_hot = board_config.is_icon_hot(write.wr_hit)
    write.icon_new = board_config.is_icon_new(write.wr_datetime)
    write.icon_file = BoardFileManager(board_config.board, write.wr_id).is_exist()
    write.icon_link = write.wr_link1 or write.wr_link2
    write.icon_reply = write.wr_reply

    return write


# FIXME: 대댓글이 있는 상태에서 bo_reply_order를 바꾸면 입력하지 못하는 오류
# ex) 처음에는 정방향 A B C가 입력되고 역방향으로 바꾸면 last_reply_char이 A가 된다(Min).
# 역방향의 char_end는 A이고 A - 1은 예외처리하고 있음으로 대댓글이 입력되지 않는다
def generate_reply_character(board: Board, write):
    """ 대댓글 단계 문자열 생성 

    Args:
        board (Board): 게시판 object
        write (Write): 댓글/답글을 달 게시글 object

    Raises:
        AlertException: Z를 넘어가는 문자열 예외처리

    Returns:
        str: A~Z의 연속된 문자열(Ex: A, B, AA, AB, ABA ..)
    """
    db = SessionLocal()
    write_model = dynamic_create_write_table(board.bo_table)

    # 마지막 문자열 1개 자르기
    if not write.wr_is_comment:
        origin_reply = write.wr_reply
        query = (
            select(func.substr(write_model.wr_reply, -1).label("reply"))
            .where(
                write_model.wr_num == write.wr_num,
                func.length(write_model.wr_reply) == (len(origin_reply) + 1)
            )
        )
        if origin_reply:
            query = query.where(write_model.wr_reply.like(f"{origin_reply}%"))
    else:
        origin_reply = write.wr_comment_reply
        query = (
            select(func.substr(write_model.wr_comment_reply, -1).label("reply"))
            .where(
                write_model.wr_parent == write.wr_parent,
                write_model.wr_comment == write.wr_comment,
                func.length(write_model.wr_comment_reply) == (len(origin_reply) + 1)
            )
        )
        if origin_reply:
            query = query.where(write_model.wr_comment_reply.like(f"{origin_reply}%"))

    # 정방향이면 최대값, 역방향이면 최소값
    if board.bo_reply_order:
        last_reply_char = db.scalar(query.order_by(desc("reply")))
        char_begin = "A"
        char_end = "Z"
        char_increase = 1
    else:
        last_reply_char = db.scalar(query.order_by(asc("reply")))
        char_begin = "Z"
        char_end = "A"
        char_increase = -1

    if last_reply_char == char_end:  # A~Z은 26 입니다.
        raise AlertException("더 이상 답변하실 수 없습니다. 답변은 26개 까지만 가능합니다.")

    if not last_reply_char:
        reply_char = char_begin
    else:
        reply_char = chr(ord(last_reply_char) + char_increase)

    return origin_reply + reply_char


def is_owner(object: object, mb_id: str = None):
    """ 게시글/댓글 작성자인지 확인한다.

    Args:
        object (object): mb_id 속성을 가진 객체
        mb_id (str, optional): 회원 아이디. Defaults to None.

    Returns:
        _type_: _description_
    """
    object_mb_id = getattr(object, "mb_id", None)
    if object_mb_id:
        return object_mb_id == mb_id
    else:
        return False


def send_write_mail(request: Request, board: Board, write: WriteBaseModel, origin_write: WriteBaseModel = None):
    """게시글/답글/댓글 작성 시, 메일을 발송한다.

    Args:
        request (Request): request 객체
        board (Board): 게시판 object
        write (WriteBaseModel): 작성된 게시글/답글/댓글 object
        origin_write (WriteBaseModel, optional): 원본 게시글/답글 object. Defaults to None.
    """
    db = SessionLocal()
    config = request.state.config
    templates = UserTemplates()

    def _add_admin_email(admin_id):
        admin = db.query(Member).filter_by(mb_id=admin_id).first()
        if admin:
            send_email_list.append(admin.mb_email)

    send_email_list = []
    if config.cf_email_wr_board_admin and board.bo_admin:
        _add_admin_email(board.bo_admin)
    if config.cf_email_wr_group_admin and board.group.gr_admin:
        _add_admin_email(board.group.gr_admin)
    if config.cf_email_wr_super_admin:
        _add_admin_email(config.cf_admin)
    if config.cf_email_wr_write and origin_write:
        send_email_list.append(origin_write.wr_email)

    if write.wr_is_comment:
        act = "댓글"
        link_url = str(request.url_for("read_post", bo_table=board.bo_table, wr_id=origin_write.wr_id)) + f"#c_{write.wr_id}"

        if config.cf_email_wr_comment_all:
            # 댓글 쓴 모든 이에게 메일 발송
            write_model = dynamic_create_write_table(board.bo_table)
            query = db.query(distinct(write_model.wr_email).label("email")).filter(
                (write_model.wr_email.notin_(["", write.wr_email])),
                (write_model.wr_parent == origin_write.wr_id)
            )
            comments = query.all()
            send_email_list.extend(comment.email for comment in comments)
    else:
        act = "답변글" if origin_write else "새글"
        link_url = request.url_for("read_post", bo_table=board.bo_table, wr_id=write.wr_id)

    # 중복 이메일 제거
    send_email_list = list(set(send_email_list))
    for email in send_email_list:
        # TODO: 내용 HTML 처리 필요
        subject = f"[{config.cf_title}] {board.bo_subject} 게시판에 {act}이 등록되었습니다."
        body = templates.TemplateResponse(
            "bbs/mail_form/write_update_mail.html", {
                "request": request,
                "act": act,
                "board": board,
                "wr_subject": write.wr_subject,
                "wr_name": write.wr_name,
                "wr_content": write.wr_content,
                "link_url": link_url,
            }
        ).body.decode("utf-8")
        mailer(email, subject, body)

    db.close()


def get_list_thumbnail(request: Request, board: Board, write: WriteBaseModel, thumb_width: int, thumb_height: int, **kwargs):
    """게시글 목록의 섬네일 이미지를 생성한다.

    Args:
        request (Request): _description_
        board (Board): _description_
        write (WriteBaseModel): _description_
        thumb_width (int, optional): _description_. Defaults to 0.
        thumb_height (int, optional): _description_. Defaults to 0.
    """
    config = request.state.config
    images, files = BoardFileManager(board, write.wr_id).get_board_files_by_type(request)
    source_file = None
    result = {"src": "", "alt": ""}

    if images:
        # TODO : 게시글의 파일정보를 캐시된 데이터에서 조회한다.
        # 업로드 파일 목록
        source_file = images[0].bf_file
        result["alt"] = images[0].bf_content
    else:
        # TODO : 게시글의 본문정보를 캐시된 데이터에서 조회한다.
        # 게시글 본문
        editor_images = get_editor_image(write.wr_content, view=False)
        for image in editor_images:
            ext = image.split(".")[-1].lower()
            # TODO: 아래 코드가 정상처리되는지 확인 필요
            # image의 경로 앞에 /가 있으면 /를 제거한다. 에디터 본문의 경로와 python의 경로가 다르기 때문에..
            if image.startswith("/"):
                image = image[1:]

            # image경로의 파일이 존재하고 이미지파일인지 확인
            if (os.path.exists(image)
                    and os.path.isfile(image)
                    and os.path.getsize(image) > 0
                    and ext in config.cf_image_extension
                    ):
                source_file = image
                break

    # 섬네일 생성
    if source_file:
        src = thumbnail(source_file, width=thumb_width, height=thumb_height, **kwargs)
        if src:
            result["src"] = src

    return result


# 본문의 이미지 태그에 width를 강제로 지정하는 필터함수
def set_image_width(content: str, width: str = None) -> str:
    """본문의 이미지 태그에 width를 강제로 지정하는 필터함수

    Args:
        content (str): 게시글 본문
        width (int, optional): 이미지 width. Defaults to 0.

    Returns:
        str: 이미지 태그에 width가 추가된 본문
    """
    if width:
        content = re.sub(r"<img([^>]+)>", f"<img\\1 width={width}>", content)
    return content


def delete_write(request: Request, bo_table: str, origin_write: WriteBaseModel) -> bool:
    """게시글을 삭제한다.

    Args:
        request (Request): request 객체
        bo_table (str): 게시판 코드
        write (WriteBaseModel): 게시글 object

    Returns:
        bool: 결과
    """
    db = SessionLocal()
    board = db.get(Board, bo_table)
    board_config = BoardConfig(request, board)
    group = board.group

    member = request.state.login_member
    member_id = getattr(member, "mb_id", None)
    member_level = get_member_level(request)
    member_admin_type = get_admin_type(request, member_id, group=group, board=board)
    write_mbember_mb_no = db.scalar(select(Member.mb_no).where(Member.mb_id==origin_write.mb_id))
    write_member = db.get(Member, write_mbember_mb_no)
    write_member_level = getattr(write_member, "mb_level", 1)

    # 권한 체크
    if member_admin_type and member_admin_type != "super" and write_member_level > member_level:
        raise AlertException("자신보다 높은 권한의 게시글은 삭제할 수 없습니다.", 403)
    elif origin_write.mb_id and not is_owner(origin_write, member_id):
        raise AlertException("자신의 게시글만 삭제할 수 있습니다.", 403)
    elif not origin_write.mb_id and not request.session.get(f"ss_delete_{bo_table}_{origin_write.wr_id}"):
        raise AlertException("비회원 글을 삭제할 권한이 없습니다.", 403, f"/bbs/password/delete/{bo_table}/{origin_write.wr_id}?{request.query_params}")
    
    # 답변글이 있을 때 삭제 불가
    write_model = dynamic_create_write_table(bo_table)
    query = db.query(write_model).filter(
        write_model.wr_reply.like(f"{origin_write.wr_reply}%"),
        write_model.wr_num == origin_write.wr_num,
        write_model.wr_is_comment == 0,
        write_model.wr_id != origin_write.wr_id
    )
    is_reply = db.query(literal(True)).filter(query.exists()).scalar()
    if is_reply:
        raise AlertException("답변이 있는 글은 삭제할 수 없습니다. \\n\\n우선 답변글부터 삭제하여 주십시오.", 403)

    if not board_config.is_delete_by_comment(origin_write.wr_id):
        raise AlertException(f"이 글과 관련된 댓글이 {board.bo_count_delete}건 이상 존재하므로 삭제 할 수 없습니다.", 403)

    # 원글 + 댓글
    count_write = 0
    count_comment = 0
    writes = db.query(write_model).filter_by(wr_parent=origin_write.wr_id).order_by(write_model.wr_id).all()
    for write in writes:
        # 원글 삭제
        if not write.wr_is_comment:
            # 원글 포인트 삭제
            # TODO: 오류로 인한 주석
            # if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "쓰기"):
            #     insert_point(request, write.mb_id, board.bo_write_point * (-1), f"{board.bo_subject} {write.wr_id} 글 삭제")

            # 파일+섬네일 삭제
            BoardFileManager(board, write.wr_id).delete_board_files()

            # TODO: 에디터 섬네일 삭제

            count_write += 1
        else:
            # 댓글 포인트 삭제
            # TODO: 오류로 인한 주석
            # if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "댓글"):
            #     insert_point(request, write.mb_id, board.bo_comment_point * (-1), f"{board.bo_subject} {write.wr_id} 댓글 삭제")

            count_comment += 1

    # 원글+댓글 삭제
    db.query(write_model).filter_by(wr_parent=origin_write.wr_id).delete()

    # 최근 게시물 삭제
    db.query(BoardNew).filter(
        BoardNew.bo_table == bo_table,
        BoardNew.wr_parent == origin_write.wr_id
    ).delete()

    # 스크랩 삭제
    db.query(Scrap).filter_by(
        bo_table = bo_table,
        wr_id = origin_write.wr_id
    ).delete()

    # 공지사항 삭제
    board.bo_notice = board_config.set_board_notice(origin_write.wr_id, False)

    # 게시글 갯수 업데이트
    board.bo_count_write -= count_write
    board.bo_count_comment -= count_comment

    db.commit()

    # 최신글 캐시 삭제
    G6FileCache().delete_prefix(f'latest-{bo_table}')

    return True


def is_secret_write(write: WriteBaseModel = None) -> bool:
    """비밀글인지 확인한다.

    Args:
        write (WriteBaseModel, optional): 게시글 object. Defaults to None.

    Returns:
        bool: 비밀글 여부
    """
    return "secret" in getattr(write, "wr_option", "")


def url_auto_link(text: str, request: Request, is_nofollow: bool = True) -> str:
    """문자열 안에 포함된 URL을 링크로 변환한다.

    Args:
        text (str): 변환할 문자열.
        request (Request): Request 객체.
        is_nofollow: nofollow 속성 포함여부. Defaults to True.

    Returns:
        str: 변환된 문자열.
    """
    cf_link_target = getattr(request.state.config, "cf_link_target", "_blank")

    def _nofollow(attrs, _):
        if is_nofollow:
            return bleach.callbacks.nofollow(attrs)
        else:
            return attrs

    def _target(attrs, _):
        attrs = bleach.callbacks.target_blank(attrs)
        if (None, "target") in attrs:
            attrs[(None, "target")] = cf_link_target
        return attrs
    
    return bleach.linkify(text, callbacks=[_nofollow, _target], parse_email=True)


def is_write_delay(request: Request) -> bool:
    """특정 시간 간격 내에 다시 글을 작성할 수 있는지 확인하는 함수"""
    if request.state.is_super_admin:
        return True

    delay_sec = int(request.state.config.cf_delay_sec)
    current_time = datetime.now()
    write_time = request.session.get("ss_write_time")

    if delay_sec > 0:
        time_interval = timedelta(seconds=delay_sec)
        if write_time:
            available_time = datetime.strptime(write_time, "%Y-%m-%d %H:%M:%S") + time_interval
            if available_time > current_time:
                return False

    return True


def set_write_delay(request: Request):
    """글 작성 시간을 세션에 저장하는 함수"""
    delay_sec = int(request.state.config.cf_delay_sec)

    if not request.state.is_super_admin and delay_sec > 0:
        request.session["ss_write_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")