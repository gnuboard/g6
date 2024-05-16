import os

from typing_extensions import Union, List
from fastapi import Request, UploadFile
from sqlalchemy import select, delete

from core.database import db_session
from core.models import Board, WriteBaseModel, Group, AutoSave
from core.exception import AlertException
from core.formclass import WriteForm
from lib.board_lib import (
    BoardConfig, FileCache, is_write_delay, send_write_mail
)
from lib.member import MemberDetails
from lib.common import (
    dynamic_create_write_table, filter_words,
    remove_query_params, set_url_query_params
)
from lib.html_sanitizer import content_sanitizer
from lib.pbkdf2 import create_hash
from service import BaseService
from service.board_file_service import BoardFileService
from api.v1.models.board import WriteModel


class BoardService(BaseService, BoardConfig):
    """게시판 관련 기반 서비스 클래스"""

    FILE_DIRECTORY = "data/file/"

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
    ):
        self.db = db
        board = self.get_board(bo_table)
        super().__init__(request, board)
        self.bo_table = bo_table
        self.write_model = dynamic_create_write_table(bo_table)
        self.categories = self.get_category_list()
        self.member = MemberDetails(request, request.state.login_member, board=self.board)

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise AlertException(status_code=status_code, detail=detail, url=url)

    def validate_wr_password(self, wr_password: str = None):
        """비회원 글쓰기시 비밀번호 작성 여부를 검증"""
        if self.member.mb_id:
            return
        if not wr_password:
            self.raise_exception(detail="비회원 글쓰기시 비밀번호를 기재해야 합니다.", status_code=400)

    def set_wr_name(self, member: MemberDetails = None, default_name: str = None) -> str:
        """실명사용 여부를 확인 후 실명이면 이름을, 아니면 닉네임을 반환한다.

        Args:
            board (Board): 게시판 object
            member (MemberDetails): 회원정보 object 

        Returns:
            str: 이름 또는 닉네임
        """
        if member.mb_id:
            if self.board.bo_use_name:
                return member.mb_name
            else:
                return member.mb_nick
        elif default_name:
            return default_name
        else:
            self.raise_exception(detail="로그인 세션 만료, 비회원 글쓰기시 작성자 이름 미기재 등의 비정상적인 접근입니다.", status_code=400)

    def validate_admin_authority(self):
        """게시판 관리자 검증"""
        if not self.member.admin_type:
            self.raise_exception(detail="게시판 관리자 이상 접근이 가능합니다.", status_code=403)

    def validate_write_level(self):
        """글쓰기 레벨 비교 검증"""
        if not self.is_write_level():
            self.raise_exception(detail="글을 작성할 권한이 없습니다.", status_code=403)

    def validate_secret_board(self, secret: str, html: str, mail: str):
        """게시판의 비밀글 사용여부 검증"""
        if self.member.admin_type:
            return

        # 비밀글 사용여부 체크
        if not self.board.bo_use_secret and "secret" in secret and "secret" in html and "secret" in mail:
            self.raise_exception(status_code=403, detail="비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.")

        # 비밀글 옵션에 따라 비밀글 설정
        if self.board.bo_use_secret == 2:
            self.secret = "secret"

    def validate_post_content(self, content):
        """게시글 내용 검증"""
        filtered_word = filter_words(self.request, content)
        if filtered_word:
            self.raise_exception(detail=f"내용에 금지단어({filtered_word})가 포함되어 있습니다.", status_code=400)

    def validate_write_delay(self):
        """글쓰기 간격 검증"""
        if not is_write_delay(self.request):
            self.raise_exception(status_code=400, detail="너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.")

    def validate_anonymous_password(self, data):
        """비회원 글쓰기시 비밀번호 검증"""
        if not self.member and not data.wr_password:
            self.raise_exception(detail="비회원 글쓰기시 비밀번호를 기재해야 합니다.", status_code=400)

    def get_board(self, bo_table: str) -> Board:
        """게시판 정보를 가져온다."""
        board = self.db.get(Board, bo_table)
        if not board:
            self.raise_exception(detail="존재하지 않는 게시판입니다.", status_code=404)
        return board

    def get_admin_board_list(self) -> List[Board]:
        """관리자가 속한 게시판 목록을 가져옵니다."""
        query = select(Board).join(Group).order_by(Board.gr_id, Board.bo_order, Board.bo_table)
        if self.member.admin_type == "group":
            query = query.where(Group.gr_admin == self.member.mb_id)
        elif self.member.admin_type == "board":
            query = query.where(Board.bo_admin == self.member.mb_id)
        return self.db.scalars(query).all()

    def get_write(self, wr_id: Union[int, str]) -> WriteBaseModel:
        """게시글(댓글)을 가져온다."""
        if not isinstance(wr_id, int) and not wr_id.isdigit():
            self.raise_exception(detail="올바르지 않은 게시글 번호입니다.", status_code=400)

        write = self.db.get(self.write_model, wr_id)
        if not write:
            self.raise_exception(detail="존재하지 않는 게시글(댓글)입니다.", status_code=404)

        return write

    def get_parent_post(self, parent_id: int, is_reply: bool = True):
        """부모글 호출"""
        if not parent_id:
            return None

        if is_reply:    # 답변글
            validate_func = self.is_reply_level
            target_expr = "답변글"
        else:           # 댓글
            validate_func = self.is_comment_level
            target_expr = "댓글"

        # 답변/댓글 권한 검증
        if not validate_func():
            self.raise_exception(detail=f"{target_expr}을 작성할 권한이 없습니다.", status_code=403)

        # 부모글 호출
        parent_write = self.db.get(self.write_model, parent_id)
        if not parent_write:
            self.raise_exception(f"{target_expr}을 쓸 원본 글이 존재하지 않습니다.", 404)
        return parent_write

    def get_redirect_url(self, write):
        """리다이렉트 URL 생성"""
        query_params = remove_query_params(self.request, "parent_id")
        url = f"/board/{self.bo_table}/{write.wr_id}"
        return set_url_query_params(url, query_params)

    def get_cleaned_data(self, content):
        """Stored XSS 방지용 데이터 정제"""
        return content_sanitizer.get_cleaned_data(content)

    def arrange_data(self, data: Union[WriteForm, WriteModel], secret: str, html: str, mail: str):
        """
        form 또는 body 형태로 들어오는 데이터를 양식에 맞게 정리
          - 항목: ca_name, wr_password, wr_name, wr_email, wr_homepage, wr_option, wr_link1, wr_link2, wr_content
        """
        category_list = self.board.bo_category_list.split("|") if self.board.bo_category_list else []
        if category_list:
            if not data.ca_name or data.ca_name not in category_list:
                self.raise_exception(
                    status_code=400,
                    detail=f"ca_name: {data.ca_name}, 잘못된 분류입니다. 분류는 {','.join(category_list)} 중 하나여야 합니다."
                )
        else:
            data.ca_name = ""
        self.validate_wr_password(data.wr_password)
        data.wr_password = create_hash(data.wr_password) if data.wr_password else ""
        data.wr_name = self.set_wr_name(self.member, data.wr_name)
        data.wr_email = getattr(self.member, "mb_email", data.wr_email)
        data.wr_homepage = getattr(self.member, "mb_homepage", data.wr_homepage)

        # 옵션 설정
        options = [opt for opt in [html, secret, mail] if opt]
        data.wr_option = ",".join(map(str, options))

        # 링크 설정
        if not self.is_link_level():
            data.wr_link1 = ""
            data.wr_link2 = ""

        # Stored XSS 방지
        data.wr_content = self.get_cleaned_data(data.wr_content)

    def set_notice(self, wr_id: int, notice: bool):
        """공지글 설정"""
        self.board.bo_notice = self.set_board_notice(wr_id, notice)

    def send_write_mail_(self, write, parent_write):
        """메일 발송"""
        if self.use_email:
            send_write_mail(self.request, self.board, write, parent_write)

    def save_secret_session(self, wr_id: int, secret: str):
        """세션을 request에 저장"""
        if secret == "secret":
            self.request.session[f"ss_secret_{self.bo_table}_{wr_id}"] = True

    def delete_cache(self):
        """최신글 캐시 삭제"""
        FileCache().delete_prefix(f"latest-{self.bo_table}")
    
    def delete_auto_save(self, uid: str):
        """자동저장 글 삭제"""
        if uid:
            self.db.execute(delete(AutoSave).where(AutoSave.as_uid == uid))

    def upload_files(
        self,
        file_service: BoardFileService,
        write: WriteBaseModel,
        file_list: List[UploadFile],
        file_content: List[str] = None,
        file_dels: list = None
    ):
        """파일 업로드"""
        # files = []
        # print("file_list", file_list)
        # for file in file_list:
        #     if getattr(file, "size", None):
        #         files.append(file)

        if self.member.mb_id and self.member.mb_id != write.mb_id:
            self.raise_exception(status_code=403, detail="자신의 글에만 파일을 업로드할 수 있습니다.")

        if not self.is_upload_level():
            self.raise_exception(status_code=403, detail="파일 업로드 권한이 없습니다.")

        directory = os.path.join(self.FILE_DIRECTORY, self.bo_table)
        wr_file = write.wr_file

        # 경로 생성
        os.makedirs(directory, exist_ok=True)

        # 파일 삭제
        if file_dels:
            for bf_no in file_dels:
                file_service.delete_board_file(self.board.bo_table, write.wr_id, bf_no)
                wr_file -= 1

        # 파일 업로드 처리 및 파일정보 저장
        exclude_file = {"size": [], "ext": []}
        for file in file_list:
            index = file_list.index(file)

            if file.filename:
                # 관리자가 아니면서 설정한 업로드 사이즈보다 크거나 업로드 가능 확장자가 아니면 업로드하지 않음
                if not self.member.admin_type:
                    if not file_service.is_upload_size(self.board, file):
                        exclude_file["size"].append(file.filename)
                        continue
                    if not file_service.is_upload_extension(file):
                        exclude_file["ext"].append(file.filename)
                        continue

                board_file = file_service.get_board_file(self.board.bo_table, write.wr_id, index)
                bf_content = file_content[index] if file_content and file_content[index] else ""
                filename = file_service.get_filename(file.filename)
                if board_file:
                    # 기존파일 삭제
                    file_service.remove_file(board_file.bf_file)
                    # 파일 업로드 및 정보 업데이트
                    file_service.upload_file(directory, filename, file)
                    file_service.update_board_file(board_file, directory, filename, file, bf_content)
                else:
                    # 파일 업로드 및 정보 추가
                    file_service.upload_file(directory, filename, file)
                    file_service.insert_board_file(self.board.bo_table, write.wr_id, index,
                                                        directory, filename, file, bf_content)
                    wr_file += 1

        # exclude_file이 존재하면 파일 업로드 실패 메시지 출력
        msg = ""
        if exclude_file.get("size"):
            msg += f"{','.join(exclude_file['size'])} 파일은 업로드 용량({self.board.bo_upload_size}byte)을 초과하였습니다.\\n"
        if exclude_file.get("ext"):
            msg += f"{','.join(exclude_file['ext'])} 파일은 업로드 가능 확장자가 아닙니다.\\n"
        if msg:
            self.raise_exception(detail=msg, status_code=400)

        # 파일 개수 업데이트
        write.wr_file = wr_file
        self.db.commit()
