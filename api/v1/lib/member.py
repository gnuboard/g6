"""회원 관련 유틸리티 함수를 제공합니다."""
import abc
from typing import Tuple
from typing_extensions import Annotated

from fastapi import HTTPException, Path, Request
from sqlalchemy.sql import select

from core.database import db_session
from core.exception import AlertException
from core.models import Member
from lib.common import is_none_datetime
from lib.pbkdf2 import validate_password


class BaseService(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def raise_exception(self, status_code: int, detail: str = None):
        pass


class MemberService(BaseService):
    """
    회원 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    - 회원 정보 조회, 인증, 상태 검증 등의 기능을 포함합니다.
    """
    def __init__(self, request: Request, db: db_session, mb_id: Annotated[str, Path(...)]):
        self.request = request
        self.db = db
        self.mb_id = mb_id
        self.member = None

    def raise_exception(self, status_code: int = 400, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)

    def fetch_member(self) -> Member:
        """회원 정보를 조회합니다."""
        if self.member is None:
            member = self._fetch_member_by_id()
            if not member:
                self.raise_exception(status_code=404, detail=f"{self.mb_id} : 회원정보가 없습니다.")
            self.member = member
        return self.member
    
    def authenticate_member(self, password: str) -> Member:
        """회원 인증을 수행합니다."""
        # 아이디, 비밀번호 중 어떤 것이 틀렸는지 알려주지 않도록 하기 위해
        # self.fetch_member()를 호출하지 않고 바로 쿼리를 실행합니다.
        member = self._fetch_member_by_id()
        if not member or not validate_password(password, member.mb_password):
            self.raise_exception(status_code=403, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

        is_active, message = self.is_activated(member)
        if not is_active:
            self.raise_exception(status_code=403, detail=message)

        is_certified, message = self.is_member_email_certified(member)
        if not is_certified:
            self.raise_exception(status_code=403, detail=message)

        return member
    
    def get_current_member(self) -> Member:
        """현재 로그인한 회원 정보를 조회합니다."""
        member = self.fetch_member()

        is_active, message = self.is_activated(member)
        if not is_active:
            self.raise_exception(status_code=403, detail=message)

        is_certified, message = self.is_member_email_certified(member)
        if not is_certified:
            self.raise_exception(status_code=403, detail=message)

        return member
    
    def get_email_non_certify_member(self, key: str) -> Member:
        """이메일 인증처리가 안된 회원 정보를 조회합니다."""
        member = self.fetch_member()

        is_active, message = self.is_activated(member)
        if not is_active:
            self.raise_exception(status_code=403, detail=message)

        if not is_none_datetime(member.mb_email_certify):
            raise HTTPException(status_code=409, detail="이미 인증된 회원입니다.")

        if member.mb_email_certify2 != key:
            raise HTTPException(status_code=400, detail="메일인증 요청 정보가 올바르지 않습니다.")

        return member
    
    def get_member_profile(self, current_member: Member) -> Member:
        """회원 프로필 정보를 조회합니다."""
        member = self.fetch_member()

        if member.mb_open == 0 and member.mb_id != current_member.mb_id:
            self.raise_exception(status_code=403, detail="회원정보를 공개하지 않은 회원입니다.")

        return member
    
    def is_activated(self, member: Member) -> Tuple[bool, str]:
        """활성화된 회원인지 확인합니다."""
        if member.mb_leave_date or member.mb_intercept_date:
            return False, "현재 로그인한 회원은 탈퇴 또는 차단된 회원입니다."
        return True, "정상 회원입니다."
    
    def is_member_email_certified(self, member: Member) -> Tuple[bool, str]:
        """이메일 인증이 완료된 회원인지 확인합니다."""
        config = self.request.state.config

        if config.cf_use_email_certify and is_none_datetime(member.mb_email_certify):
            return False, f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다."
        return True, "이메일 인증을 완료한 회원입니다."
    
    def _fetch_member_by_id(self) -> Member:
        """회원 정보를 데이터베이스에서 조회합니다."""
        return self.db.scalar(select(Member).where(Member.mb_id == self.mb_id))


class MemberServiceAPI(MemberService):
    """
    API 요청에 사용되는 MemberService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.

    ### Example

    ```python
        @router.get("/members/{mb_id}")
        async def read_member(
            member_service: Annotated[MemberServiceAPI, Depends()],
            current_member: Annotated[Member, Depends(get_current_member)]
        ):
            return member_service.get_member_profile(current_member)
    ```
    """
    def raise_exception(self, status_code: int, detail: str = None):
        super().raise_exception(status_code, detail)


class MemberServiceTemplate(MemberService):
    """
    템플릿 렌더링에 사용되는 MemberService 구현 클래스.  
    - 이 클래스는 템플릿과 관련된 예외 처리(AlertException 사용)를 구현합니다.

    ### Example

    ```python
        @router.get("/members/{mb_id}")
        async def read_member(
            member_service: Annotated[MemberServiceTemplate, Depends()],
            current_member: Annotated[Member, Depends(get_current_member)]
        ):
            return member_service.get_member_profile(current_member)
    ```
    """
    def raise_exception(self, status_code: int, detail: str = None):
        raise AlertException(status_code=status_code, detail=detail)