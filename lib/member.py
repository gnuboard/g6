"""회원 관련 기능을 제공하는 모듈입니다."""
import math
from datetime import date, datetime, timedelta
from typing import Tuple, Union

from fastapi import Request

from core.models import Board, Config, Group, Member


class MemberDetails:
    mb_no: int = 0
    mb_id: str = None
    mb_name: str = None
    mb_nick: str = None
    mb_email: str = None
    mb_homepage: str = None
    mb_level: int = 1
    mb_tel: str = None
    mb_hp: str = None
    mb_certify: str = None
    mb_adult: int = 0
    mb_signature: str = None
    mb_point: int = 0
    mb_today_login: datetime = None
    mb_login_ip: str = None
    mb_datetime: datetime = None
    mb_ip: str = None
    mb_leave_date: str = None
    mb_intercept_date: str = None
    mb_mailling: int = 0
    mb_sms: int = 0
    mb_profile: int = 0

    _admin_type: str = None

    def __init__(
        self,
        request: Request,
        member: Member,
        board: Board = None,
        group: Group = None
    ):
        # TODO: 반복적으로 호출되는 문제 해결해야함.
        # print("__init__", member)
        super().__init__()

        self.request = request
        self.config = request.state.config
        # member의 속성을 class 속성에 복사
        if member:
            for key, value in member.__dict__.items():
                setattr(self, key, value)
        self.level: int = self.mb_level
        self.admin_type: Union[str, None] = self.get_admin_type(group, board)

    def get_admin_type(self, group: Group = None, board: Board = None) -> Union[str, None]:
        """게시판 관리자 여부 확인 후 관리자 타입 반환
        Args:
            group (Group, optional): 게시판 그룹 정보. Defaults to None.
            board (Board, optional): 게시판 정보. Defaults to None.

        Returns:
            Union[str, None]: 관리자 타입 (super, group, board, None)
        """
        if not self.mb_id:
            return None

        group = group or (board.group if board else None)

        is_authority = None
        if self.config.cf_admin == self.mb_id:
            is_authority = "super"
        elif group and group.gr_admin == self.mb_id:
            is_authority = "group"
        elif board and board.bo_admin == self.mb_id:
            is_authority = "board"

        return is_authority

    def is_super_admin(self) -> bool:
        """최고관리자 여부 확인"""
        cf_admin = str(self.config.cf_admin).lower().strip()

        if not cf_admin:
            return False

        if self.mb_id and self.mb_id.lower().strip() == cf_admin:
            return True

        return False


def get_member_level(request: Request) -> int:
    """request에서 회원 레벨 정보를 가져오는 함수"""
    member: Member = request.state.login_member

    return int(member.mb_level) if member else 1


def get_admin_type(request: Request, mb_id: str = None,
                   group: Group = None, board: Board = None) -> Union[str, None]:
    """게시판 관리자 여부 확인 후 관리자 타입 반환
    - 그누보드5의 is_admin 함수를 참고하여 작성하려고 했으나, 이미 is_admin가 있어서 함수 이름을 변경함

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str, optional): 회원 아이디. Defaults to None.
        group (Group, optional): 게시판 그룹 정보. Defaults to None.
        board (Board, optional): 게시판 정보. Defaults to None.

    Returns:
        Union[str, None]: 관리자 타입 (super, group, board, None)
    """
    if not mb_id:
        return None

    config = request.state.config
    group = group or (board.group if board else None)

    is_authority = None
    if config.cf_admin == mb_id:
        is_authority = "super"
    elif group and group.gr_admin == mb_id:
        is_authority = "group"
    elif board and board.bo_admin == mb_id:
        is_authority = "board"

    return is_authority


def is_super_admin(request: Request, mb_id: str = None) -> bool:
    """최고관리자 여부 확인

    Args:
        request (Request): FastAPI Request 객체
        mb_id (str, optional): 회원 아이디. Defaults to None.

    Returns:
        bool: 최고관리자이면 True, 아니면 False
    """
    config: Config = request.state.config
    cf_admin = str(config.cf_admin).lower().strip()

    if not cf_admin:
        return False

    mb_id = mb_id or request.session.get("ss_mb_id", "")
    if mb_id and mb_id.lower().strip() == cf_admin:
        return True

    return False


def get_next_open_date(request: Request, open_date: date = None) -> str:
    """다음 프로필 공개 가능일을 반환

    Args:
        request (Request): FastAPI Request 객체
        open_date (date): 최근 프로필 공개 변경일

    Returns:
        datetime: 다음 프로필 공개 가능일
    """
    open_days = getattr(request.state.config, "cf_open_modify", 0)
    if open_days == 0:
        return ""

    base_date = open_date if open_date else date.today()
    calculated_date = base_date + timedelta(days=open_days)

    return calculated_date.strftime("%Y-%m-%d")


def hide_member_id(mb_id: str):
    """아이디를 가리기 위한 함수
    - 아이디의 절반을 가리고, 가려진 부분은 *로 표시한다.

    Args:
        mb_id (str): 회원 아이디

    Returns:
        str: 가려진 회원 아이디
    """
    id_len = len(mb_id)
    hide_len = math.floor(id_len / 2)
    start_len = math.ceil((id_len - hide_len) / 2)
    end_len = math.floor((id_len - hide_len) / 2)
    return mb_id[:start_len] + "*" * hide_len + mb_id[-end_len:]


def set_zip_code(zip_code: str = None) -> Tuple[str, str]:
    """우편번호를 앞뒤 3자리로 나누는 함수

    Args:
        zip_code (str): 우편번호

    Returns:
        Tuple[str, str]: (앞 3자리, 뒤 3자리)
    """
    if not zip_code:
        return "", ""

    return zip_code[:3], zip_code[3:6]
