"""게시판/게시글 함수 모음"""
import os
import re
from datetime import datetime, timedelta

import bleach
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, asc, desc, func, insert, or_, select
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm import Session

from core.database import DBConnect
from core.exception import AlertException
from core.models import Board, BoardNew, Member, WriteBaseModel
from core.template import TemplateService, UserTemplates
from lib.common import (
    FileCache, StringEncrypt, cut_name, dynamic_create_write_table, get_admin_email,
    get_admin_email_name, get_editor_image, thumbnail
)
from lib.mail import mailer
from lib.member import MemberDetails
from service.board_file_service import BoardFileService as FileService


class BoardConfig():
    """게시판 설정 정보를 담는 클래스."""

    def __init__(self, request: Request, board: Board) -> None:
        self.board = board
        self.config = request.state.config
        self.is_mobile = request.state.is_mobile
        self.request = request

        self.member = MemberDetails(request, request.state.login_member)
        self.member.admin_type = self.member.get_admin_type(board=board)

    @property
    def gallery_width(self) -> int:
        """갤러리 목록 이미지 가로 크기를 반환.

        Returns:
            int: 갤러리 이미지 가로 크기.
        """
        return (self.board.bo_mobile_gallery_width if self.is_mobile else self.board.bo_gallery_width) or 200

    @property
    def gallery_height(self) -> int:
        """갤러리 목록 이미지 세로 크기를 반환.

        Returns:
            int: 갤러리 이미지 세로 크기.
        """
        return (self.board.bo_mobile_gallery_height if self.is_mobile else self.board.bo_gallery_height) or 150

    @property
    def image_width(self) -> int:
        """게시판 상세페이지에서 보여줄 이미지 가로 크기를 반환.

        Returns:
            int: 이미지 가로 크기.
        """
        return self.board.bo_image_width or None

    @property
    def page_rows(self) -> int:
        """게시판 페이지당 출력할 행의 수를 반환.

        Returns:
            int: 게시판 페이지당 출력할 행의 수.
        """
        # 모바일 여부 확인
        bo_page_rows = self.board.bo_mobile_page_rows if self.is_mobile else self.board.bo_page_rows
        page_rows = self.config.cf_mobile_page_rows if self.is_mobile else self.config.cf_page_rows

        return bo_page_rows if bo_page_rows != 0 else page_rows

    @property
    def table_width(self) -> int:
        """게시판 테이블의 가로 크기를 반환.

        Returns:
            int: 게시판 테이블의 가로 크기.
        """
        return self.board.bo_table_width or 100

    @property
    def get_table_width(self) -> str:
        """게시판 테이블의 가로 크기를 단위와 함께 반환.

        Returns:
            str: 게시판 테이블의 가로 크기.
        """
        unit = "px" if self.table_width > 100 else "%"

        return f"{self.table_width}{unit}"

    @property
    def select_editor(self) -> str:
        """게시판에 사용할 에디터를 반환.

        Returns:
            str: 게시판에 사용할 에디터.
        """
        if not self.board.bo_use_dhtml_editor or not self.config.cf_editor:
            return "textarea"

        return self.board.bo_select_editor or self.config.cf_editor

    @property
    def subject(self) -> str:
        """게시판 제목을 반환.

        Returns:
            str: 게시판 제목.
        """
        if self.request.state.is_mobile and self.board.bo_mobile_subject:
            return self.board.bo_mobile_subject
        else:
            return self.board.bo_subject

    @property
    def use_captcha(self) -> bool:
        """게시판에 캡차 사용 여부를 반환.

        Returns:
            bool: 게시판에 캡차 사용 여부.
        """
        if self.member.admin_type:
            return False

        if not self.member or self.board.bo_use_captcha:
            return True

        return False

    @property
    def use_email(self) -> bool:
        """게시판에 이메일 사용 여부를 반환.

        Returns:
            bool: 게시판에 이메일 사용 여부.
        """
        return self.config.cf_email_use and self.board.bo_use_email

    @property
    def write_min(self) -> int:
        """게시글 등록 최소 글수 제한"""
        return self._get_write_text_limit(self.board.bo_write_min)

    @property
    def write_max(self) -> int:
        """게시글 등록 최대 글수 제한"""
        return self._get_write_text_limit(self.board.bo_write_max)

    def cut_write_subject(self, subject, cut_length: int = 0) -> str:
        """주어진 cut_length에 기반하여 subject 문자열을 자르고 필요한 경우 "..."을 추가합니다.

        Args:
            - subject: 자를 대상인 주제 문자열.
            - cut_length: subject 문자열의 최대 길이. Default: 0

        Returns:
            - str : 수정된 subject 문자열.
        """
        cut_length = cut_length or (self.board.bo_mobile_subject_len if self.is_mobile else self.board.bo_subject_len)

        if not cut_length:
            return subject

        return subject[:cut_length] + "..." if len(subject) > cut_length else subject

    def get_category_list(self) -> list:
        """게시판 카테고리 목록을 반환.

        Returns:
            list: 게시판 카테고리 목록.
        """
        if (not self.board.bo_use_category
                or self.board.bo_category_list == ""):
            return []

        return self.board.bo_category_list.split("|")

    def get_display_ip(self, ip: str) -> str:
        """IP 주소를 표시형식으로 변환
        Args:
            ip (str): IP 주소
        """
        if self.member.admin_type:
            return ip

        if self.board.bo_use_ip_view:
            return re.sub(r"([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)", "\\1.#.#.\\4", ip)
        else:
            return ""

    def get_member_signature(self, mb_id: str = None) -> str:
        """게시판에서 서명보이기를 사용 중이면 회원의 서명을 반환한다.

        Args:
            mb_id (str): 회원 아이디. Defaults to None.

        Returns:
            str: 회원 서명
        """
        try:
            db = DBConnect().sessionLocal()

            if self.board.bo_use_signature and mb_id:
                member = db.scalar(
                    select(Member).filter(Member.mb_id == mb_id))

                return getattr(member, "mb_signature", "")
            else:
                return ""
        finally:
            db.close()

    def get_notice_list(self) -> list:
        """게시판 공지글 번호 목록을 반환.

        Returns:
            list: 게시판 공지글 번호 목록.
        """
        if not self.board.bo_notice:
            return []
        return self.board.bo_notice.split(",")

    def get_list_sort_query(self, model: WriteBaseModel, query: Select) -> Select:
        """게시글 목록의 정렬을 포함한 query를 반환.

        Args:
            query (Select): 게시글 목록 쿼리

        Returns:
            Select: 게시글 목록 쿼리
        """
        if self.board.bo_sort_field:
            sort_fields = self.board.bo_sort_field.split(",")
            for field in sort_fields:
                field_parts = field.strip().split(" ")
                sort_field = getattr(model, field_parts[0])
                if not sort_field:
                    continue
                sort_order = asc(sort_field) if len(field_parts) == 1 or field_parts[1].lower() == "asc" else desc(sort_field)
                query = query.order_by(sort_order)
        else:
            query = query.order_by(model.wr_num, model.wr_reply)

        return query

    def is_list_level(self) -> bool:
        """게시글 목록을 볼 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_list_level)

    def is_read_level(self) -> bool:
        """게시글을 읽을 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_read_level)

    def is_write_level(self) -> bool:
        """게시글을 작성 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_write_level)

    def is_reply_level(self) -> bool:
        """게시글을 답변 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_reply_level)

    def is_comment_level(self) -> bool:
        """댓글을 작성 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_comment_level)

    def is_link_level(self) -> bool:
        """게시글 작성 시, 링크를 추가 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_link_level)

    def is_upload_level(self) -> bool:
        """게시글 작성 시, 파일을 업로드 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_upload_level)

    def is_download_level(self) -> bool:
        """게시글의 첨부파일을 다운로드 할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_download_level)

    def is_html_level(self) -> bool:
        """게시글 작성 시, HTML을 추가할 수 있는 권한을 확인한다."""
        return self._can_action_by_level(self.board.bo_html_level)

    def is_icon_hot(self, hit: int) -> bool:
        """인기글 아이콘 출력 여부를 반환.

        Args:
            hit (int): 조회수.

        Returns:
            bool: 인기글 아이콘 출력 여부.
        """
        return hit >= self.board.bo_hot if self.board.bo_hot > 0 else False

    def is_icon_new(self, reg_date: datetime) -> bool:
        """새글 아이콘 출력 여부를 반환.

        Args:
            reg_date (str): 등록일.

        Returns:
            bool: 새글 아이콘 출력 여부.
        """
        result = False
        if self.board.bo_new > 0:
            result = reg_date > (datetime.now() - timedelta(hours=int(self.board.bo_new)))

        return result

    def is_board_notice(self, wr_id: int) -> bool:
        """게시글이 공지글인지 확인한다.

        Args:
            wr_id (int): 게시글 아이디

        Returns:
            bool: 공지글 여부
        """
        return str(wr_id) in self.board.bo_notice.split(",")

    def is_read_point(self, write: WriteBaseModel) -> bool:
        """글 읽기 포인트 체크"""
        return self._can_action_by_point(self.board.bo_read_point, write)

    def is_write_point(self) -> bool:
        """글 쓰기 포인트 체크"""
        return self._can_action_by_point(self.board.bo_write_point)

    def is_comment_point(self) -> bool:
        """댓글 쓰기 포인트 체크"""
        return self._can_action_by_point(self.board.bo_comment_point)

    def is_download_point(self, write: WriteBaseModel) -> bool:
        """다운로드 포인트 체크"""
        return self._can_action_by_point(self.board.bo_download_point, write)

    def is_modify_by_comment(self, wr_id: int) -> bool:
        """댓글 수에 따라 게시글 수정이 가능한지"""
        return self._can_action_by_comment_count(wr_id, self.board.bo_count_modify)

    def is_delete_by_comment(self, wr_id: int) -> bool:
        """댓글 수에 따라 게시글 삭제가 가능한지"""
        return self._can_action_by_comment_count(wr_id, self.board.bo_count_delete)

    def set_board_notice(self, wr_id: int, insert: bool = False) -> str:
        """게시판의 공지글 정보(`,`구분자 문자열)를 수정한다.

        Args:
            wr_id (int): _description_
            insert (bool, optional): _description_. Defaults to False.

        Returns:
            str: _description_
        """
        notice_ids = self.board.bo_notice.split(",") if self.board.bo_notice else []
        exist = self.is_board_notice(wr_id)

        if insert and not exist:
            notice_ids.append(str(wr_id))
        elif not insert and exist:
            notice_ids.remove(str(wr_id))

        return ",".join(map(str, notice_ids))

    def set_wr_name(self, member: Member = None, default_name: str = None) -> str:
        """실명사용 여부를 확인 후 실명이면 이름을, 아니면 닉네임을 반환한다.

        Args:
            board (Board): 게시판 object
            member (Member): 회원 object 

        Returns:
            str: 이름 또는 닉네임
        """
        if member:
            if self.board.bo_use_name:
                return member.mb_name
            return member.mb_nick
        elif default_name:
            return default_name
        else:
            raise AlertException("로그인 세션 만료, 비회원 글쓰기시 작성자 이름 미기재 등의 비정상적인 접근입니다.", 400)

    def _can_action_by_level(self, level: int) -> bool:
        """회원 레벨에 따라 행동 가능 여부를 판단한다.

        Args:
            level (int): 권한 레벨

        Returns:
            bool: 행동 가능 여부
        """
        if self.member.admin_type:
            return True
        return level <= self.member.mb_level

    def _can_action_by_comment_count(self, wr_id: int, limit: int) -> bool:
        """댓글 수에 따라 행동 가능 여부를 판단한다.

        Args:
            request (Request): Request 객체
            wr_id (int): 게시글 아이디
            limit (int): 제한할 댓글 수

        Returns:
            bool: 수정 가능 여부
        """
        if self.member.admin_type:
            return True

        with DBConnect().sessionLocal() as db:
            write_model = dynamic_create_write_table(self.board.bo_table)
            comment_count = db.scalar(
                select(func.count())
                .select_from(write_model)
                .where(
                    write_model.wr_parent == wr_id,
                    write_model.wr_is_comment == 1
                )
            )

        if limit and limit <= comment_count:
            return False
        return True

    def _can_action_by_point(self, point: int, write: WriteBaseModel = None) -> bool:
        """포인트에 따라 행동 가능 여부를 판단한다.

        Args:
            point (int): 증감할 포인트

        Returns:
            bool: 행동 가능 여부
        """
        member_point = getattr(self.member, "mb_point", 0)

        # 관리자 or 포인트가 0 이상이면 통과
        if self.member.admin_type or point >= 0:
            return True
        # 게시글 작성자 or 게시글 작성자 IP와 현재 접속 IP가 같으면 통과
        if write:
            if (is_owner(write, self.member.mb_id)
                or (not self.member.mb_id
                    and self.board.bo_read_level == 1
                    and write.wr_ip == self.request.client.host)):
                return True

        return (member_point + point) >= 0

    def _get_write_text_limit(self, limit: int) -> int:
        """게시글/댓글 작성 제한 글 수를 반환.

        Args:
            limit (int): 게시글 작성 제한 글 수.

        Returns:
            int: 게시글 작성 제한 글 수.
        """
        if self.member.admin_type or self.board.bo_use_dhtml_editor:
            return 0
        return limit


