import os
from datetime import datetime
from typing_extensions import List, Union
from fastapi import Request, HTTPException, UploadFile
from sqlalchemy import delete, inspect, select, func, update

from core.database import db_session
from core.models import Board, Member, WriteBaseModel, AutoSave, BoardNew, BoardGood, Scrap
from core.formclass import WriteForm
from lib.board_lib import (
    is_write_delay,insert_point, BoardFileManager,
    FileCache, get_next_num, generate_reply_character, send_write_mail,
)
from lib.common import remove_query_params, set_url_query_params, filter_words, make_directory, dynamic_create_write_table, cut_name
from lib.html_sanitizer import content_sanitizer
from lib.dependencies import validate_captcha as lib_validate_captcha
from lib.pbkdf2 import create_hash
from lib.g5_compatibility import G5Compatibility
from lib.template_filters import number_format, datetime_format
from api.v1.models.board import WriteModel
from .base_handler import BoardService


class CreatePostService(BoardService):
    """
    게시글 생성 공통 클래스
    Template, API 클래스에서 상속받아 사용
    """

    FILE_DIRECTORY = "data/file/"

    def __init__(self, request: Request, db: db_session, bo_table: str, board: Board, member: Member):
        super().__init__(request, db, bo_table, board, member)

    def validate_write_level(self):
        if not self.is_write_level():
            self.raise_exception(detail="글을 작성할 권한이 없습니다.", status_code=403)

    def validate_secret_board(self, secret: str, html: str, mail: str):
        """게시판의 비밀글 사용여부 검증"""
        if self.admin_type:
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

    def get_cleaned_data(self, content):
        """Stored XSS 방지용 데이터 정제"""
        return content_sanitizer.get_cleaned_data(content)

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
            self.raise_exception("답변글(댓글)을 쓸 원본 글이 존재하지 않습니다.", 404)
        return parent_write

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

    def add_point(self, write, parent_write: WriteBaseModel = None):
        """포인트 추가"""
        if self.mb_id:
            point = self.board.bo_comment_point if parent_write else self.board.bo_write_point
            content = f"{self.board.bo_subject} {write.wr_id} 글" + ("답변" if parent_write else "쓰기")
            insert_point(self.request, self.mb_id, point, content, self.bo_table, write.wr_id, "쓰기")

    def send_write_mail_(self, write, parent_write):
        """메일 발송"""
        if self.use_email:
            send_write_mail(self.request, self.board, write, parent_write)

    def set_notice(self, wr_id: int, notice: bool):
        """공지글 설정"""
        self.board.bo_notice = self.set_board_notice(wr_id, notice)

    def upload_files(self, write, files: List[UploadFile], file_content: list = None, file_dels: list = None):
        """파일 업로드"""
        if not self.is_upload_level() or not files:
            return

        file_manager = BoardFileManager(self.board, write.wr_id)
        directory = os.path.join(self.FILE_DIRECTORY, self.bo_table)
        wr_file = write.wr_file

        # 경로 생성
        make_directory(directory)

        # 파일 삭제
        if file_dels:
            for bf_no in file_dels:
                file_manager.delete_board_file(bf_no)
                wr_file -= 1

        # 파일 업로드 처리 및 파일정보 저장
        exclude_file = {"size": [], "ext": []}
        for file in files:
            index = files.index(file)
            if file.filename:
                # 관리자가 아니면서 설정한 업로드 사이즈보다 크거나 업로드 가능 확장자가 아니면 업로드하지 않음
                if not self.admin_type:
                    if not file_manager.is_upload_size(file):
                        exclude_file["size"].append(file.filename)
                        continue
                    if not file_manager.is_upload_extension(self.request, file):
                        exclude_file["ext"].append(file.filename)
                        continue

                board_file = file_manager.get_board_file(index)
                bf_content = file_content[index] if file_content else ""
                filename = file_manager.get_filename(file.filename)
                if board_file:
                    # 기존파일 삭제
                    file_manager.remove_file(board_file.bf_file)
                    # 파일 업로드 및 정보 업데이트
                    file_manager.upload_file(directory, filename, file)
                    file_manager.update_board_file(board_file, directory, filename, file, bf_content)
                else:
                    # 파일 업로드 및 정보 추가
                    file_manager.upload_file(directory, filename, file)
                    file_manager.insert_board_file(index, directory, filename, file, bf_content)
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

    def delete_cache(self):
        """최신글 캐시 삭제"""
        FileCache().delete_prefix(f"latest-{self.bo_table}")

    def save_write(self, parent_id, data: Union[WriteForm, WriteModel]):
        """게시글을 저장"""
        parent_write = self.get_parent_post(parent_id)
        write = self.write_model(
            wr_num=parent_write.wr_num if parent_write else get_next_num(self.bo_table),
            wr_reply=generate_reply_character(self.board, parent_write) if parent_write else "",
            wr_datetime=datetime.now(),
            mb_id=self.mb_id or "",
            wr_ip=self.request.client.host,
            **data.__dict__
        )
        self.db.add(write)
        self.db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        self.board.bo_count_write = self.board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        self.db.commit()
        return write

    async def validate_captcha(self, recaptcha_response: str):
        """캡차 검증"""
        if self.use_captcha:
            await lib_validate_captcha(self.request, recaptcha_response)

    def validate_write_delay(self):
        """글쓰기 간격 검증"""
        if not is_write_delay(self.request):
            self.raise_exception(status_code=400, detail="너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.")

    def delete_auto_save(self, uid: str):
        """자동저장 글 삭제"""
        if uid:
            self.db.execute(delete(AutoSave).where(AutoSave.as_uid == uid))

    def save_secret_session(self, wr_id: int, secret: str):
        """세션을 request에 저장"""
        if secret == "secret":
            self.request.session[f"ss_secret_{self.bo_table}_{wr_id}"] = True

    def get_redirect_url(self, write):
        """리다이렉트 URL 생성"""
        query_params = remove_query_params(self.request, "parent_id")
        url = f"/board/{self.bo_table}/{write.wr_id}"
        return set_url_query_params(url, query_params)


