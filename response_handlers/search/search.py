from typing_extensions import List
from fastapi import Request, HTTPException
from sqlalchemy import select, func

from core.models import Member, Board, Group, GroupMember
from core.database import db_session
from core.exception import AlertException
from lib.service import BaseService
from lib.board_lib import BoardConfig, get_admin_type, write_search_filter, get_list
from lib.common import dynamic_create_write_table


class SearchService(BaseService, BoardConfig):
    """
    게시판 검색 서비스 클래스
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        member: Member,
        gr_id: str = None,
        onetable: str = None,
    ):
        self.request = request
        self.db = db
        self.member = member
        self.mb_id = getattr(member, "mb_id", None)
        self.member_level = getattr(member, "mb_level") if member else 1
        self.admin_type = get_admin_type(request, self.mb_id, group=gr_id)
        self.login_member = self.member
        self.login_member_id = self.mb_id
        self.login_member_admin_type = self.admin_type
        self.login_member_level = self.member_level
        self.gr_id = gr_id
        self.onetable = onetable

    def raise_exception(self):
        raise AlertException(status_code=400, detail="검색 결과가 없습니다.")

    def get_groups(self) -> List[Group]:
        """게시판 그룹 목록 조회"""
        groups = self.db.scalars(
            select(Group)
            .order_by(Group.gr_id)
        ).all()
        return groups

    def get_boards(self) -> List[Board]:
        """게시판 목록 조회"""
        boards_query = (
            select(Board)
            .where(
                Board.bo_use_search == 1,
                Board.bo_list_level <= self.member_level,
            )
            .order_by(Board.bo_order, Board.gr_id, Board.bo_table)
        )
        if self.gr_id:
            boards_query = boards_query.where(Board.gr_id == self.gr_id)
        boards = self.db.scalars(boards_query).all()
        return boards

    def search(self, boards, sfl: str, stx: str, sop: str) -> dict:
        """게시판 검색 데이터"""
        remove_boards = []
        total_search_count = 0
        for board in boards:
            board_config = BoardConfig(self.request, board)
            board.subject = board_config.subject
            # 그룹접근 사용이면서 그룹관리자도 아니고 그룹회원도 아닌 경우 boards에서 제외
            group = board.group
            if group.gr_use_access and not self.request.state.is_super_admin:
                is_group_admin = (group.gr_admin == self.mb_id)
                group_member = self.db.scalar(
                    select(GroupMember).where(
                        GroupMember.gr_id == group.gr_id,
                        GroupMember.mb_id == self.mb_id
                    )
                )
                if not (is_group_admin or group_member):
                    remove_boards.append(board)
                    continue

            # 게시판 별 검색 Query 설정
            write_model = dynamic_create_write_table(board.bo_table)
            query = write_search_filter(self.request, write_model, search_field=sfl, keyword=stx, operator=sop)
            query = board_config.get_list_sort_query(write_model, query)
            board.search_count = self.db.scalar(query.add_columns(func.count()).order_by(None))

            if board.search_count > 0:
                board.writes = self.db.scalars(query.add_columns(write_model).limit(5)).all()
                total_search_count += board.search_count
                for write in board.writes:
                    write = get_list(self.request, write, board_config)
                    if write.wr_is_comment:
                        word = "댓글"
                        parent_write = self.db.get(write_model, write.wr_parent)
                        breakpoint()
                        write.subject = parent_write.wr_subject
                        write.href = f"/board/{board.bo_table}/{parent_write.wr_id}?{self.request.query_params}#c_{write.wr_id}"
                    else:
                        word = "글"
                        write.href = f"/board/{board.bo_table}/{write.wr_id}?{self.request.query_params}"

                    if "secret" in write.wr_option:
                        write.wr_content = f"[비밀{word} 입니다.]"
            else:
                # 검색 결과가 없으면 remove_boards 추가
                remove_boards.append(board)
                continue

        # boards에서 제외된 게시판 제거
        for board in remove_boards:
            boards.remove(board)

        return {"total_search_count": total_search_count, "boards": boards}
    

class SearchServiceAPI(SearchService):
    """
    API 요청에 사용되는 게시판 검색 클래스.
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self):
        raise HTTPException(status_code=400, detail="검색 결과가 없습니다.")