def write_search_filter(
        model: WriteBaseModel,
        category: str = None,
        search_field: str = None,
        keyword: str = None,
        operator: str = "or") -> Select:
    """게시판 검색 필터를 적용합니다.
    - 그누보드5의 get_sql_search와 동일한 기능을 합니다.

    Args:
        model (WriteBaseModel): 검색할 모델(게시글).
        category (str, optional): 검색할 분류. Defaults to None.
        fields (str, optional): 검색할 필드. Defaults to None.
        keyword (str, optional): 검색할 문자열. Defaults to None.
        operator (str, optional): 검색 조건. Defaults to None.

    Returns:
        Select: 필터가 적용된 쿼리.
    """
    with DBConnect().sessionLocal() as db:
        fields = []
        is_comment = False

        query = select()
        # 분류
        if category:
            query = query.where(model.ca_name == category)

        # 검색 필드 및 단어 설정
        # 검색어를 단어로 분리하여 operator에 따라 필터를 생성
        word_filters = []
        words = keyword.split(" ")
        if search_field:
            # search_field는 {필드명},{코멘트여부} 형식으로 전달됨 (0:댓글, 1:게시글)
            tmp = search_field.split(",")
            fields = tmp[0].split("||")
            is_comment = (tmp[1] == "0") if len(tmp) > 1 else False

            # 패스워드 필드 제거
            if "wr_password" in fields:
                fields.remove("wr_password")

            # 필드검색 필터 생성 (or 조건)
            for word in words:
                if not word.strip():
                    continue
                word_filters.append(or_(
                    *[getattr(model, field).like(f"%{word}%") for field in fields if hasattr(model, field)]))

        # 분리된 단어 별 검색필터에 or 또는 and를 적용
        if operator == "and":
            query = query.where(and_(*word_filters))
        else:
            query = query.where(or_(*word_filters))

        # 댓글 검색
        if is_comment:
            query = query.where(model.wr_is_comment == 1)
            # 원글만 조회해야하므로, wr_parent 목록을 가져와서 in조건으로 재필터링
            parents = db.scalars(query.add_columns(model)).all()
            query = select().where(model.wr_id.in_([row.wr_parent for row in parents]))

        return query


