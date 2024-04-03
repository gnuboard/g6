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
    게시글 수정 클래스
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
        """글 삭제 시 댓글 수를 확인하여 삭제 여부를 결정"""
        if not self.is_modify_by_comment(self.wr_id):
            self.raise_exception(detail=f"이 글과 관련된 댓글이 {self.board.bo_count_modify}건 이상 존재하므로 수정 할 수 없습니다.", status_code=403)
    
    def update_children_category(self, data: WriteModel):
        """답글의 카테고리를 부모글의 카테고리로 변경"""
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
    API 요청에 사용되는 게시글 수정 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)