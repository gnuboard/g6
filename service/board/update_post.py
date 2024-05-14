from typing_extensions import Union, Annotated
from fastapi import Request, Path, Depends, Form
from sqlalchemy import update, select, func

from core.database import db_session
from core.models import WriteBaseModel
from core.formclass import WriteForm, WriteCommentForm
from lib.board_lib import generate_reply_character, is_owner
from lib.g5_compatibility import G5Compatibility
from lib.template_filters import number_format
from lib.html_sanitizer import content_sanitizer
from lib.pbkdf2 import create_hash, validate_password
from api.v1.models.board import WriteModel, CommentModel
from service.point_service import PointService
from . import BoardService


class UpdatePostService(BoardService):
    """
    게시글 수정 클래스
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(...)],
        wr_id: Annotated[int, Path(...)],
    ):
        super().__init__(request, db, bo_table)
        self.wr_id = wr_id

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(...)],
        wr_id: Annotated[int, Path(...)],
    ):
        instance = cls(request, db, bo_table, wr_id)
        return instance

    def validate_author(self, write: WriteBaseModel, wr_password: str = None):
        """작성자 확인"""
        if not is_owner(write, self.member.mb_id) and not validate_password(wr_password, write.wr_password):
            self.raise_exception(detail="작성자만 수정할 수 있습니다.", status_code=403)

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


class CommentService(UpdatePostService):
    """댓글 관리 클래스"""

    def __init__(
        self,
        request: Request,
        db: db_session,
        point_service: Annotated[PointService, Depends()],
        bo_table: Annotated[str, Path(...)],
        wr_id: Annotated[int, Form(...)],
    ):
        super().__init__(request, db, bo_table, wr_id)
        self.g5_instance = G5Compatibility(db)
        self.point_service = point_service

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        point_service: Annotated[PointService, Depends()],
        bo_table: Annotated[str, Path(...)],
        wr_id: Annotated[int, Form(...)],
    ):
        instance = cls(request, db, point_service, bo_table, wr_id)
        return instance

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

    def get_parent_comment(self, comment_id: int) -> WriteBaseModel:
        """댓글 존재 여부 확인"""
        parent_comment = self.db.get(self.write_model, comment_id)
        if not parent_comment:
            self.raise_exception(detail=f"{comment_id} : 존재하지 않는 댓글입니다.", status_code=404)
        return parent_comment

    def validate_write_comment_paring(self, wr_parent: int):
        """댓글과 게시글의 연관성 검증"""
        if self.wr_id != wr_parent:
            self.raise_exception(detail="작성하려는 대댓글의 댓글이, 부모글의 댓글이 아닙니다.", status_code=403)

    def save_comment(
            self, data: Union[WriteCommentForm, CommentModel], write: WriteBaseModel
    ) -> WriteBaseModel:
        """댓글을 저장하고 댓글 ORM 객체를 반환"""
        comment = self.write_model()

        if data.comment_id:
            # 해당 생성 댓글이 대댓글(댓글의 댓글)인 경우의 로직
            parent_comment = self.get_parent_comment(data.comment_id)
            self.validate_write_comment_paring(parent_comment.wr_parent)
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
        if not comment.mb_id and not data.wr_password:
            self.raise_exception(detail="비회원 댓글 작성 시 비밀번호는 필수입니다.", status_code=403)
        comment.wr_password = create_hash(data.wr_password) if data.wr_password else ""
        comment.wr_name = self.set_wr_name(self.member, data.wr_name)
        self.validate_anonymous_password(data)
        comment.wr_email = getattr(self.member, "mb_email", "")
        comment.wr_homepage = getattr(self.member, "mb_homepage", "")
        comment.wr_datetime = comment.wr_last = self.g5_instance.get_wr_last_now(self.write_model.__tablename__)
        comment.wr_ip = self.request.client.host
        self.db.add(comment)

        # 게시글에 댓글 수 증가
        write.wr_comment +=  1

        self.db.commit()
        return comment

    def add_point(self, comment: WriteBaseModel):
        """포인트 추가"""
        if self.member.mb_id:
            point = self.board.bo_comment_point
            content = f"{self.board.bo_subject} {comment.wr_parent}-{comment.wr_id} 댓글쓰기"
            self.point_service.save_point(self.member.mb_id, point, content,
                                          self.bo_table, comment.wr_id, "댓글")