class CreatePostServiceAPI(CreatePostService):

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
    
    def save_write(self, parent_id, wr_data):
        """게시글을 저장"""
        parent_write = self.get_parent_post(parent_id)
        wr_data_dict = wr_data.model_dump()
        model_fields = inspect(self.write_model).columns.keys()
        filtered_wr_data = {key: value for key, value in wr_data_dict.items() if key in model_fields}
        write = self.write_model(**filtered_wr_data)
        write.wr_num = parent_write.wr_num if parent_write else get_next_num(self.bo_table)
        write.wr_reply = generate_reply_character(self.board, parent_write) if parent_write else ""
        write.mb_id = self.mb_id if self.mb_id else ''
        write.wr_ip = self.request.client.host
        self.db.add(write)
        self.db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        self.board.bo_count_write = self.board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        self.db.commit()
        return write


class CreateCommentService(CreatePostService):
    """댓글 생성 클래스"""

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
    ):
        super().__init__(request, db, bo_table, board, member)
        self.g5_instance = G5Compatibility(db)

    def validate_comment_level(self):
        """댓글 작성 권한 검증"""
        if not self.is_comment_level():
            self.raise_exception(detail="댓글을 작성할 권한이 없습니다.", status_code=403)

    def validate_point(self):
        """댓글 작성에 필요한 포인트 검증"""
        point = self.board.bo_comment_point
        if not self.config.cf_use_point:
            return
        if self.is_comment_point():
            return

        point = number_format(abs(point))
        message = f"댓글 작성에 필요한 포인트({point})가 부족합니다. "
        if not self.member:
            message += "로그인 후 다시 시도해주세요."
        self.raise_exception(detail=message, status_code=403)

    def save_comment(self, data, write):
        """댓글을 저장하고 댓글 ORM 객체를 반환"""
        comment = self.write_model()

        if data.comment_id:
            # 해당 생성 댓글이 대댓글(댓글의 댓글)인 경우의 로직
            parent_comment = self.db.get(self.write_model, data.comment_id)
            if not parent_comment:
                self.raise_exception(detail=f"{data.comment_id} : 존재하지 않는 댓글입니다.", status_code=404)

            comment.wr_comment_reply = generate_reply_character(self.board, parent_comment)
            comment.wr_comment = parent_comment.wr_comment
        else:
            comment.wr_comment = self.db.scalar(
                select(func.coalesce(func.max(self.write_model.wr_comment), 0) + 1)
                .where(
                    self.write_model.wr_parent == write.wr_id,
                    self.write_model.wr_is_comment == 1
                ))

        wr_option = getattr(data, "wr_option", None) or getattr(data, "wr_secret", None) or ""

        # 댓글 추가정보 등록
        comment.ca_name = write.ca_name
        comment.wr_option = wr_option
        comment.wr_num = write.wr_num
        comment.wr_parent = write.wr_id
        comment.wr_is_comment = 1
        comment.wr_content = content_sanitizer.get_cleaned_data(data.wr_content)
        comment.mb_id = getattr(self.member, "mb_id", "")
        comment.wr_password = create_hash(data.wr_password) if data.wr_password else ""
        comment.wr_name = self.set_wr_name(self.member, data.wr_name)
        comment.wr_email = getattr(self.member, "mb_email", "")
        comment.wr_homepage = getattr(self.member, "mb_homepage", "")
        comment.wr_datetime = comment.wr_last = self.g5_instance.get_wr_last_now(self.write_model.__tablename__)
        comment.wr_ip = self.request.client.host
        self.db.add(comment)

        # 게시글에 댓글 수 증가
        write.wr_comment +=  1

        self.db.commit()
        return comment

    def add_point(self, comment):
        """포인트 추가"""
        if self.mb_id:
            point = self.board.bo_comment_point
            content = f"{self.board.bo_subject} {comment.wr_parent}-{comment.wr_id} 댓글쓰기", self.bo_table, comment.wr_id, "댓글"
            insert_point(self.request, self.mb_id, point, content, self.bo_table, comment.wr_id, "쓰기")


