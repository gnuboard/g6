from fastapi import Request, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import asc, desc, func, select

from core.database import db_session
from core.models import Board, Member
from lib.board_lib import write_search_filter, get_list, AlertException, UserTemplates
from lib.template_functions import get_paging
from .base_handler import BoardBase


class ListPostCommon(BoardBase):

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
        search_params: dict
    ):
        super().__init__(request, db, bo_table, board, member)
        self.query = self.get_query(search_params)
        self.prev_spt = None
        self.next_spt = None

    def get_query(self, search_params: dict):
        sca = self.request.query_params.get("sca")
        sfl = search_params.get('sfl')
        stx = search_params.get('stx')
        sst = search_params.get('sst')
        sod = search_params.get('sod')

        # 게시글 목록 조회
        self.query = write_search_filter(self.request, self.write_model, sca, sfl, stx)

        # 정렬
        if sst and hasattr(self.write_model, sst):
            if sod == "desc":
                self.query = self.query.order_by(desc(sst))
            else:
                self.query = self.query.order_by(asc(sst))
        else:
            self.query = self.get_list_sort_query(self.write_model, self.query)

        if sst and hasattr(self.write_model, sst):
            if sod == "desc":
                self.query = self.query.order_by(desc(sst))
            else:
                self.query = self.query.order_by(asc(sst))
        else:
            self.query = self.get_list_sort_query(self.write_model, self.query)

        if (sca or (sfl and stx)):  # 검색일 경우
            search_part = int(self.config.cf_search_part) or 10000
            min_spt = self.db.scalar(
                select(func.coalesce(func.min(self.write_model.wr_num), 0)))
            spt = int(self.request.query_params.get("spt", min_spt))
            self.prev_spt = spt - search_part if spt > min_spt else None
            self.next_spt = spt + search_part if spt + search_part < 0 else None

            # wr_num 컬럼을 기준으로 검색단위를 구분합니다. (wr_num은 음수)
            self.query = self.query.where(self.write_model.wr_num.between(spt, spt + search_part))

            # 검색 내용에 댓글이 잡히는 경우 부모 글을 가져오기 위해 wr_parent를 불러오는 subquery를 이용합니다.
            subquery = select(self.query.add_columns(self.write_model.wr_parent).distinct().order_by(None).subquery().alias("subquery"))
            self.query = select().where(self.write_model.wr_id.in_(subquery))
        else:   # 검색이 아닌 경우
            self.query = self.query.where(self.write_model.wr_is_comment == 0)

        return self.query

    def get_writes(
        self,
        search_params: dict,
    ):
        current_page = search_params.get('current_page')
        page_rows = self.page_rows

        # 페이지 번호에 따른 offset 계산
        offset = (current_page - 1) * page_rows
        # 최종 쿼리 결과를 가져옵니다.
        writes = self.db.scalars(
            self.query.add_columns(self.write_model)
            .offset(offset).limit(page_rows)
        ).all()

        total_count = self.get_total_count()

        # 게시글 정보 수정
        for write in writes:
            write.num = total_count - offset - writes.index(write)
            write = get_list(self.request, write, self)

        return writes
    
    def get_notice_writes(
        self,
        search_params: dict,
    ):
        current_page = search_params.get('current_page')
        sca = self.request.query_params.get("sca")
        notice_writes = []
        if current_page == 1:
            notice_ids = self.get_notice_list()
            notice_query = select(self.write_model).where(self.write_model.wr_id.in_(notice_ids))
            if sca:
                notice_query = notice_query.where(self.write_model.ca_name == sca)
            notice_writes = [get_list(self.request, write, self) for write in self.db.scalars(notice_query).all()]
        return notice_writes

    def get_total_count(self):
        total_count = self.db.scalar(self.query.add_columns(func.count()).order_by(None))
        return total_count


class ListPostTemplate(ListPostCommon):
    
    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
        search_params: dict,
    ):
        super().__init__(request, db, bo_table, board, member, search_params)
        self.set_exception_type(AlertException)
        if not self.is_list_level():
            raise AlertException("목록을 볼 권한이 없습니다.", 403)

        self.template_url: str = f"/board/{self.board.bo_skin}/list_post.html"
        self.context = {
            "request": request,
            "categories": self.categories,
            "board": self.board,
            "board_config": self,
            "notice_writes": self.get_notice_writes(search_params),
            "writes": self.get_writes(search_params),
            "total_count": self.get_total_count(),
            "current_page": search_params['current_page'],
            "paging": get_paging(request, search_params['current_page'], self.get_total_count(), self.page_rows),
            "is_write": self.is_write_level(),
            "table_width": self.get_table_width,
            "gallery_width": self.gallery_width,
            "gallery_height": self.gallery_height,
            "prev_spt": self.prev_spt,
            "next_spt": self.next_spt,
        }

    def response(self):
        return UserTemplates().TemplateResponse(self.template_url, self.context)


class ListPostAPI(ListPostCommon):

    def __init__(
        self, request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member,
        search_params: dict,
    ):
        super().__init__(request, db, bo_table, board, member, search_params)
        self.set_exception_type(HTTPException)

        if not self.admin_type and self.member_level < self.board.bo_list_level:
            raise HTTPException(status_code=403, detail=f"목록을 볼 권한이 없습니다.")

        self.content = {
            "categories": self.categories,
            "board": self.board,
            "writes": self.get_writes(search_params),
            "total_count": self.get_total_count(),
            "current_page": search_params['current_page'],
            "prev_spt": self.prev_spt,
            "next_spt": self.next_spt,
        }

    def response(self):
        return jsonable_encoder(self.content)