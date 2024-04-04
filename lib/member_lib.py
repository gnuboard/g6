"""회원 관련 기능을 제공하는 모듈입니다."""
import math
import os
import re
import secrets
from glob import glob
from datetime import date, datetime, timedelta
from typing import Union, Optional, Tuple

from fastapi import Request, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import exists, select

from core.database import DBConnect, db_session
from core.exception import AlertException
from core.models import Board, Config, Group, Member
from lib.common import is_none_datetime, delete_image, get_client_ip
from lib.pbkdf2 import validate_password
from lib.service import BaseService


class MemberService(BaseService):
    """
    회원 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    - 회원 정보 조회, 인증, 상태 검증 등의 기능을 포함합니다.

    ### Example

    ```python
        @router.get("/members/{mb_id}")
        async def read_member(
            member_service: Annotated[MemberService, Depends()],
            current_member: Annotated[Member, Depends(get_current_member)]
        ):
            return member_service.get_member_profile(current_member)
    ```
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db
        self.member = None

    def raise_exception(self, status_code: int = 400, detail: str = None):
        raise AlertException(detail, status_code)

    def create_member(self, data) -> Member:
        """회원 정보를 생성합니다."""
        config = self.request.state.config

        member = Member(**data.__dict__)
        member.mb_level = getattr(config, "cf_register_level", 1)
        member.mb_login_ip = get_client_ip(self.request)
        # 메일인증
        if getattr(config, "cf_use_email_certify", False):
            member.mb_email_certify2 = secrets.token_hex(16)  # 일회용 인증키
        else:
            member.mb_email_certify = datetime.now()  # 인증완료

        self.db.add(member)
        self.db.commit()

        return member

    def read_member(self, mb_id: str) -> Member:
        """회원 정보를 조회합니다."""
        if self.member is None:
            member = self._fetch_member_by_id(mb_id)
            if not member:
                self.raise_exception(
                    status_code=404, detail=f"{mb_id} : 회원정보가 없습니다.")
            self.member = member
        return self.member

    def authenticate_member(self, mb_id: str, password: str) -> Member:
        """
        비밀번호를 검증하여 회원 인증을 수행합니다.
        - 회원 정보가 없거나 탈퇴 또는 차단된 회원은 조회할 수 없습니다.
        - 이메일 인증이 완료되지 않은 회원은 조회할 수 없습니다.
        """
        # 아이디, 비밀번호 중 어떤 것이 틀렸는지 알려주지 않도록 하기 위해
        # self.fetch_member()를 호출하지 않습니다.
        member = self._fetch_member_by_id(mb_id)
        if not member or not validate_password(password, member.mb_password):
            self.raise_exception(
                status_code=403, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

        is_active, message = self.is_activated(member)
        if not is_active:
            self.raise_exception(status_code=403, detail=message)

        is_certified, message = self.is_member_email_certified(member)
        if not is_certified:
            self.raise_exception(status_code=403, detail=message)

        return member

    def get_member(self, mb_id: str) -> Member:
        """
        현재 회원 정보를 조회합니다.
        - 회원 정보가 없거나 탈퇴 또는 차단된 회원은 조회할 수 없습니다.
        - 이메일 인증이 완료되지 않은 회원은 조회할 수 없습니다.
        """
        member = self.read_member(mb_id)
        is_active, message = self.is_activated(member)
        if not is_active:
            self.raise_exception(status_code=403, detail=message)

        is_certified, message = self.is_member_email_certified(member)
        if not is_certified:
            self.raise_exception(status_code=403, detail=message)

        return member

    def read_email_non_certify_member(self, mb_id: str, key: str) -> Member:
        """
        이메일 인증처리가 안된 회원 정보를 조회합니다.
        - 회원 정보가 없거나 탈퇴 또는 차단된 회원은 조회할 수 없습니다.
        - 이미 인증된 회원은 조회할 수 없습니다.
        - 메일인증 요청 정보(key)가 올바르지 않으면 조회할 수 없습니다.
        """
        member = self.read_member(mb_id)

        is_active, message = self.is_activated(member)
        if not is_active:
            self.raise_exception(status_code=403, detail=message)

        if not is_none_datetime(member.mb_email_certify):
            self.raise_exception(status_code=409, detail="이미 인증된 회원입니다.")

        if member.mb_email_certify2 != key:
            self.raise_exception(
                status_code=400, detail="메일인증 요청 정보가 올바르지 않습니다.")

        return member

    def get_member_profile(self, mb_id: str, current_member: Member) -> Member:
        """
        회원 프로필 정보를 조회합니다.
        - 최고관리자 또는 자신의 정보는 정보공개 여부를 확인하지 않습니다.
        - 정보공개 여부가 설정되어 있지 않은 회원은 조회할 수 없습니다.
        """
        member = self.read_member(mb_id)
        # 최고관리자도 아니고 자신의 정보가 아니면 정보공개 여부를 확인합니다.
        if not (self.request.state.is_super_admin or current_member.mb_id == mb_id):
            if not current_member.mb_open:
                self.raise_exception(
                    status_code=403, detail="자신의 정보를 공개하지 않으면 다른분의 정보를 조회할 수 없습니다.\\n\\n정보공개 설정은 회원정보수정에서 하실 수 있습니다.")
            if not member.mb_open:
                self.raise_exception(
                    status_code=403, detail="회원정보를 공개하지 않은 회원입니다.")

        return member

    def is_activated(self, member: Member) -> Tuple[bool, str]:
        """활성화된 회원인지 확인합니다."""
        if member.mb_leave_date or member.mb_intercept_date:
            return False, "현재 로그인 회원은 탈퇴 또는 차단된 회원입니다."
        return True, "정상 회원입니다."

    def is_member_email_certified(self, member: Member) -> Tuple[bool, str]:
        """이메일 인증이 완료된 회원인지 확인합니다."""
        config = self.request.state.config

        if config.cf_use_email_certify and is_none_datetime(member.mb_email_certify):
            return False, f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다."
        return True, "이메일 인증을 완료한 회원입니다."

    def update_member(self, member: Member, data: dict) -> Member:
        """회원 정보를 수정합니다."""
        member_data = data.items()
        for key, value in member_data:
            if hasattr(member, key) and value is not None:
                setattr(member, key, value)
        self.db.commit()

        return member

    def leave_member(self, member: Member):
        """
        회원을 탈퇴 처리합니다
        - 회원 정보를 탈퇴 처리하고 탈퇴일자를 기록합니다.
        - 실제 데이터는 삭제되지 않습니다.
        """
        member.mb_leave_date = datetime.now().strftime("%Y%m%d")
        member.mb_memo = f"{member.mb_memo}\n{datetime.now().strftime('%Y-%m-%d')}탈퇴함"
        self.db.commit()

    def find_id(self, mb_name: str, mb_email: str) -> Member:
        """
        회원 아이디를 찾습니다.
        - 최고관리자는 제외합니다.
        - 소셜로그인으로 가입한 회원은 아이디를 찾을 수 없습니다.
        """
        from bbs.social import SocialAuthService

        config = self.request.state.config
        member = self.db.scalar(
            select(Member).where(
                Member.mb_name == mb_name,
                Member.mb_email == mb_email,
                Member.mb_id != getattr(
                    config, "cf_admin", "admin")  # 최고관리자는 제외
            )
        )
        if not member:
            self.raise_exception(
                status_code=400, detail="입력하신 정보와 일치하는 회원이 없습니다.")
        if SocialAuthService.check_exists_by_member_id(member.mb_id):
            self.raise_exception(
                status_code=400, detail="소셜로그인으로 가입하신 회원은 아이디를 찾을 수 없습니다.")

        return hide_member_id(member.mb_id), member.mb_datetime.strftime("%Y-%m-%d %H:%M:%S")

    def find_member_from_password_info(self, mb_id: str, mb_email: str) -> Member:
        """
        비밀번호 찾기 정보로 회원을 찾습니다.
        - 최고관리자는 제외합니다.
        - 소셜로그인으로 가입한 회원은 비밀번호를 찾을 수 없습니다.
        """
        from bbs.social import SocialAuthService

        config = self.request.state.config
        member = self.db.scalar(
            select(Member).where(
                Member.mb_id == mb_id,
                Member.mb_email == mb_email,
                Member.mb_id != config.cf_admin  # 최고관리자는 제외
            )
        )
        if not member:
            self.raise_exception(
                status_code=400, detail="입력하신 정보와 일치하는 회원이 없습니다.")

        if SocialAuthService.check_exists_by_member_id(member.mb_id):
            self.raise_exception(
                status_code=400, detail="소셜로그인으로 가입하신 회원은 비밀번호를 찾을 수 없습니다.")

        # 비밀번호 재설정 토큰 저장
        member.mb_lost_certify = secrets.token_hex(16)
        self.db.commit()
        self.db.refresh(member)

        return member

    def reset_password(self, mb_id: str, token: str, mb_password: str):
        """비밀번호를 재설정합니다."""
        from bbs.social import SocialAuthService

        config = self.request.state.config
        member = self.db.scalar(
            select(Member).where(
                Member.mb_id == mb_id,
                Member.mb_lost_certify == token,
                Member.mb_id != config.cf_admin  # 최고관리자는 제외
            )
        )
        if not member:
            self.raise_exception(status_code=403, detail="유효하지 않은 요청입니다.")

        if SocialAuthService.check_exists_by_member_id(member.mb_id):
            self.raise_exception(
                status_code=400, detail="소셜로그인으로 가입하신 회원은 비밀번호를 재설정할 수 없습니다.")

        member.mb_password = mb_password
        member.mb_lost_certify = ""
        self.db.commit()

    def _fetch_member_by_id(self, mb_id: str) -> Member:
        """회원 정보를 데이터베이스에서 조회합니다."""
        return self.db.scalar(select(Member).where(Member.mb_id == mb_id))


class MemberImageService(BaseService):
    """
    회원 이미지 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """
    ICON_DIR = "data/member"
    IMAGE_DIR = "data/member_image"
    NO_IMAGE_PATH = "/static/img/no_profile.gif"

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    @staticmethod
    def get_icon_path(mb_id: str) -> str:
        """회원 아이콘 이미지 경로를 반환합니다.

        Args:
            mb_id (str, optional): 회원아이디. Defaults to None.

        Returns:
            str: 회원 아이콘 경로
        """
        directory = MemberImageService.ICON_DIR
        return MemberImageService._get_image_path(directory, mb_id)

    @staticmethod
    def get_image_path(mb_id: str) -> str:
        """회원 이미지 경로를 반환합니다.

        Args:
            mb_id (str, optional): 회원아이디. Defaults to None.

        Returns:
            str: 회원 이미지 경로
        """
        directory = MemberImageService.IMAGE_DIR
        return MemberImageService._get_image_path(directory, mb_id)

    @staticmethod
    def _get_image_path(directory: str, mb_id: str = None) -> str:
        """이미지 경로를 반환하는 함수
        - 회원 아이콘/이미지는 아이디의 앞 2자리 디렉토리에 저장됩니다.

        Args:
            directory (str): 이미지 경로
            mb_id (str, optional): 회원아이디.

        Returns:
            str: 이미지 경로
        """
        if not mb_id:
            return MemberImageService.NO_IMAGE_PATH

        member_directory = os.path.join(directory, mb_id[:2])
        image_files = glob(os.path.join(member_directory, f"{mb_id}.*"))
        if image_files:
            mtime = os.path.getmtime(image_files[0])  # 캐시를 위해 파일 수정시간을 추가
            return f"/{image_files[0]}?{int(mtime)}"

        return MemberImageService.NO_IMAGE_PATH

    def update_image_file(
            self,
            mb_id: str,
            image_type: str,
            file: Optional[UploadFile],
            is_delete: Optional[int]) -> None:
        """
        회원 아이콘/이미지 파일 저장 및 삭제 처리

        Args:
            request: FastAPI Request 객체
            mb_id: 회원 아이디
            file: 업로드할 아이콘/이미지 파일
            is_delete: 아이콘/이미지 삭제 여부
        """
        directory = self.IMAGE_DIR if image_type == "image" else self.ICON_DIR
        sub_directory = mb_id[:2]
        image_directory = os.path.join(directory, sub_directory)
        image_obj = self._validate_and_open_image(file, image_type)

        if is_delete or image_obj:
            self._delete_existing_images(image_directory, mb_id)

        if image_obj:
            # 이미지 저장 경로 생성
            os.makedirs(image_directory, exist_ok=True)
            # 이미지 저장
            file_ext = image_obj.format.lower()
            save_path = os.path.join(image_directory, f"{mb_id}.{file_ext}")

            image_obj.save(save_path)
            image_obj.close()

    def _delete_existing_images(self, directory: str, mb_id: str):
        """기존 이미지 파일 삭제 처리"""
        existing_images = glob(os.path.join(directory, f"{mb_id}.*"))
        for image in existing_images:
            os.remove(image)

    def _save_image_file(self, file: UploadFile, directory: str, mb_id: str, image_type: str):
        """이미지 파일 저장 처리"""
        image_obj = self._validate_and_open_image(file, image_type)
        if image_obj:
            # 이미지 저장 경로
            file_ext = image_obj.format.lower()
            save_path = os.path.join(directory, mb_id[:2], f"{mb_id}.{file_ext}")
            # 이미지 저장 경로 생성
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            # 이미지 저장
            image_obj.save(save_path)
            image_obj.close()

    def _validate_and_open_image(
            self,
            file: Optional[UploadFile],
            image_type: str) -> Optional[Image.Image]:
        """
        회원 이미지 파일 유효성 검사

        Args:
            file: 업로드할 이미지 파일
            image_type: 이미지 타입 (img, icon)

        Raises:
            self.raise_exception: 이미지 파일이 아닌 경우
        """

        if not file or not file.filename:
            return None

        config = self.request.state.config
        img_ext_regex = getattr(config, "cf_image_extension", "")
        image_config = self._get_image_type_config(image_type)

        try:
            image_obj = Image.open(file.file)
        except UnidentifiedImageError:
            self.raise_exception(400, "이미지 파일이 아닙니다.")

        width, height = image_obj.size
        type_name = image_config['name']
        cf_size = image_config['cf_size']
        cf_width = image_config['cf_width']
        cf_height = image_config['cf_height']

        if cf_size and file.size > cf_size:
            self.raise_exception(
                400, f"{type_name} 용량은 {cf_size} 이하로 업로드 해주세요.")

        if (cf_width and width > cf_width) or (cf_height and height > cf_height):
            self.raise_exception(
                400, f"{type_name} 크기는 {cf_width}x{cf_height} 이하로 업로드 해주세요.")

        if img_ext_regex:
            if not re.match(fr".*\.({img_ext_regex})$", file.filename, re.IGNORECASE):
                img_ext_str = img_ext_regex.replace("|", ", ")
                self.raise_exception(400, f"{img_ext_str} 파일만 업로드 가능합니다.")

        return image_obj

    def _get_image_type_config(self, image_type: str) -> dict:
        """이미지 타입에 따른 설정을 반환합니다."""
        config = self.request.state.config
        img_type_dict = {
            'icon': {
                'name': '아이콘',
                'cf_size': config.cf_member_icon_size,
                'cf_width': config.cf_member_icon_width,
                'cf_height': config.cf_member_icon_height,
            },
            'image': {
                'name': '이미지',
                'cf_size': config.cf_member_img_size,
                'cf_width': config.cf_member_img_width,
                'cf_height': config.cf_member_img_height,
            },
        }
        return img_type_dict[image_type]


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


def is_email_registered(email: str, mb_id: str = None) -> bool:
    """이메일이 이미 등록되어 있는지 확인

    Args:
        email (str): 이메일 주소
        mb_id (str, optional): 회원 아이디. Defaults to None.
            회원정보 수정시 자신의 이메일을 제외하기 위해 사용

    Returns:
        bool: 이미 등록된 이메일이면 True, 아니면 False
    """
    query = exists(Member).where(Member.mb_email == email).select()
    if mb_id:
        query = query.where(Member.mb_id != mb_id)

    with DBConnect().sessionLocal() as db:
        exists_member = db.scalar(query)

    if exists_member:
        return True
    else:
        return False


def is_prohibit_email(request: Request, email: str):
    """금지된 메일인지 검사

    Args:
        request (Request): request 객체
        email (str): 이메일 주소

    Returns:
        bool: 금지된 메일이면 True, 아니면 False
    """
    config = request.state.config
    _, domain = email.split("@")

    # config에서 금지된 도메인 목록 가져오기
    cf_prohibit_email = getattr(config, "cf_prohibit_email", "")
    if cf_prohibit_email:
        prohibited_domains = [d.lower().strip() for d in cf_prohibit_email.split('\n')]

        # 주어진 도메인이 금지된 도메인 목록에 있는지 확인
        if domain.lower() in prohibited_domains:
            return True

    return False


def validate_mb_id(request: Request, mb_id: str) -> Tuple[bool, str]:
    """ 회원가입이 가능한 아이디인지 검사

    Args:
        request (Request): request 객체
        mb_id (str): 가입할 아이디

    Returns:
        Tuple[bool, str]: (검사 결과, 메시지)
    """
    config = request.state.config

    if not mb_id or mb_id.strip() == "":
        return False, "아이디를 입력해주세요."

    with DBConnect().sessionLocal() as db:
        exists_id = db.scalar(
            exists(Member).where(Member.mb_id == mb_id).select()
        )
    if exists_id:
        return False, "이미 가입된 아이디입니다."

    prohibited_ids = [id.strip() for id in getattr(config, "cf_prohibit_id", "").split(",")]
    if mb_id in prohibited_ids:
        return False, "사용할 수 없는 아이디입니다."

    return True, "사용 가능한 아이디입니다."


def validate_nickname(request: Request, mb_nick: str) -> Tuple[bool, str]:
    """ 등록 가능한 닉네임인지 검사

    Args:
        mb_nick : 등록할 닉네임
        prohibit_id : 금지된 닉네임

    Return:
        가능한 닉네임이면 True 아니면 에러메시지 배열

    """
    config = request.state.config

    if not mb_nick or mb_nick.strip() == "":
        return False, "닉네임을 입력해주세요."

    with DBConnect().sessionLocal() as db:
        exists_nickname = db.scalar(
            exists(Member).where(Member.mb_nick == mb_nick).select()
        )
    if exists_nickname:
        return False, "해당 닉네임이 존재합니다."

    if mb_nick in getattr(config, "cf_prohibit_id", "").strip():
        return False, "닉네임으로 정할 수 없는 단어입니다."

    return True, "사용 가능한 닉네임입니다."


def validate_nickname_change_date(before_nick_date: date,
                                  nick_modify_date: int) -> Tuple[bool, str]:
    """
        닉네임 변경 가능한지 날짜 검사
        Args:
            before_nick_date (datetime) : 이전 닉네임 변경한 날짜
            nick_modify_date (int) : 닉네임 수정가능일
        Raises:
            ValidationError: 닉네임 변경 가능일 안내
    """
    if not is_none_datetime(before_nick_date) and nick_modify_date != 0:
        available_date = before_nick_date + timedelta(days=nick_modify_date)
        if datetime.now().date() < available_date:
            return False, f"{available_date.strftime('%Y-%m-%d')} 이후 닉네임을 변경할 수 있습니다."

    return True, "닉네임을 변경할 수 있습니다."


def validate_email(request: Request, email: str) -> Tuple[bool, str]:
    """ 등록 가능한 이메일인지 검사

    Args:
        Request: request 객체
        email (str): 이메일 주소

    Returns:
        Tuple[bool, str]: (검사 결과, 메시지)

    """
    if not email or email.strip() == "":
        return False, "이메일을 입력해주세요."

    if is_email_registered(email):
        return False, "이미 가입된 이메일입니다."

    if is_prohibit_email(request, email):
        return False, "사용할 수 없는 이메일입니다."

    return True, "사용 가능한 이메일입니다."


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