class CreateCommentServiceAPI(CreateCommentService):
    """
    댓글 생성을 위한 API 클래스
      - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class MoveUpdateService(BoardService):
    """게시글을 이동/복사하는 클래스입니다."""

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
        sw: str,
    ):
        super().__init__(request, db, bo_table, board, member)
        self.sw = sw
        self.act = "이동" if sw == "move" else "복사"

    def get_origin_writes(self, wr_ids):
        """선택된 원본 글들을 가져옵니다."""
        origin_writes = self.db.scalars(
            select(self.write_model)
            .where(self.write_model.wr_id.in_(wr_ids.split(',')))
        ).all()
        return origin_writes

    def move_copy_post(self, target_bo_tables: list, origin_writes: WriteBaseModel):
        """게시글들을 복사/이동 합니다."""
        origin_board = self.board
        origin_bo_table = self.bo_table

        # 게시글 복사/이동 작업 반복
        file_cache = FileCache()
        for target_bo_table in target_bo_tables:
            for origin_write in origin_writes:
                target_write_model = dynamic_create_write_table(target_bo_table)
                target_write = target_write_model()

                # 복사/이동 로그 기록
                if not origin_write.wr_is_comment and self.config.cf_use_copy_log:
                    nick = cut_name(self.request, self.member.mb_nick)
                    log_msg = f"[이 게시물은 {nick}님에 의해 {datetime_format(datetime.now()) } {origin_board.bo_subject}에서 {self.act} 됨]"
                    if "html" in origin_write.wr_option:
                        log_msg = f'<div class="content_{self.sw}">' + log_msg + '</div>'
                    else:
                        log_msg = '\n' + log_msg

                # 게시글 복사
                initial_field = ["wr_id", "wr_parent"]
                for field in origin_write.__table__.columns.keys():
                    if field in initial_field:
                        continue
                    elif field == 'wr_content':
                        target_write.wr_content = origin_write.wr_content + log_msg
                    elif field == 'wr_num':
                        target_write.wr_num = get_next_num(target_bo_table)
                    else:
                        setattr(target_write, field, getattr(origin_write, field))

                if self.sw == "copy":
                    target_write.wr_good = 0
                    target_write.wr_nogood = 0
                    target_write.wr_hit = 0
                    target_write.wr_datetime = datetime.now()

                # 게시글 추가
                self.db.add(target_write)
                self.db.commit()
                # 부모아이디 설정
                target_write.wr_parent = target_write.wr_id
                self.db.commit()

                if self.sw == "move":
                    # 최신글 이동
                    self.db.execute(
                        update(BoardNew)
                        .where(BoardNew.bo_table == origin_board.bo_table, BoardNew.wr_id == origin_write.wr_id)
                        .values(bo_table=target_bo_table, wr_id=target_write.wr_id, wr_parent=target_write.wr_id)
                    )
                    # 게시글
                    if not origin_write.wr_is_comment:
                        # 추천데이터 이동
                        self.db.execute(
                            update(BoardGood)
                            .where(BoardGood.bo_table == target_bo_table, BoardGood.wr_id == target_write.wr_id)
                            .values(bo_table=target_bo_table, wr_id=target_write.wr_id)
                        )
                        # 스크랩 이동
                        self.db.execute(
                            update(Scrap)
                            .where(Scrap.bo_table == target_bo_table, Scrap.wr_id == target_write.wr_id)
                            .values(bo_table=target_bo_table, wr_id=target_write.wr_id)
                        )
                    # 기존 데이터 삭제
                    self.db.delete(origin_write)
                    self.db.commit()

                # 파일이 존재할 경우
                file_manager = BoardFileManager(origin_board, origin_write.wr_id)
                if file_manager.is_exist():
                    if self.sw == "move":
                        file_manager.move_board_files(CreatePostService.FILE_DIRECTORY, target_bo_table, target_write.wr_id)
                    else:
                        file_manager.copy_board_files(CreatePostService.FILE_DIRECTORY, target_bo_table, target_write.wr_id)

            # 최신글 캐시 삭제
            file_cache.delete_prefix(f'latest-{target_bo_table}')

        # 원본 게시판 최신글 캐시 삭제
        file_cache.delete_prefix(f'latest-{origin_bo_table}')


class MoveUpdateServiceAPI(MoveUpdateService):
    """
    게시글을 이동/복사하는 API 클래스입니다.
    상위클래스의 예외 처리 함수를 오버라이딩 하여 사용합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)