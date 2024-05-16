from datetime import datetime
from typing_extensions import Annotated, List, Union
from fastapi import Request, Path, Form, Depends
from sqlalchemy import select, update

from core.database import db_session
from core.models import WriteBaseModel, BoardNew, BoardGood, Scrap
from core.formclass import WriteForm
from lib.board_lib import FileCache, get_next_num, generate_reply_character
from lib.common import cut_name, dynamic_create_write_table
from lib.dependency.dependencies import (
    validate_captcha as lib_validate_captcha, get_variety_bo_table
)
from lib.template_filters import datetime_format
from api.v1.models.board import WriteModel, WriteTransportation
from service.point_service import PointService
from . import BoardService
from service.board_file_service import BoardFileService

class CreatePostService(BoardService):
    """
    게시글 생성 클래스
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        point_service: Annotated[PointService, Depends()],
        bo_table: Annotated[str, Path(...)],
    ):
        super().__init__(request, db, bo_table)
        self.point_service = point_service

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        point_service: Annotated[PointService, Depends()],
        bo_table: Annotated[str, Path(...)],
    ):
        instance = cls(request, db, point_service, bo_table)
        return instance

    def add_point(self, write, parent_write: WriteBaseModel = None):
        """포인트 추가"""
        if self.member.mb_id:
            point = self.board.bo_comment_point if parent_write else self.board.bo_write_point
            content = f"{self.board.bo_subject} {write.wr_id} 글" + ("답변" if parent_write else "쓰기")
            self.point_service.save_point(self.member.mb_id, point, content,
                                          self.bo_table, write.wr_id, "쓰기")

    def save_write(self, parent_id, data: Union[WriteForm, WriteModel]):
        """게시글을 저장"""
        parent_write = self.get_parent_post(parent_id)
        write = self.write_model(
            wr_num=parent_write.wr_num if parent_write else get_next_num(self.bo_table),
            wr_reply=generate_reply_character(self.board, parent_write) if parent_write else "",
            wr_datetime=datetime.now(),
            mb_id=self.member.mb_id or "",
            wr_ip=self.request.client.host,
            **data.__dict__
        )
        self.db.add(write)
        self.db.commit()

        write.wr_parent = write.wr_id  # 부모아이디 설정
        self.board.bo_count_write = self.board.bo_count_write + 1  # 게시판 글 갯수 1 증가
        self.db.commit()
        return write

    async def validate_captcha(self, recaptcha_response: str):
        """캡차 검증"""
        if self.use_captcha:
            await lib_validate_captcha(self.request, recaptcha_response)


class MoveUpdateService(BoardService):
    """게시글을 이동/복사하는 클래스입니다."""

    def __init__(
        self,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        bo_table: Annotated[str, Depends(get_variety_bo_table)],
        sw: Annotated[str, Form(...)]
    ):
        super().__init__(request, db, bo_table)
        self.sw = sw
        self.act = "이동" if sw == "move" else "복사"
        self.file_service = file_service

    @classmethod
    async def async_init(
        cls,
        request: Request,
        db: db_session,
        file_service: Annotated[BoardFileService, Depends()],
        bo_table: Annotated[str, Depends(get_variety_bo_table)],
        sw: Annotated[str, Form(...)]
    ):
        instance = cls(request, db, file_service, bo_table, sw)
        return instance

    def get_origin_writes(self, wr_ids: str) -> List[WriteBaseModel]:
        """선택된 원본 글들을 가져옵니다."""
        origin_writes = self.db.scalars(
            select(self.write_model)
            .where(self.write_model.wr_id.in_(wr_ids.split(',')))
        ).all()
        return origin_writes

    def move_copy_post(self, target_bo_tables: list, origin_writes: WriteBaseModel):
        """게시글들을 복사/이동 합니다."""
        origin_board = self.board
        origin_bo_table = self.bo_table

        # 게시글 복사/이동 작업 반복
        file_cache = FileCache()
        for target_bo_table in target_bo_tables:
            for origin_write in origin_writes:
                target_write_model = dynamic_create_write_table(target_bo_table)
                target_write = target_write_model()

                # 복사/이동 로그 기록
                log_msg = ""
                if not origin_write.wr_is_comment and self.config.cf_use_copy_log:
                    nick = cut_name(self.request, self.member.mb_nick)
                    log_msg = f"[이 게시물은 {nick}님에 의해 {datetime_format(datetime.now()) } {origin_board.bo_subject}에서 {self.act} 됨]"
                    if "html" in origin_write.wr_option:
                        log_msg = f'<div class="content_{self.sw}">' + log_msg + '</div>'
                    else:
                        log_msg = '\n' + log_msg

                # 게시글 복사
                initial_field = ["wr_id", "wr_parent"]
                for field in origin_write.__table__.columns.keys():
                    if field in initial_field:
                        continue
                    elif field == 'wr_content':
                        target_write.wr_content = origin_write.wr_content + log_msg
                    elif field == 'wr_num':
                        target_write.wr_num = get_next_num(target_bo_table)
                    else:
                        setattr(target_write, field, getattr(origin_write, field))

                if self.sw == WriteTransportation.MOVE.value:
                    target_write.wr_good = 0
                    target_write.wr_nogood = 0
                    target_write.wr_hit = 0
                    target_write.wr_datetime = datetime.now()

                # 게시글 추가
                self.db.add(target_write)
                self.db.commit()
                # 부모아이디 설정
                target_write.wr_parent = target_write.wr_id
                self.db.commit()

                if self.sw == WriteTransportation.MOVE.value:
                    # 최신글 이동
                    self.db.execute(
                        update(BoardNew)
                        .where(BoardNew.bo_table == origin_board.bo_table, BoardNew.wr_id == origin_write.wr_id)
                        .values(bo_table=target_bo_table, wr_id=target_write.wr_id, wr_parent=target_write.wr_id)
                    )
                    # 게시글
                    if not origin_write.wr_is_comment:
                        # 추천데이터 이동
                        self.db.execute(
                            update(BoardGood)
                            .where(BoardGood.bo_table == target_bo_table, BoardGood.wr_id == target_write.wr_id)
                            .values(bo_table=target_bo_table, wr_id=target_write.wr_id)
                        )
                        # 스크랩 이동
                        self.db.execute(
                            update(Scrap)
                            .where(Scrap.bo_table == target_bo_table, Scrap.wr_id == target_write.wr_id)
                            .values(bo_table=target_bo_table, wr_id=target_write.wr_id)
                        )
                    # 기존 데이터 삭제
                    self.db.delete(origin_write)
                    self.db.commit()

                # 파일이 존재할 경우
                if self.file_service.is_exist(origin_board.bo_table, origin_write.wr_id):
                    if self.sw == WriteTransportation.MOVE.value:
                        self.file_service.move_board_files(CreatePostService.FILE_DIRECTORY,
                                                           origin_bo_table, origin_write.wr_id,
                                                           target_bo_table, target_write.wr_id)
                    else:
                        self.file_service.copy_board_files(CreatePostService.FILE_DIRECTORY,
                                                           origin_bo_table, origin_write.wr_id,
                                                           target_bo_table, target_write.wr_id)
            # 최신글 캐시 삭제
            file_cache.delete_prefix(f'latest-{target_bo_table}')

        # 원본 게시판 최신글 캐시 삭제
        file_cache.delete_prefix(f'latest-{origin_bo_table}')
