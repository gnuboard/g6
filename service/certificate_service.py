"""본인인증 관련 기능을 제공하는 모듈입니다."""
from fastapi import Request

from core.database import db_session
from core.exception import AlertException
from core.models import Member
from service import BaseService


class CertificateService(BaseService):
    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.config  = request.state.config
        self.db = db

        self.use_hp = getattr(request.state.config, "cf_use_hp", False)
        self.cert_use = getattr(request.state.config, "cf_cert_use", 0)
        self.cert_hp = getattr(request.state.config, "cf_cert_hp", None)
        self.cert_simple = getattr(request.state.config, "cf_cert_simple", None)
        self.cert_ipin = getattr(request.state.config, "cf_cert_ipin", None)
        self.cert_req = getattr(request.state.config, "cf_cert_req", 0)

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        return AlertException(status_code=status_code, detail=detail, url=url)

    def should_use_hp(self):
        """
        핸드폰번호 입력 창 표시여부를 반환합니다.

        본인확인 사용 설정이 되어있고,
        휴대폰인증, 간편인증 중 하나라도 설정되어 있는 경우 True를 반환합니다.
        """
        return self.cert_use and (self.cert_hp or self.cert_simple)

    def should_required_hp(self, member: Member = None) -> bool:
        """
        핸드폰번호 입력 필수여부를 반환합니다.

        본인확인 사용 설정이 되어있고,
        휴대폰인증, 간편인증 중 하나라도 설정되어 있고,
        가입 시 본인확인 필수가 설정되어 있고,
        회원의 본인인증 방식이 아이핀이 아닌 경우 True를 반환합니다.
        """
        return bool(
            self.should_use_hp()
            and self.cert_req
            and getattr(member, "mb_certify", "") != "ipin"
        )

    def get_certificate_type(self, member: Member) -> str:
        """
        회원의 본인인증 방식을 반환합니다.
        """
        if member.mb_certify == "hp":
            return "휴대폰"
        if member.mb_certify == "simple":
            return "간편인증"
        if member.mb_certify == "ipin":
            return "아이핀"
        return ""
