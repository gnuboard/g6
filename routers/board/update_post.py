from typing_extensions import Annotated, List
from fastapi import Request, Depends, Form, Path, File, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import update

from core.database import db_session
from core.models import Board, Member
from core.formclass import WriteForm
from lib.dependencies import get_board, get_write, get_login_member
from api.v1.models.board import WriteModel
from api.v1.dependencies.board import get_current_member, validate_write
from .create_post import CreatePostTemplate, CreatePostAPI


class UpdatePostCommon:

    def validate_restrict_comment_count(self):
        if not self.is_modify_by_comment(self.wr_id):
            raise self.ClassException(f"이 글과 관련된 댓글이 {self.board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.", 403)
    
    def update_children_category(self, data):
        if data.ca_name:
            self.db.execute(
                update(self.write_model).where(self.write_model.wr_parent == self.wr_id)
                .values(ca_name=data.ca_name)
            )
            self.db.commit()


class UpdatePostTemplate(CreatePostTemplate, UpdatePostCommon):

    def __init__(
        self,
        request: Request,
        db: db_session,
        member: Annotated[Member, Depends(get_login_member)],
        board: Annotated[Board, Depends(get_board)],
        bo_table: str = Path(...),
        wr_id: str = Path(...),
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
        self.wr_id = wr_id
        self.uid = uid
        self.form_data = form_data
        self.files = files
        self.file_content = file_content
        self.file_dels = file_dels
        self.recaptcha_response = recaptcha_response

    def save_write(self, write):
        for field, value in self.form_data.__dict__.items():
            if value:
                setattr(write, field, value)
        self.db.commit()

    def update_post(self):
        self.validate_restrict_comment_count() # only update
        write = get_write(self.db, self.bo_table, self.wr_id)
        
        self.validate_secret_board()
        self.validate_post_content(self.form_data.wr_subject, self.form_data.wr_content)
        self.arrange_data(self.form_data)
        self.save_secret_session(self.wr_id)
        self.save_write(write)
        self.set_notice(write.wr_id, self.notice)
        self.delete_auto_save(self.uid)
        if self.files:
            self.upload_files(write, self.files, self.file_content, self.file_dels)
        self.update_children_category(self.form_data) # only update
        self.delete_cache()
        return write

    def response(self):
        write = self.update_post()
        redirect_url = self.get_redirect_url(write)
        return RedirectResponse(redirect_url, status_code=303)


class UpdatePostAPI(CreatePostAPI, UpdatePostCommon):

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(...)],
        board: Annotated[Board, Depends(get_board)],
        wr_data: Annotated[WriteModel, Depends(validate_write)],
        member: Annotated[Member, Depends(get_current_member)],
        wr_id: Annotated[str, Path(...)],
    ):
        super().__init__(
            request=request, db=db, bo_table=bo_table, board=board, member=member, wr_data=wr_data
        )
        self.wr_id = wr_id
        self.parent_id = wr_data.parent_id
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
        bo_table = self.bo_table
        request = self.request
        db = self.db
        wr_id = self.wr_id
        wr_data = self.wr_data
        write = get_write(db, bo_table, wr_id)
        wr_data_dict = wr_data.model_dump()
        for key, value in wr_data_dict.items():
            setattr(write, key, value)
        write.wr_ip = request.client.host
        db.commit()
        return write

    def update_post(self):
        self.validate_restrict_comment_count() # only update
        self.validate_secret_board()
        self.validate_post_content(self.wr_data.wr_subject, self.wr_data.wr_content)
        self.arrange_data(self.wr_data)
        write = self.save_write()
        self.set_notice(self.wr_id, self.notice)
        self.update_children_category(self.wr_data) # only update
        self.delete_cache()
        return write

    def response(self):
        self.update_post()
        return {"result": "updated"}