def get_next_num(bo_table: str) -> int:
    """
    게시판의 다음글 번호를 얻는다.
    """
    try:
        db = DBConnect().sessionLocal()

        write_model = dynamic_create_write_table(bo_table)
        min_wr_num = db.scalar(select(func.coalesce(func.min(write_model.wr_num), 0)))

        return min_wr_num - 1
    finally:
        db.close()


def get_list(request: Request, db: Session, write: WriteBaseModel, board_config: BoardConfig, subject_len: int = 0):
    """게시글 목록의 출력에 필요한 정보를 추가합니다.
    - 그누보드5의 get_list와 동일한 기능을 합니다.

    Args:
        request (Request): FastAPI Request 객체.
        write (WriteBaseModel): 게시글 객체.
        board (Board): 게시판 객체.
        subject_len (int, optional): 게시글 제목 길이. Defaults to 0.

    Returns:
        WriteBaseModel: 게시글 목록.
    """
    file_service = FileService(request, db)
    write.subject = board_config.cut_write_subject(write.wr_subject, subject_len)
    write.name = cut_name(request, write.wr_name)
    write.email = StringEncrypt().encrypt(write.wr_email)
    write.datetime = write.wr_datetime.strftime("%y-%m-%d")

    write.is_notice = board_config.is_board_notice(write.wr_id)
    write.icon_secret = "secret" in write.wr_option
    write.icon_hot = board_config.is_icon_hot(write.wr_hit)
    write.icon_new = board_config.is_icon_new(write.wr_datetime)
    write.icon_file = file_service.is_exist(board_config.board.bo_table, write.wr_id)
    write.icon_link = write.wr_link1 or write.wr_link2
    write.icon_reply = write.wr_reply

    return write


