from datetime import datetime
from typing_extensions import List
from fastapi import Request, HTTPException
from sqlalchemy import select, func

from core.models import Board, BoardNew
from core.database import db_session
from core.exception import AlertException
from lib.service import BaseService
from lib.common import dynamic_create_write_table, cut_name, FileCache
from lib.point import delete_point, insert_point
from lib.board_lib import BoardFileManager


class BoardNewService(BaseService):
    """
    최신 게시글 관리 클래스(최신 게시글 목록 조회 및 삭제 등)
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
    ):
        self.request = request
        self.db = db
        self.config = request.state.config
        self.page_rows = self.config.cf_mobile_page_rows if request.state.is_mobile and self.config.cf_mobile_page_rows else self.config.cf_new_rows

    def raise_exception(self):
        raise AlertException(status_code=400, detail="검색 결과가 없습니다.")

    def format_datetime(self, wr_datetime: datetime):
        """
        당일인 경우 시간표시
        """
        current_datetime = datetime.now()

        if wr_datetime.date() == current_datetime.date():
            return wr_datetime.strftime("%H:%M")
        else:
            return wr_datetime.strftime("%y-%m-%d")

    def get_query(self, gr_id=None, mb_id=None, view=None) -> select:
        """검색 조건에 따라 query를 반환"""
        query = select().join(BoardNew.board).order_by(BoardNew.bn_id.desc())
        
        if gr_id:
            query = query.where(Board.gr_id == gr_id)
        if mb_id:
            query = query.where(BoardNew.mb_id == mb_id)
        if view == "write":
            query = query.where(BoardNew.wr_parent == BoardNew.wr_id)
        elif view == "comment":
            query = query.where(BoardNew.wr_parent != BoardNew.wr_id)
        return query

    def get_offset(self, current_page: int) -> int:
        """페이지 계산을 위한 offset 설정"""
        offset = (current_page - 1) * self.page_rows
        return offset

    def get_board_news(self, query: select, offset: int) -> List[BoardNew]:
        """최신글 목록 조회"""
        board_news = self.db.scalars(query.add_columns(BoardNew).offset(offset).limit(self.page_rows)).all()
        return board_news

    def get_total_count(self, query: select) -> int:
        """최신글 총 갯수 조회"""
        total_count = self.db.scalar(query.add_columns(func.count(BoardNew.bn_id)).order_by(None))
        return total_count

    def arrange_borad_news_data(self, board_news: list[BoardNew], total_count: int, offset: int):
        """최신글 결과 데이터 설정"""
        for new in board_news:
            new.num = total_count - offset - (board_news.index((new)))
            # 게시글 정보 조회
            write_model = dynamic_create_write_table(new.bo_table)
            write = self.db.get(write_model, new.wr_id)
            if write:
                # 댓글/게시글 구분
                if write.wr_is_comment:
                    new.subject = "[댓글] " + write.wr_content[:100]
                    new.link = f"/board/{new.bo_table}/{new.wr_parent}#c_{write.wr_id}"
                else:
                    new.subject = write.wr_subject
                    new.link = f"/board/{new.bo_table}/{new.wr_id}"

                # 작성자
                new.name = cut_name(self.request, write.wr_name)
                # 시간설정
                new.datetime = self.format_datetime(write.wr_datetime)

    def delete_board_news(self, bn_ids: list):
        """최신글 삭제"""
        # 새글 정보 조회
        board_news = self.db.scalars(select(BoardNew).where(BoardNew.bn_id.in_(bn_ids))).all()
        for new in board_news:
            board = self.db.get(Board, new.bo_table)
            write_model = dynamic_create_write_table(new.bo_table)
            write = self.db.get(write_model, new.wr_id)
            if write:
                if write.wr_is_comment == 0:
                    # 게시글 삭제
                    # TODO: 게시글 삭제 공용함수 추가
                    self.db.delete(write)

                    # 원글 포인트 삭제
                    if not delete_point(self.request, write.mb_id, board.bo_table, write.wr_id, "쓰기"):
                        insert_point(self.request, write.mb_id, board.bo_write_point * (-1), f"{board.bo_subject} {write.wr_id} 글 삭제")
                else:
                    # 댓글 삭제
                    # TODO: 댓글 삭제 공용함수 추가
                    self.db.delete(write)

                    # 댓글 포인트 삭제
                    if not delete_point(self.request, write.mb_id, board.bo_table, write.wr_id, "댓글"):
                        insert_point(self.request, write.mb_id, board.bo_comment_point * (-1), f"{board.bo_subject} {write.wr_parent}-{write.wr_id} 댓글 삭제")
                # 파일 삭제
                BoardFileManager(board, write.wr_id).delete_board_files()

            # 최신글 삭제
            self.db.delete(new)

            # 최신글 캐시 삭제
            FileCache().delete_prefix(f'latest-{new.bo_table}')

        self.db.commit()

class BoardNewServiceAPI(BoardNewService):
    """
    API 요청에 사용되는 최신글 목록 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self):
        raise HTTPException(status_code=400, detail="검색 결과가 없습니다.")