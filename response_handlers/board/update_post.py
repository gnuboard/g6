from typing_extensions import Union
from fastapi import Request, HTTPException
from sqlalchemy import update

from core.database import db_session
from core.models import Board, Member
from core.formclass import WriteForm
from api.v1.models.board import WriteModel
from .create_post import CreatePostService


class UpdatePostService(CreatePostService):
    """
    Template용 게시글 수정 클래스
    - Template response를 위한 로직 > CreatePostTemplate의 클래스 변수와 메소드를 상속, 오버라이딩하여 사용
    - API response와 공통된 로직 > UpdatePostCommon의 메소드를 사용
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
        wr_id: str,
    ):
        super().__init__(request, db, bo_table, board, member)
        self.wr_id = wr_id

    def validate_restrict_comment_count(self):
        if not self.is_modify_by_comment(self.wr_id):
            self.raise_exception(detail=f"이 글과 관련된 댓글이 {self.board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.", status_code=403)
    
    def update_children_category(self, data: WriteModel):
        if data.ca_name:
            self.db.execute(
                update(self.write_model).where(self.write_model.wr_parent == self.wr_id)
                .values(ca_name=data.ca_name)
            )
            self.db.commit()

    def save_write(self, write, data: Union[WriteForm, WriteModel]):
        """게시글 수정 사항을 저장"""
        for field, value in data.__dict__.items():
            if value:
                setattr(write, field, value)
        self.db.commit()


class UpdatePostServiceAPI(UpdatePostService):
    """
    API용 게시글 수정 클래스
    - API response를 위한 로직 > CreatePostAPI의 클래스 변수와 메소드를 상속, 오버라이딩하여 사용
    - Template response와 공통된 로직 > UpdatePostCommon의 메소드를 사용
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)