# FIXME: 대댓글이 있는 상태에서 bo_reply_order를 바꾸면 입력하지 못하는 오류
# ex) 처음에는 정방향 A B C가 입력되고 역방향으로 바꾸면 last_reply_char이 A가 된다(Min).
# 역방향의 char_end는 A이고 A - 1은 예외처리하고 있음으로 대댓글이 입력되지 않는다
def generate_reply_character(board: Board, write):
    """ 대댓글 단계 문자열 생성 

    Args:
        board (Board): 게시판 object
        write (Write): 댓글/답글을 달 게시글 object

    Raises:
        AlertException: Z를 넘어가는 문자열 예외처리

    Returns:
        str: A~Z의 연속된 문자열(Ex: A, B, AA, AB, ABA ..)
    """
    db = DBConnect().sessionLocal()
    write_model = dynamic_create_write_table(board.bo_table)

    # 마지막 문자열 1개 자르기
    if not write.wr_is_comment:
        origin_reply = write.wr_reply
        query = (
            select(func.substr(write_model.wr_reply, -1).label("reply"))
            .where(
                write_model.wr_num == write.wr_num,
                func.char_length(write_model.wr_reply) == (len(origin_reply) + 1)
            )
        )
        if origin_reply:
            query = query.where(write_model.wr_reply.like(f"{origin_reply}%"))
    else:
        origin_reply = write.wr_comment_reply
        query = (
            select(func.substr(write_model.wr_comment_reply, -1).label("reply"))
            .where(
                write_model.wr_parent == write.wr_parent,
                write_model.wr_comment == write.wr_comment,
                func.char_length(write_model.wr_comment_reply) == (len(origin_reply) + 1)
            )
        )
        if origin_reply:
            query = query.where(write_model.wr_comment_reply.like(f"{origin_reply}%"))

    # 정방향이면 최대값, 역방향이면 최소값
    if board.bo_reply_order:
        last_reply_char = db.scalar(query.order_by(desc("reply")))
        char_begin = "A"
        char_end = "Z"
        char_increase = 1
    else:
        last_reply_char = db.scalar(query.order_by(asc("reply")))
        char_begin = "Z"
        char_end = "A"
        char_increase = -1

    if last_reply_char == char_end:  # A~Z은 26 입니다.
        raise AlertException("더 이상 답변하실 수 없습니다. 답변은 26개 까지만 가능합니다.")

    if not last_reply_char:
        reply_char = char_begin
    else:
        reply_char = chr(ord(last_reply_char) + char_increase)

    db.close()

    return origin_reply + reply_char


