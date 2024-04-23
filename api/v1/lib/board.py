from typing_extensions import Dict, Annotated
from fastapi import Request, HTTPException, Path, Depends
from sqlalchemy import inspect

from core.models import Board, Member
from core.database import db_session
from lib.dependency.dependencies import common_search_query_params
from lib.board_lib import get_admin_type, generate_reply_character, get_next_num
from lib.member import MemberDetails
from service.board import (
    GroupBoardListService, ListPostService, ReadPostService,
    CreatePostService
)
from api.v1.dependencies.member import get_current_member_optional


class GroupBoardListServiceAPI(GroupBoardListService):
    """
    그룹의 게시판 목록을 얻기 위한 API 클래스
      - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        gr_id: Annotated[str, Path(...)],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, gr_id)
        self.member = MemberDetails(request, member, group=self.group)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class ListPostServiceAPI(ListPostService):
    """
    API 요청에 사용되는 게시글 목록 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(...)],
        search_params: Annotated[Dict, Depends(common_search_query_params)],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, bo_table, search_params)
        self.member = MemberDetails(request, member, board=self.board)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class ReadPostServiceAPI(ReadPostService):
    """
    API 요청에 사용되는 게시글 읽기 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[str, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, bo_table, wr_id)
        self.member = MemberDetails(request, member, board=self.board)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class CreatePostServiceAPI(CreatePostService):
    """
    API 요청에 사용되는 게시글 생성 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, bo_table)
        self.member = MemberDetails(request, member, board=self.board)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
    
    def save_write(self, parent_id, wr_data):
        """게시글을 저장"""
        parent_write = self.get_parent_post(parent_id)
        wr_data_dict = wr_data.model_dump()
        model_fields = inspect(self.write_model).columns.keys()
        filtered_wr_data = {key: value for key, value in wr_data_dict.items() if key in model_fields}
        write = self.write_model(**filtered_wr_data)
        write.wr_num = parent_write.wr_num if parent_write else get_next_num(self.bo_table)
        write.wr_reply = generate_reply_character(self.board, parent_write) if parent_write else ""
        write.mb_id = self.member.mb_id if self.member.mb_id else ''
        write.wr_ip = self.request.client.host
        self.db.add(write)
        self.db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        self.board.bo_count_write = self.board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        self.db.commit()
        return write

def is_possible_level(
    request: Request,
    member_info: Dict,
    board: Board,
    level_type: str,
):
    member_level = member_info["member_level"]
    mb_id = member_info["mb_id"]
    admin_type = get_admin_type(request, mb_id, board=board)
    board_level = getattr(board, level_type)
    if board_level is None:
        raise HTTPException(status_code=404, detail=f"level_type: {level_type} > 존재하지 않는 속성입니다.")
    if admin_type:
        return True
    return member_level >= board_level


def is_possible_point(
    member_info: Dict,
    action_point: int,
):
    member = member_info["member"]
    if not action_point:
        return True
    
    if not member:
        return False

    return member.mb_point + action_point >= 0    