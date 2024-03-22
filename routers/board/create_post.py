import os
from datetime import datetime
from typing_extensions import Annotated, List, Union
from fastapi import Request, HTTPException, Depends, Form, Path, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, inspect

from core.database import db_session
from core.models import Board, Member, WriteBaseModel, AutoSave
from core.formclass import WriteForm
from lib.board_lib import (
    is_write_delay, AlertException, insert_point, BoardFileManager,
    FileCache, get_next_num, generate_reply_character, send_write_mail,
    set_write_delay, insert_board_new
)
from lib.common import remove_query_params, set_url_query_params, filter_words, make_directory
from lib.html_sanitizer import content_sanitizer
from lib.dependencies import validate_captcha, get_board, check_login_member
from lib.pbkdf2 import create_hash
from api.v1.models.board import WriteModel
from api.v1.dependencies.board import get_current_member, validate_write
from .base import BoardRouter, PointEnum


class CreatePostCommon(BoardRouter):

    FILE_DIRECTORY = "data/file/"

    def __init__(self, request: Request, db: db_session, board: Board, bo_table: str,
                member: Member, parent_id: int = None, notice: bool = False,
                secret: str = "", html: str = "", mail: str = ""):
        super().__init__(request, db, bo_table, board, member)
        self.parent_id = parent_id
        self.notice = notice
        self.secret = secret
        self.html = html
        self.mail = mail

    def validate_secret_board(self):
        if self.admin_type:
            return

        # 비밀글 사용여부 체크
        if not self.board.bo_use_secret and "secret" in self.secret and "secret" in self.html and "secret" in self.mail:
            raise self.ClassException(status_code=403, detail="비밀글 미사용 게시판 이므로 비밀글로 등록할 수 없습니다.")

        # 비밀글 옵션에 따라 비밀글 설정
        if self.board.bo_use_secret == 2:
            self.secret = "secret"

    def validate_post_content(self, wr_subject, wr_content):
        subject_filter_word = filter_words(self.request, wr_subject)
        content_filter_word = filter_words(self.request, wr_content)
        if subject_filter_word or content_filter_word:
            word = subject_filter_word if subject_filter_word else content_filter_word
            raise self.ClassException(detail=f"제목/내용에 금지단어({word})가 포함되어 있습니다.", status_code=400)

    def get_cleaned_data(self, content):
        return content_sanitizer.get_cleaned_data(content)

    ## create 전용
    def get_parent_post(self, parent_id: int):
        """부모글 호출"""
        if not parent_id:
            return None

        # 답변 권한 검증
        if not self.is_reply_level():
            raise self.ClassException(detail="답변글을 작성할 권한이 없습니다.", status_code=403)

        # 부모글 호출
        parent_write = self.db.get(self.write_model, parent_id)
        if not parent_write:
            raise self.ClassException("답변할 글이 존재하지 않습니다.", 404)
        return parent_write

    def arrange_data(self, data: Union[WriteForm, WriteModel]):
        category_list = self.board.bo_category_list.split("|") if self.board.bo_category_list else []
        if category_list:
            if not data.ca_name or data.ca_name not in category_list:
                raise self.ClassException(
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
        options = [opt for opt in [self.html, self.secret, self.mail] if opt]
        data.wr_option = ",".join(map(str, options))

        # 링크 설정
        if not self.is_link_level():
            data.wr_link1 = ""
            data.wr_link2 = ""

        # Stored XSS 방지
        data.wr_content = self.get_cleaned_data(data.wr_content)

    ## create 전용
    def add_point(self, write, parent_write: WriteBaseModel = None):
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

    def upload_files(self, write, files, file_content, file_dels):
        """파일 업로드"""
        if not self.is_upload_level():
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
            if isinstance(self.ClassException, AlertException):
                redirect_url = self.get_redirect_url(write)
                raise self.ClassException(detail=msg, status_code=400, url=redirect_url)

            raise self.ClassException(detail=msg, status_code=400)

        # 파일 개수 업데이트
        write.wr_file = wr_file
        self.db.commit()

    def delete_cache(self):
        """최신글 캐시 삭제"""
        FileCache().delete_prefix(f"latest-{self.bo_table}")


class CreatePostTemplate(CreatePostCommon):

    ClassException = AlertException

    def __init__(
        self,
        request: Request,
        db: db_session,
        member: Annotated[Member, Depends(check_login_member)],
        board: Annotated[Board, Depends(get_board)],
        bo_table: str = Path(...),
        parent_id: int = Form(None),
        notice: bool = Form(False),
        secret: str = Form(""),
        html: str = Form(""),
        mail: str = Form(""),
        form_data: WriteForm = Depends(), # only Template
        uid: str = Form(None), # only Template
        files: List[UploadFile] = File(None, alias="bf_file[]"), # only Template
        file_content: list = Form(None, alias="bf_content[]"), # only Template
        file_dels: list = Form(None, alias="bf_file_del[]"), # only Template
        recaptcha_response: str = Form("", alias="g-recaptcha-response"), # only Template
    ):
        super().__init__(
            request=request, db=db, bo_table=bo_table, board=board, member=member,
            parent_id=parent_id, notice=notice, secret=secret, html=html, mail=mail
        )
        self.uid = uid
        self.form_data = form_data
        self.files = files
        self.file_content = file_content
        self.file_dels = file_dels
        self.recaptcha_response = recaptcha_response

    def validate_write_delay(self):
        """글쓰기 간격 검증"""
        if not is_write_delay(self.request):
            raise self.ClassException(status_code=400, detail="너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.")

    async def validate_captcha_(self):
        """캡차 검증"""
        if self.use_captcha:
            await validate_captcha(self.request, self.recaptcha_response)

    def save_write(self, parent_id):
        parent_write = self.get_parent_post(parent_id)
        write = self.write_model(
            wr_num=parent_write.wr_num if parent_write else get_next_num(self.bo_table),
            wr_reply=generate_reply_character(self.board, parent_write) if parent_write else "",
            wr_datetime=datetime.now(),
            mb_id=self.mb_id or "",
            wr_ip=self.request.client.host,
            **self.form_data.__dict__
        )
        self.db.add(write)
        self.db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        self.board.bo_count_write = self.board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        self.db.commit()
        return write

    def save_secret_session(self, wr_id: int):
        """세션 저장"""
        if self.secret:
            self.request.session[f"ss_secret_{self.bo_table}_{wr_id}"] = True

    def delete_auto_save(self, uid: str):
        """자동저장 글 삭제"""
        if uid:
            self.db.execute(delete(AutoSave).where(AutoSave.as_uid == uid))

    def get_redirect_url(self, write):
        query_params = remove_query_params(self.request, "parent_id")
        url = f"/board/{self.bo_table}/{write.wr_id}"
        return set_url_query_params(url, query_params)

    def create_post(self):
        self.validate_write_delay()
        self.validate_captcha_()
        self.validate_secret_board()
        self.validate_post_content(self.form_data.wr_subject, self.form_data.wr_content)
        self.validate_possible_point(PointEnum.WRITE)
        self.arrange_data(self.form_data)
        write = self.save_write(self.parent_id)
        # 글 작성 시간 기록
        set_write_delay(self.request)
        self.save_secret_session(write.wr_id)
        insert_board_new(self.bo_table, write)
        self.add_point(write)
        self.send_write_mail_(write, self.parent_id)
        self.set_notice(write.wr_id, self.notice)
        self.delete_auto_save(self.uid)
        if self.files:
            self.upload_files(write, self.files, self.file_content, self.file_dels)
        self.delete_cache()
        self.db.commit()
        return write

    def response(self):
        write = self.create_post()
        redirect_url = self.get_redirect_url(write)
        return RedirectResponse(redirect_url, status_code=303)


class CreatePostAPI(CreatePostCommon):

    ClassException = HTTPException

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(...)],
        board: Annotated[Board, Depends(get_board)],
        wr_data: Annotated[WriteModel, Depends(validate_write)],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        super().__init__(
            request=request, db=db, bo_table=bo_table, board=board,
            parent_id=wr_data.parent_id, notice=wr_data.notice, secret=wr_data.secret,
            html=wr_data.html, mail=wr_data.mail, member=member
        )
        self.wr_subject = wr_data.wr_subject
        self.wr_content = wr_data.wr_content
        self.wr_password = wr_data.wr_password
        self.wr_name = wr_data.wr_name
        self.wr_email = wr_data.wr_email
        self.wr_homepage = wr_data.wr_homepage
        self.wr_link1 = wr_data.wr_link1
        self.wr_link2 = wr_data.wr_link2
        self.wr_datetime = wr_data.wr_datetime
        self.wr_data = wr_data

    def save_write(self):
        parent_write = self.get_parent_post(self.parent_id)
        wr_data_dict = self.wr_data.model_dump()
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

    def create_post(self):
        self.validate_secret_board()
        self.validate_post_content(self.wr_subject, self.wr_content)
        self.validate_possible_point(PointEnum.WRITE)
        self.arrange_data(self.wr_data)
        write = self.save_write()
        insert_board_new(self.bo_table, write)
        self.add_point(write)
        self.send_write_mail_(write, self.parent_id)
        self.set_notice(write.wr_id, self.notice)
        self.delete_cache()
        self.db.commit()
        return write

    def response(self):
        self.create_post()
        return {"result": "created"}