def is_owner(mb_id_object: object, mb_id: str = None):
    """ 게시글/댓글 작성자인지 확인한다.

    Args:
        mb_id_object (object): mb_id 속성을 가진 객체
        mb_id (str, optional): 회원 아이디. Defaults to None.

    Returns:
        _type_: _description_
    """
    attr_mb_id = getattr(mb_id_object, "mb_id", None)
    if attr_mb_id:
        return attr_mb_id == mb_id
    else:
        return False


def send_write_mail(request: Request, board: Board, write: WriteBaseModel, origin_write: WriteBaseModel = None):
    """게시글/답글/댓글 작성 시, 메일을 발송한다.

    Args:
        request (Request): request 객체
        board (Board): 게시판 object
        write (WriteBaseModel): 작성된 게시글/답글/댓글 object
        origin_write (WriteBaseModel, optional): 원본 게시글/답글 object. Defaults to None.
    """
    with DBConnect().sessionLocal() as db:
        config = request.state.config
        templates = Jinja2Templates(
                directory=TemplateService.get_templates_dir())

        def _add_admin_email(admin_id: str):
            admin = db.scalar(select(Member).filter_by(mb_id=admin_id))
            if admin:
                send_email_list.append(admin.mb_email)

        send_email_list = []
        if config.cf_email_wr_board_admin and board.bo_admin:
            _add_admin_email(board.bo_admin)
        if config.cf_email_wr_group_admin and board.group.gr_admin:
            _add_admin_email(board.group.gr_admin)
        if config.cf_email_wr_super_admin:
            _add_admin_email(config.cf_admin)
        if config.cf_email_wr_write and origin_write:
            send_email_list.append(origin_write.wr_email)

        if write.wr_is_comment:
            act = "댓글"
            link_url = str(request.url_for("read_post", bo_table=board.bo_table, wr_id=origin_write.wr_id)) + f"#c_{write.wr_id}"

            if config.cf_email_wr_comment_all:
                # 댓글 쓴 모든 이에게 메일 발송
                write_model = dynamic_create_write_table(board.bo_table)
                query = select(write_model.wr_email).distinct().where(
                    write_model.wr_email.notin_(["", write.wr_email]),
                    write_model.wr_parent == origin_write.wr_id
                )
                comments = db.scalars(query).all()
                send_email_list.extend(email for email in comments)
        else:
            act = "답변글" if origin_write else "새글"
            link_url = request.url_for("read_post", bo_table=board.bo_table, wr_id=write.wr_id)

        # 중복 이메일 제거
        send_email_list = list(set(send_email_list))
        for email in send_email_list:
            subject = f"[{config.cf_title}] {board.bo_subject} 게시판에 {act}이 등록되었습니다."
            body = templates.TemplateResponse(
                "bbs/mail_form/write_update_mail.html", {
                    "request": request,
                    "act": act,
                    "board": board,
                    "wr_subject": write.wr_subject,
                    "wr_name": write.wr_name,
                    "wr_content": write.wr_content,
                    "link_url": link_url,
                }
            ).body.decode("utf-8")
            mailer(get_admin_email(request), email, subject, body, get_admin_email_name(request))


