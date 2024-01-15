import os
from typing import Union

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models import Board, Config, Group, Member as MemberModel
from core.database import DBConnect
from lib.common import is_none_datetime


class MemberService(MemberModel):
    @classmethod
    def create_by_id(cls, db: Session, mb_id: str) -> "MemberService":
        query = select(cls).where(cls.mb_id == mb_id)

        return db.scalar(query)

    def is_intercept_or_leave(self) -> bool:
        """차단 또는 탈퇴한 회원인지 확인합니다.

        Returns:
            bool: 차단 또는 탈퇴한 회원이면 True, 아니거나 회원정보가 없으면 False
        """
        if not self.mb_id:
            return False

        return self.mb_leave_date or self.mb_intercept_date

    def is_email_certify(self, use_email_certify: bool) -> bool:
        """이메일 인증을 받았는지 확인합니다.
        Args:
            use_email_certify (bool): 이메일 인증을 사용하는지 여부

        Returns:
            bool: 이메일 인증을 받았으면 True, 아니면 False
        """
        if not use_email_certify:
            return True

        if not self.mb_id:
            return False

        return not is_none_datetime(self.mb_email_certify)


def get_member(mb_id: str) -> MemberModel:
    """회원 레코드 얻기
    -  fields: str = '*' # fields : 가져올 필드, 예) "mb_id, mb_name, mb_nick"

    Args:
        mb_id (str): 회원아이디

    Returns:
        Member: 회원 레코드
    """
    with DBConnect().sessionLocal() as db:
        member = db.scalar(select(MemberModel).filter_by(mb_id=mb_id))

    return member


def get_member_icon(mb_id: str = None) -> str:
    """회원 아이콘 경로를 반환하는 함수

    Args:
        mb_id (str, optional): 회원아이디. Defaults to None.

    Returns:
        str: 회원 아이콘 경로
    """
    icon_dir = "data/member"

    if mb_id:
        member_dir = f"{icon_dir}/{mb_id[:2]}"
        icon_path = os.path.join(member_dir, f"{mb_id}.gif")

        if os.path.exists(icon_path):
            mtime = os.path.getmtime(icon_path)  # 캐시를 위해 파일수정시간을 추가
            return f"/{icon_path}?{mtime}"

    return "/static/img/no_profile.gif"


def get_member_image(mb_id: str = None) -> str:
    """회원 이미지 경로를 반환하는 함수

    Args:
        mb_id (str, optional): 회원아이디. Defaults to None.

    Returns:
        str: 회원 이미지 경로
    """
    image_dir = "data/member_image"

    if mb_id:
        member_dir = f"{image_dir}/{mb_id[:2]}"
        image_path = os.path.join(member_dir, f"{mb_id}.gif")

        if os.path.exists(image_path):
            mtime = os.path.getmtime(image_path)  # 캐시를 위해 파일수정시간을 추가
            return f"/{image_path}?{mtime}"

    return "/static/img/no_profile.gif"


def get_member_level(request: Request) -> int:
    """request에서 회원 레벨 정보를 가져오는 함수"""
    member: MemberModel = request.state.login_member

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
