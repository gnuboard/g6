"""전체검색 관련 기능을 제공하는 서비스 모듈입니다."""
from typing_extensions import Annotated, List
from fastapi import Depends, Query, Request, HTTPException
from sqlalchemy import select, func

from api.v1.dependencies.member import get_current_member_optional
from core.models import Member, Board, Group, GroupMember
from core.database import db_session
from core.exception import AlertException
from lib.board_lib import BoardConfig, write_search_filter, get_list
from lib.common import dynamic_create_write_table
from lib.member import MemberDetails
from service import BaseService


class SearchService(BaseService):
    """
    게시판 검색 서비스 클래스
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        gr_id: Annotated[str, Query()] = None,
        onetable: Annotated[str, Query()] = None,
    ):
        self.request = request
        self.db = db
        self.gr_id = gr_id
        self.onetable = onetable
        self.group = None
        if gr_id:
            self.group = self.db.get(Group, gr_id)

        self.member = MemberDetails(request, request.state.login_member)
        self.member.admin_type = self.member.get_admin_type(group=self.group)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        gr_id: Annotated[str, Query()] = None,
        onetable: Annotated[str, Query()] = None,
    ):
        instance = cls(request, db, gr_id, onetable)
        return instance

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
                Board.bo_list_level <= self.member.level,
            )
            .order_by(Board.bo_order, Board.gr_id, Board.bo_table)
        )
        if self.gr_id:
            boards_query = boards_query.where(Board.gr_id == self.gr_id)
        boards = self.db.scalars(boards_query).all()
        return boards

    def search(self, boards: List[Board], sfl: str, stx: str, sop: str) -> dict:
        """게시판 검색 데이터"""
        remove_boards = []
        total_search_count = 0
        for board in boards:
            board_config = BoardConfig(self.request, board)
            board.subject = board_config.subject
            # 그룹접근 사용이면서 그룹관리자도 아니고 그룹회원도 아닌 경우 boards에서 제외
            group = board.group
            if group.gr_use_access and not self.member.is_super_admin():
                is_group_admin = group.gr_admin == self.member.mb_id
                group_member = self.db.scalar(
                    select(GroupMember).where(
                        GroupMember.gr_id == group.gr_id,
                        GroupMember.mb_id == self.member.mb_id
                    )
                )
                if not (is_group_admin or group_member):
                    remove_boards.append(board)
                    continue

            # 게시판 별 검색 Query 설정
            write_model = dynamic_create_write_table(board.bo_table)
            query = write_search_filter(write_model, search_field=sfl,
                                        keyword=stx, operator=sop)
            query = board_config.get_list_sort_query(write_model, query)
            board.search_count = self.db.scalar(query.add_columns(func.count()).order_by(None))

            if board.search_count > 0:
                board.writes = self.db.scalars(query.add_columns(write_model).limit(5)).all()
                total_search_count += board.search_count
                for write in board.writes:
                    write = get_list(self.request, self.db, write, board_config)
                    if write.wr_is_comment:
                        word = "댓글"
                        parent_write = self.db.get(write_model, write.wr_parent)
                        if parent_write:
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
    def __init__(
        self,
        request: Request,
        db: db_session,
        member: Annotated[Member, Depends(get_current_member_optional)],
        gr_id: str = None,
        onetable: str = None,
    ):
        super().__init__(request, db, gr_id, onetable)
        self.member = MemberDetails(request, member)
        self.member.admin_type = self.member.get_admin_type(group=self.group)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        member: Annotated[Member, Depends(get_current_member_optional)],
        gr_id: str = None,
        onetable: str = None,
    ):
        instance = cls(request, db, member, gr_id, onetable)
        return instance

    def raise_exception(self):
        raise HTTPException(status_code=400, detail="검색 결과가 없습니다.")
