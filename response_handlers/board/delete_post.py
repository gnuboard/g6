
from fastapi import Request, HTTPException
from sqlalchemy import select, exists, delete, update

from core.database import db_session
from core.models import Board, Member, WriteBaseModel, BoardNew, Scrap
from lib.board_lib import is_owner, insert_point, delete_point, BoardFileManager, FileCache
from lib.common import remove_query_params, set_url_query_params
from .base_handler import BoardService


class DeletePostService(BoardService):
    """
    게시글 삭제 공통 처리 클래스
    Template, API 클래스에서 상속받아 사용
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        wr_id: int,
        write: WriteBaseModel,
        member: Member,
    ):
        super().__init__(request, db, bo_table, board, member)
        self.wr_id = wr_id
        self.write = write
        self.write_member_mb_no = self.db.scalar(select(Member.mb_no).where(Member.mb_id == write.mb_id))
        self.write_member = self.db.get(Member, self.write_member_mb_no)
        self.write_member_level = getattr(self.write_member, "mb_level", 1)

    def validate_level(self, with_session: bool = True):
        if self.admin_type == "super":
            return

        if self.admin_type and self.write_member_level > self.member_level:
            self.raise_exception(status_code=403, detail="자신보다 높은 권한의 게시글은 삭제할 수 없습니다.")
        elif self.write.mb_id and not is_owner(self.write, self.mb_id):
            self.raise_exception(status_code=403, detail="자신의 게시글만 삭제할 수 있습니다.", )

        if not self.write.mb_id:
            if with_session and not self.request.session.get(f"ss_delete_{self.bo_table}_{self.wr_id}"):
                url = f"/bbs/password/delete/{self.bo_table}/{self.wr_id}"
                query_params = remove_query_params(self.request, "token")
                self.raise_exception(status_code=403, detail="비회원 글을 삭제할 권한이 없습니다.", url=set_url_query_params(url, query_params))
            elif not with_session:
                self.raise_exception(status_code=403, detail="비회원 글을 삭제할 권한이 없습니다.")
        
    def validate_exists_reply(self):
        """답변글이 있을 때 삭제 불가"""
        exists_reply = self.db.scalar(
            exists(self.write_model)
            .where(
                self.write_model.wr_reply.like(f"{self.write.wr_reply}%"),
                self.write_model.wr_num == self.write.wr_num,
                self.write_model.wr_is_comment == 0,
                self.write_model.wr_id != self.wr_id
            )
            .select()
        )
        if exists_reply:
            self.raise_exception(detail="답변이 있는 글은 삭제할 수 없습니다. 우선 답변글부터 삭제하여 주십시오.", status_code=403)

    def validate_exists_comment(self):
         """게시판 설정에서 정해놓은 댓글 개수 이상일 때 삭제 불가"""
         if not self.is_delete_by_comment(self.wr_id):
            self.raise_exception(detail=f"이 글과 관련된 댓글이 {self.board.bo_count_delete}건 이상 존재하므로 삭제 할 수 없습니다.", status_code=403)

    def delete_write(self):
        """게시글 삭제 처리"""
        write_model = self.write_model
        db = self.db
        bo_table = self.bo_table
        board = self.board

        # 원글 + 댓글
        delete_write_count = 0
        delete_comment_count = 0
        writes = db.scalars(
            select(write_model)
            .filter_by(wr_parent=self.wr_id)
            .order_by(write_model.wr_id)
        ).all()
        for write in writes:
            # 원글 삭제
            if not write.wr_is_comment:
                # 원글 포인트 삭제
                if not delete_point(self.request, write.mb_id, bo_table, self.wr_id, "쓰기"):
                    insert_point(self.request, write.mb_id, board.bo_write_point * (-1), f"{board.bo_subject} {self.wr_id} 글 삭제")
                # 파일+섬네일 삭제
                BoardFileManager(board, self.wr_id).delete_board_files()

                delete_write_count += 1
                # TODO: 에디터 섬네일 삭제
            else:
                # 댓글 포인트 삭제
                if not delete_point(self.request, write.mb_id, bo_table, self.wr_id, "댓글"):
                    insert_point(self.request, write.mb_id, board.bo_comment_point * (-1), f"{board.bo_subject} {self.wr_id} 댓글 삭제")

                delete_comment_count += 1

        # 원글+댓글 삭제
        db.execute(delete(write_model).filter_by(wr_parent=self.wr_id))

        # 최근 게시물 삭제
        db.execute(delete(BoardNew).where(
            BoardNew.bo_table == bo_table,
            BoardNew.wr_parent == self.wr_id
        ))

        # 스크랩 삭제
        db.execute(delete(Scrap).filter_by(
            bo_table=bo_table,
            wr_id=self.wr_id
        ))

        # 공지사항 삭제
        board.bo_notice = self.set_board_notice(self.wr_id, False)

        # 게시글 갯수 업데이트
        board.bo_count_write -= delete_write_count
        board.bo_count_comment -= delete_comment_count

        db.commit()
        db.close()

        # 최신글 캐시 삭제
        FileCache().delete_prefix(f'latest-{bo_table}')


class DeletePostServiceAPI(DeletePostService):

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class DeleteCommentService(DeletePostService):
    """댓글 삭제 처리 클래스"""

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        wr_id: int,
        write: WriteBaseModel,
        member: Member,
    ):
        super().__init__(request, db, bo_table, board, wr_id, write, member)
        self.wr_id = wr_id
        self.comment = write

    def check_authority(self, with_session: bool = True):
        """
        게시글 삭제 권한 검증
        - Template 용으로 사용하는 경우 with_session 인자는 True 값으로 하며
          익명 댓글일 경우 session을 통해 권한을 검증합니다.
        - API 용으로 사용하는 경우 with_session 인자는 False 값으로 사용합니다.
        """
        if self.admin_type:
            return

        # 익명 댓글
        if not self.comment.mb_id:

            # API 요청일때
            if not with_session:
                self.raise_exception(detail="삭제할 권한이 없습니다.", status_code=403)

            # 템플릿 요청일때
            session_name = f"ss_delete_comment_{self.bo_table}_{self.wr_id}"
            if self.request.session.get(session_name):
                return
            url = f"/bbs/password/comment-delete/{self.bo_table}/{self.wr_id}"
            query_params = remove_query_params(self.request, "token")
            self.raise_exception(detail="삭제할 권한이 없습니다.", status_code=403, url=set_url_query_params(url, query_params))

        # 회원 댓글
        if not is_owner(self.comment, self.mb_id):
            self.raise_exception(detail="자신의 댓글만 삭제할 수 있습니다.", status_code=403)

    def delete_comment(self):
        """댓글 삭제 처리"""
        write_model= self.write_model

        # 댓글 삭제
        self.db.delete(self.comment)

        # 게시글에 댓글 수 감소
        self.db.execute(
            update(write_model).values(wr_comment=write_model.wr_comment - 1)
            .where(write_model.wr_id == self.comment.wr_parent)
        )

        self.db.commit()


class DeleteCommentServiceAPI(DeleteCommentService):
    """
    댓글 삭제 처리 API 클래스, 
    상속받은 클래스에서 예외처리 함수를 오버라이딩 하여 사용합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code, detail)


class ListDeleteService(BoardService):

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
    ):
        super().__init__(request, db, bo_table, board, member)

    def delete_writes(self, wr_ids: list):
        """게시글 목록 삭제"""
        write_model = self.write_model
        writes = self.db.scalars(
            select(write_model)
            .where(write_model.wr_id.in_(wr_ids))
        ).all()
        for write in writes:
            self.db.delete(write)
            # 원글 포인트 삭제
            if not delete_point(self.request, write.mb_id, self.bo_table, write.wr_id, "쓰기"):
                insert_point(self.request, write.mb_id, self.board.bo_write_point * (-1), f"{self.board.bo_subject} {write.wr_id} 글 삭제")
            
            # 파일 삭제
            BoardFileManager(self.board, write.wr_id).delete_board_files()

            # TODO: 댓글 삭제
        self.db.commit()

        # 최신글 캐시 삭제
        FileCache().delete_prefix(f'latest-{self.bo_table}')

        # TODO: 게시글 삭제시 같이 삭제해야할 것들 추가


class ListDeleteServiceAPI(ListDeleteService):

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code, detail)