def get_list_thumbnail(request: Request, board: Board, write: WriteBaseModel, thumb_width: int, thumb_height: int, **kwargs):
    """게시글 목록의 섬네일 이미지를 생성한다.

    Args:
        request (Request): _description_
        board (Board): _description_
        write (WriteBaseModel): _description_
        thumb_width (int, optional): _description_. Defaults to 0.
        thumb_height (int, optional): _description_. Defaults to 0.
    """
    config = request.state.config
    with DBConnect().sessionLocal() as db:
        service = FileService(request, db)
        images, files = service.get_board_files_by_type(board.bo_table, write.wr_id)
    source_file = None
    result = {"src": "", "alt": "", "noimg":""}

    if images:
        # TODO : 게시글의 파일정보를 캐시된 데이터에서 조회한다.
        # 업로드 파일 목록
        source_file = images[0].bf_file
        result["alt"] = images[0].bf_content
    else:
        # TODO : 게시글의 본문정보를 캐시된 데이터에서 조회한다.
        # 게시글 본문
        editor_images = get_editor_image(write.wr_content, view=False)
        for image in editor_images:
            try:
                ext = image.split(".")[-1].lower()

                # 에디터로 삽입된 이미지의 주소는 웹 경로이기에 os.path로 체크할 수 있도록 경로를 변경한다.
                # 외부 이미지도 썸네일로 보여지기를 희망하는 경우 썸네일 조건 및 생성 로직을 수정해야한다.
                image = "./data/editor/" + image.split("/data/editor/")[1]

                # image경로의 파일이 존재하고 이미지파일인지 확인
                if (os.path.exists(image)
                        and os.path.isfile(image)
                        and os.path.getsize(image) > 0
                        and ext in config.cf_image_extension):
                    source_file = image
                    break

            except Exception as e:
                print(e)
                continue

    # 섬네일 생성
    if source_file:
        result["src"] = thumbnail(source_file, width=thumb_width, height=thumb_height, **kwargs)
    # 이미지가 없을 때
    else:
        result["src"] = thumbnail("./static/img/dummy-donotremove.png",
                        target_path="./data/thumbnail_tmp",
                        width=thumb_width, height=thumb_height, **kwargs)
        result["noimg"] = "img_not_found"

    return result


# 본문의 이미지 태그에 width를 강제로 지정하는 필터함수
def set_image_width(content: str, width: str = None) -> str:
    """본문의 이미지 태그에 width를 강제로 지정하는 필터함수

    Args:
        content (str): 게시글 본문
        width (int, optional): 이미지 width. Defaults to 0.

    Returns:
        str: 이미지 태그에 width가 추가된 본문
    """
    if width:
        content = re.sub(r"<img([^>]+)>", f"<img\\1 width={width}>", content)
    return content


def is_secret_write(write: WriteBaseModel = None) -> bool:
    """비밀글인지 확인한다.

    Args:
        write (WriteBaseModel, optional): 게시글 object. Defaults to None.

    Returns:
        bool: 비밀글 여부
    """
    return "secret" in getattr(write, "wr_option", "")


