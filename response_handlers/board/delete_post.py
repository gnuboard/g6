
from fastapi import Request, HTTPException
from sqlalchemy import select, exists, delete

from core.database import db_session
from core.models import Board, Member, WriteBaseModel, BoardNew, Scrap
from lib.board_lib import AlertException, is_owner, insert_point, delete_point, BoardFileManager, FileCache
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

    def delete_write(self):
        """게시글 삭제 처리"""
        origin_write = self.write
        member_id = self.mb_id
        write_model = self.write_model
        db = self.db
        bo_table = self.bo_table
        board = self.board
        request = self.request

        write_member_mb_no = db.scalar(select(Member.mb_no).where(Member.mb_id == origin_write.mb_id))
        write_member = db.get(Member, write_member_mb_no)
        write_member_level = getattr(write_member, "mb_level", 1)

        # 권한 체크
        if self.admin_type != "super":
            if self.admin_type and write_member_level > self.member_level:
                self.raise_exception(status_code=403, detail="자신보다 높은 권한의 게시글은 삭제할 수 없습니다.")
            elif origin_write.mb_id and not is_owner(self.write, member_id):
                self.raise_exception(status_code=403, detail="자신의 게시글만 삭제할 수 있습니다.", )

            if isinstance(self.ClassException, AlertException):
                url = f"/bbs/password/delete/{self.bo_table}/{origin_write.wr_id}"
                if not origin_write.mb_id and not self.request.session.get(f"ss_delete_{self.bo_table}_{origin_write.wr_id}"):
                    query_params = remove_query_params(self.request, "token")
                    self.raise_exception(status_code=403, detail="비회원 글을 삭제할 권한이 없습니다.", url=set_url_query_params(url, query_params))
            else:
                if not origin_write.mb_id:
                    self.raise_exception(status_code=403, detail="비회원 글을 삭제할 권한이 없습니다.")
        
        # 답변글이 있을 때 삭제 불가

        exists_reply = db.scalar(
            exists(write_model)
            .where(
                write_model.wr_reply.like(f"{origin_write.wr_reply}%"),
                write_model.wr_num == origin_write.wr_num,
                write_model.wr_is_comment == 0,
                write_model.wr_id != origin_write.wr_id
            )
            .select()
        )
        if exists_reply:
            self.raise_exception(detail="답변이 있는 글은 삭제할 수 없습니다. \\n\\n우선 답변글부터 삭제하여 주십시오.", status_code=403)

        if not self.is_delete_by_comment(origin_write.wr_id):
            self.raise_exception(detail=f"이 글과 관련된 댓글이 {board.bo_count_delete}건 이상 존재하므로 삭제 할 수 없습니다.", status_code=403)

        # 원글 + 댓글
        delete_write_count = 0
        delete_comment_count = 0
        writes = db.scalars(
            select(write_model)
            .filter_by(wr_parent=origin_write.wr_id)
            .order_by(write_model.wr_id)
        ).all()
        for write in writes:
            # 원글 삭제
            if not write.wr_is_comment:
                # 원글 포인트 삭제
                if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "쓰기"):
                    insert_point(request, write.mb_id, board.bo_write_point * (-1), f"{board.bo_subject} {write.wr_id} 글 삭제")
                # 파일+섬네일 삭제
                BoardFileManager(board, write.wr_id).delete_board_files()

                delete_write_count += 1
                # TODO: 에디터 섬네일 삭제
            else:
                # 댓글 포인트 삭제
                if not delete_point(request, write.mb_id, board.bo_table, write.wr_id, "댓글"):
                    insert_point(request, write.mb_id, board.bo_comment_point * (-1), f"{board.bo_subject} {write.wr_id} 댓글 삭제")

                delete_comment_count += 1

        # 원글+댓글 삭제
        db.execute(delete(write_model).filter_by(wr_parent=origin_write.wr_id))

        # 최근 게시물 삭제
        db.execute(delete(BoardNew).where(
            BoardNew.bo_table == bo_table,
            BoardNew.wr_parent == origin_write.wr_id
        ))

        # 스크랩 삭제
        db.execute(delete(Scrap).filter_by(
            bo_table=bo_table,
            wr_id=origin_write.wr_id
        ))

        # 공지사항 삭제
        board.bo_notice = self.set_board_notice(origin_write.wr_id, False)

        # 게시글 갯수 업데이트
        board.bo_count_write -= delete_write_count
        board.bo_count_comment -= delete_comment_count

        db.commit()
        db.close()

        # 최신글 캐시 삭제
        FileCache().delete_prefix(f'latest-{bo_table}')


class DeletePostServiceAPI(DeletePostService):

    def raise_exception(self, status_code: int, detail: str = None):
        HTTPException(status_code, detail)