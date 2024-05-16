from typing_extensions import Dict, Annotated
from fastapi import Request, HTTPException, Path, Depends
from sqlalchemy import inspect

from api.v1.service.point import PointServiceAPI
from api.v1.dependencies.member import get_current_member_optional, get_current_member
from api.v1.models.board import WriteTransportationRequest
from core.models import Board, Member
from core.database import db_session
from lib.dependency.dependencies import common_search_query_params
from lib.board_lib import generate_reply_character, get_next_num
from lib.template_filters import number_format
from lib.member import get_admin_type, MemberDetails
from lib.pbkdf2 import validate_password
from service.board import (
    GroupBoardListService, ListPostService, ReadPostService,
    CreatePostService, UpdatePostService, DownloadFileService,
    DeletePostService, CommentService, DeleteCommentService,
    MoveUpdateService, ListDeleteService
)
from service.board_file_service import BoardFileService


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

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        gr_id: Annotated[str, Path(...)],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, gr_id, member)
        return instance

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

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(...)],
        search_params: Annotated[Dict, Depends(common_search_query_params)],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, bo_table, search_params, member)
        return instance

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
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, file_service, point_service, bo_table, wr_id)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, file_service, point_service, bo_table, wr_id, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)

    def validate_read_wr_password(self, wr_password: str, hashed_wr_password: str):
        """게시글 비밀번호 검사"""
        if not validate_password(wr_password, hashed_wr_password):
            self.raise_exception(403, "비밀번호가 일치하지 않습니다.")

class CreatePostServiceAPI(CreatePostService):
    """
    API 요청에 사용되는 게시글 생성 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, point_service, bo_table)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, point_service, bo_table, member)
        return instance

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

class UpdatePostServiceAPI(UpdatePostService):
    """
    API 요청에 사용되는 게시글 수정 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, bo_table, wr_id)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, bo_table, wr_id, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class DownloadFileServiceAPI(DownloadFileService):
    """
    API용 파일 다운로드 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        bf_no: Annotated[int, Path(..., title="파일 순번", description="파일 순번")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, file_service, point_service, bo_table, wr_id, bf_no)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        bf_no: Annotated[int, Path(..., title="파일 순번", description="파일 순번")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, file_service, point_service, bo_table, wr_id, bf_no, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)

    def validate_point(self, board_file):
        """다운로드 포인트 검사"""
        if not self.config.cf_use_point:
            return

        download_point = self.board.bo_download_point
        if self.is_download_point(self.write):
            self.point_service.save_point(
                self.member.mb_id, download_point,
                f"{self.board.bo_subject} {self.wr_id} 파일 다운로드", self.bo_table,
                self.wr_id, "다운로드")
            # 다운로드 횟수 증가
            self.file_service.update_download_count(board_file)
            return
        
        point = number_format(abs(download_point))
        message = f"파일 다운로드에 필요한 포인트({point})가 부족합니다."
        self.raise_exception(detail=message, status_code=403)


class DeletePostServiceAPI(DeletePostService):
    """
    API 요청에 사용되는 게시글 삭제 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        super().__init__(request, db, file_service, point_service, bo_table, wr_id)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="글 아이디", description="글 아이디")],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        instance = cls(request, db, file_service, point_service, bo_table, wr_id, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class CommentServiceAPI(CommentService):
    """
    댓글 관리를 위한 API 클래스
      - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="부모글 아이디", description="부모글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, point_service, bo_table, wr_id)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        wr_id: Annotated[int, Path(..., title="부모글 아이디", description="부모글 아이디")],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        instance = cls(request, db, point_service, bo_table, wr_id, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class DeleteCommentServiceAPI(DeleteCommentService):
    """
    댓글 삭제 처리 API 클래스, 
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        comment_id: Annotated[int, Path(..., title="댓글 아이디", description="댓글 아이디")],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        super().__init__(request, db, file_service, point_service, bo_table, comment_id)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        comment_id: Annotated[int, Path(..., title="댓글 아이디", description="댓글 아이디")],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        instance = cls(request, db, file_service, point_service, bo_table, comment_id, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code, detail)


class MoveUpdateServiceAPI(MoveUpdateService):
    """
    게시글을 이동/복사하는 API 클래스입니다.
    상위클래스의 예외 처리 함수를 오버라이딩 하여 사용합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        sw: Annotated[WriteTransportationRequest, Depends()],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        super().__init__(request, db, file_service, bo_table, sw.sw.value)
        self.member = MemberDetails(request, member, board=self.board)

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        sw: Annotated[WriteTransportationRequest, Depends()],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        instance = cls(request, db, file_service, bo_table, sw, member)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class ListDeleteServiceAPI(ListDeleteService):
    """
    API 요청에 사용되는 게시글 목록 삭제 클래스
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
        self,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        point_service: Annotated[PointServiceAPI, Depends()],
        bo_table: Annotated[str, Path(..., title="게시판 테이블명", description="게시판 테이블명")],
        member: Annotated[Member, Depends(get_current_member)],
    ):
        super().__init__(request, db, file_service, point_service, bo_table)
        self.member = MemberDetails(request, member, board=self.board)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code, detail)


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