def url_auto_link(text: str, request: Request, is_nofollow: bool = True) -> str:
    """문자열 안에 포함된 URL을 링크로 변환한다.

    Args:
        text (str): 변환할 문자열.
        request (Request): Request 객체.
        is_nofollow: nofollow 속성 포함여부. Defaults to True.

    Returns:
        str: 변환된 문자열.
    """
    cf_link_target = getattr(request.state.config, "cf_link_target", "_blank")

    def _nofollow(attrs, _):
        if is_nofollow:
            return bleach.callbacks.nofollow(attrs)
        else:
            return attrs

    def _target(attrs, _):
        attrs = bleach.callbacks.target_blank(attrs)
        if (None, "target") in attrs:
            attrs[(None, "target")] = cf_link_target
        return attrs

    return bleach.linkify(text, callbacks=[_nofollow, _target], parse_email=True)


def is_write_delay(request: Request) -> bool:
    """특정 시간 간격 내에 다시 글을 작성할 수 있는지 확인하는 함수"""
    if request.state.is_super_admin:
        return True

    delay_sec = int(request.state.config.cf_delay_sec)
    current_time = datetime.now()
    write_time = request.session.get("ss_write_time")

    if delay_sec > 0:
        time_interval = timedelta(seconds=delay_sec)
        if write_time:
            available_time = datetime.strptime(write_time, "%Y-%m-%d %H:%M:%S") + time_interval
            if available_time > current_time:
                return False

    return True


def set_write_delay(request: Request):
    """글 작성 시간을 세션에 저장하는 함수"""
    delay_sec = int(request.state.config.cf_delay_sec)

    if not request.state.is_super_admin and delay_sec > 0:
        request.session["ss_write_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def insert_board_new(bo_table: str, write: WriteBaseModel) -> None:
    """최신글 테이블 등록 함수

    Args:
        bo_table (str): 게시판 코드
        write (WriteBaseModel): 게시글 모델
    """
    db = DBConnect().sessionLocal()
    db.execute(
        insert(BoardNew)
        .values(
            bo_table=bo_table,
            wr_id=write.wr_id,
            wr_parent=write.wr_parent,
            mb_id=write.mb_id,
        )
    )
    db.commit()
    db.close()


def render_latest_posts(request: Request, skin_name: str = 'basic', bo_table: str='',
                        rows: int = 10, subject_len: int = 40):
    """최신글 목록 HTML 출력

    Args:
        request (Request): _description_
        skin_name (str, optional): 스킨 경로. Defaults to ''.
        bo_table (str, optional): 게시판 코드. Defaults to ''.
        rows (int, optional): 노출 게시글 수. Defaults to 10.
        subject_len (int, optional): 제목길이 제한. Defaults to 40.

    Returns:
        str: 최신글 HTML
    """
    templates = UserTemplates()
    templates.env.globals["get_list_thumbnail"] = get_list_thumbnail

    device = request.state.device
    file_cache = FileCache()
    cache_filename = f"latest-{bo_table}-{device}-{skin_name}-{rows}-{subject_len}-{file_cache.get_cache_secret_key()}.html"
    cache_file = os.path.join(file_cache.cache_dir, cache_filename)

    # 캐시된 파일이 있으면 파일을 읽어서 반환
    if os.path.exists(cache_file):
        return file_cache.get(cache_file)

    with DBConnect().sessionLocal() as db:
        # 게시판 설정
        board = db.get(Board, bo_table)
        if not board:
            return ""

        board_config = BoardConfig(request, board)
        board.subject = board_config.subject

        #게시글 목록 조회
        write_model = dynamic_create_write_table(bo_table)
        writes = db.scalars(
            select(write_model)
            .where(write_model.wr_is_comment == 0)
            .order_by(write_model.wr_num)
            .limit(rows)
        ).all()
        for write in writes:
            write = get_list(request, db, write, board_config, subject_len)

    context = {
        "request": request,
        "board": board,
        "writes": writes,
        "bo_table": bo_table,
    }
    temp = templates.TemplateResponse(f"latest/{skin_name}.html", context)
    temp_decode = temp.body.decode("utf-8")

    # 캐시 파일 생성
    file_cache.create(temp_decode, cache_file)

    return temp_decode
