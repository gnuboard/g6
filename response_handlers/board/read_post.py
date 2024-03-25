from typing_extensions import Annotated

from fastapi import Request, HTTPException, Depends, Path
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, select, exists

from core.database import db_session
from core.models import Board, BoardGood, WriteBaseModel, Scrap, Member
from lib.board_lib import (
    UserTemplates, AlertException, BoardFileManager, get_admin_type,
    insert_point, is_owner, cut_name
)
from lib.dependencies import (
    check_login_member,
    get_board as get_board_template,
    get_write as get_write_template
)
from lib.template_filters import number_format
from api.v1.models.board import ResponseWriteModel
from api.v1.dependencies.board import (
    get_current_member,
    get_write as get_write_api,
    get_board as get_board_api,
)
from .base_handler import BoardBase


class ReadPostCommon(BoardBase):
    """
    게시글 읽기 공통 클래스
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
        member: Member
    ):
        super().__init__(request, db, bo_table, board, member)
        self.wr_id = wr_id
        self.board.subject = self.subject

        # 게시글 정보 설정
        write.ip = self.get_display_ip(write.wr_ip)
        write.name = cut_name(request, write.wr_name)
        self.write = write

        self.comments = self.get_comments()
        # 파일정보 조회
        self.images, self.normal_files = BoardFileManager(board, wr_id).get_board_files_by_type(request)
        self.links = self.get_links()

    def block_read_comment(self):
        """댓글은 개별조회 할 수 없도록 예외처리"""
        if self.write.wr_is_comment:
            raise self.ClassException(detail=f"{self.write.wr_id} : 존재하지 않는 게시글입니다.", status_code=404)

    def validate_read_level(self):
        """읽기 권한 검증"""
        if not self.is_read_level():
            raise self.ClassException(detail="글을 읽을 권한이 없습니다.", status_code=403)

    def validate_secret(self):
        """비밀글 검증"""
        block_conditions = [
            "secret" in self.write.wr_option,
            not self.admin_type,
            not is_owner(self.write, self.mb_id),
        ]

        if isinstance(self, ReadPostTemplate):
            session_secret_name = f"ss_secret_{self.bo_table}_{self.wr_id}"
            block_conditions.append(not self.request.session.get(session_secret_name))
    
        if not all(block_conditions):
            return

        owner = False
        if self.write.wr_reply and self.mb_id:
            parent_write = self.db.scalar(
                select(self.write_model).filter_by(
                    wr_num=self.write.wr_num,
                    wr_reply="",
                    wr_is_comment=0
                )
            )
            if parent_write.mb_id == self.mb_id:
                owner = True
                if isinstance(self, ReadPostTemplate):
                    self.request.session[session_secret_name] = True
        if not owner:
            raise self.ClassException(detail="비밀글 입니다.", status_code=403)

    def validate_repeat(self):
        """한번 읽은 게시글은 세션만료까지 조회수, 포인트 처리를 하지 않는다."""
        conditions = [self.mb_id != self.write.mb_id]
        if isinstance(self, ReadPostTemplate):
            conditions.append(not self.request.session.get(self.session_name))

        if not all(conditions):
            return

        # 포인트 검사
        if self.config.cf_use_point:
            read_point = self.board.bo_read_point
            if not self.is_read_point(self.write):
                point = number_format(abs(read_point))
                message = f"게시글 읽기에 필요한 포인트({point})가 부족합니다."
                if not self.member:
                    message += f" 로그인 후 다시 시도해주세요."
                raise self.ClassException(detail=message, status_code=403)
            else:
                insert_point(self.request, self.mb_id, read_point, f"{self.board.bo_subject} {self.write.wr_id} 글읽기", self.board.bo_table, self.write.wr_id, "읽기")
        
        if isinstance(self, ReadPostTemplate):
            self.request.session[self.session_name] = True
        
        # 조회수 증가
        self.write.wr_hit += 1
        self.db.commit()

    def check_scrap(self):
        """스크랩 여부 확인"""
        if not self.member:
            return
        
        exists_scrap = self.db.scalar(
            exists(Scrap)
            .where(
                Scrap.mb_id == self.member.mb_id,
                Scrap.bo_table == self.bo_table,
                Scrap.wr_id == self.wr_id
            ).select()
        )

        if exists_scrap:
            self.write.is_scrap = True

    def check_is_good(self):
        """추천/비추천 확인"""
        if not self.member:
            return

        good_data = self.db.scalar(
            select(BoardGood)
            .filter_by(bo_table=self.bo_table, wr_id=self.wr_id, mb_id=self.member.mb_id)
        )
        if good_data:
            setattr(self.write, f"is_{good_data.bg_flag}", True)

    def get_links(self):
        """링크 목록 조회""""
        links = []
        for i in range(1, 3):
            url = getattr(self.write, f"wr_link{i}")
            hit = getattr(self.write, f"wr_link{i}_hit")
            if url:
                links.append({"no": i, "url": url, "hit": hit})

    def get_comments(self):
        """댓글 목록 조회"""
        comments = self.db.scalars(
            select(self.write_model).filter_by(
                wr_parent=self.wr_id,
                wr_is_comment=1
            ).order_by(self.write_model.wr_comment, self.write_model.wr_comment_reply)
        ).all()

        for comment in comments:
            comment.name = cut_name(self.request, comment.wr_name)
            comment.ip = self.get_display_ip(comment.wr_ip)
            comment.is_reply = len(comment.wr_comment_reply) < 5 and self.board.bo_comment_level <= self.member_level
            comment.is_edit = bool(self.admin_type) or (self.member and comment.mb_id == self.member.mb_id)
            comment.is_del = bool(self.admin_type) or (self.member and comment.mb_id == self.member.mb_id) or not comment.mb_id
            comment.is_secret = "secret" in comment.wr_option

            # 비밀댓글 처리
            session_secret_comment_name = f"ss_secret_comment_{self.bo_table}_{comment.wr_id}"
            parent_write = self.db.get(self.write_model, comment.wr_parent)
            if (comment.is_secret
                    and not self.admin_type
                    and not is_owner(comment, self.mb_id)
                    and not is_owner(parent_write, self.mb_id)
                    and not self.request.session.get(session_secret_comment_name)):
                comment.is_secret_content = True
                comment.save_content = "비밀글 입니다."
            else:
                comment.is_secret_content = False
                comment.save_content = comment.wr_content

        return comments


class ReadPostTemplate(ReadPostCommon):
    """
    Template용 게시글 읽기 클래스
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        board: Annotated[Board, Depends(get_board_template)],
        write: Annotated[WriteBaseModel, Depends(get_write_template)],
        member: Annotated[Member, Depends(check_login_member)],
        bo_table: str = Path(...),
        wr_id: int = Path(...),
    ):
        super().__init__(request, db, bo_table, board, wr_id, write, member)
        self.template_url: str = f"/board/{self.board.bo_skin}/read_post.html"
        self.admin_type = get_admin_type(request, self.mb_id, board=board)
        self.session_name = f"ss_view_{bo_table}_{wr_id}"
        self.request.state.editor = self.select_editor
        self.prev, self.next = self.get_prev_next()
        self.set_exception_type(AlertException)

        # TODO: 전체목록보이기 사용 => 게시글 목록 부분을 분리해야함
        self.write_list = None
        # if member_level >= board.bo_list_level and board.bo_use_list_view:
        #     write_list = list_post(request, db, bo_table, search_params={
        #         "current_page": 1,
        #         "sca": request.query_params.get("sca"),
        #         "sfl": request.query_params.get("sfl"),
        #         "stx": request.query_params.get("stx"),
        #         "sst": request.query_params.get("sst"),
        #         "sod": request.query_params.get("sod"),
        #     }).body.decode("utf-8")

        self.context = {
            "request": self.request,
            "board": self.board,
            "write": self.write,
            "write_list": self.write_list,
            "prev": self.prev,
            "next": self.next,
            "images": self.images,
            "files": self.images + self.normal_files,
            "links": self.links,
            "comments": self.comments,
            "is_write": self.is_write_level(),
            "is_reply": self.is_reply_level(),
            "is_comment_write": self.is_comment_level(),
        }

    def get_prev_next(self):
        """이전글 다음글 조회"""
        prev = None
        next = None
        sca = self.request.query_params.get("sca")
        sfl = self.request.query_params.get("sfl")
        stx = self.request.query_params.get("stx")
        if not self.board.bo_use_list_view:
            query = select(self.write_model).where(self.write_model.wr_is_comment == 0)
            if sca:
                query = query.where(self.write_model.ca_name == sca)
            if sfl and stx and hasattr(self.write_model, sfl):
                query = query.where(getattr(self.write_model, sfl).like(f"%{stx}%"))
            # 같은 wr_num 내에서 이전글 조회
            prev = self.db.scalar(
                query.where(
                    self.write_model.wr_num == self.write.wr_num,
                    self.write_model.wr_reply < self.write.wr_reply,
                ).order_by(desc(self.write_model.wr_reply))
            )
            if not prev:
                prev = self.db.scalar(
                    query.where(self.write_model.wr_num < self.write.wr_num)
                    .order_by(desc(self.write_model.wr_num))
                )
            # 같은 wr_num 내에서 다음글 조회
            next = self.db.scalar(
                query.where(
                    self.write_model.wr_num == self.write.wr_num,
                    self.write_model.wr_reply > self.write.wr_reply,
                ).order_by(asc(self.write_model.wr_reply))
            )
            if not next:
                next = self.db.scalar(
                    query.where(self.write_model.wr_num > self.write.wr_num)
                    .order_by(asc(self.write_model.wr_num))
                )
        return prev, next

    def response(self):
        """최종 응답 처리"""
        self.block_read_comment()
        self.validate_read_level()
        self.validate_secret()
        self.validate_repeat()
        self.check_scrap()
        self.check_is_good()
        self.db.commit()
        return UserTemplates().TemplateResponse(self.template_url, self.context)
    

class ReadPostAPI(ReadPostCommon):
    """
    API용 게시글 읽기 클래스
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        write: Annotated[WriteBaseModel, Depends(get_write_api)],
        board: Annotated[Board, Depends(get_board_api)],
        member: Annotated[Member, Depends(get_current_member)],
        bo_table: str = Path(...),
        wr_id: str = Path(...),
    ):
        super().__init__(request, db, bo_table, board, wr_id, write, member)
        
        self.admin_type = get_admin_type(request, self.mb_id, board=board)
        self.comments = self.get_comments()

        content = jsonable_encoder(self.write)
        additional_content = jsonable_encoder({
            "images": self.images,
            "normal_files": self.normal_files,
            "links": self.links,
            "comments": self.comments,
        })
        content.update(additional_content)
        self.content = content
        self.set_exception_type(HTTPException)

    def response(self):
        """최종 응답 처리"""
        content = ResponseWriteModel.model_validate(self.content)
        self.block_read_comment()
        self.validate_read_level()
        self.validate_secret()
        self.validate_repeat()
        self.check_scrap()
        self.check_is_good()
        self.db.commit()
        return content