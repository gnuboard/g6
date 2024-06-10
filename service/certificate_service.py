"""본인인증 관련 기능을 제공하는 모듈입니다."""
from datetime import date, datetime, timedelta
import hashlib
from fastapi import Depends, Request
from sqlalchemy import func, insert, select
from typing_extensions import Annotated

from core.database import db_session
from core.exception import AlertCloseException
from core.models import CertHistory, Member, MemberCertHistory
from lib.common import get_client_ip
from service import BaseService
from service.member_service import MemberService


class CertificateService(BaseService):
    """본인인증 관련 기능을 제공하는 클래스입니다."""
    INICIS_MID_PREFIX = "SRA"
    INICIS_TEST_MID = 'INIiasTest'
    INICIS_TEST_API_KEY = 'TGdxb2l3enJDWFRTbTgvREU3MGYwUT09'
    KCP_SITE_CD_PREFIX = 'SM'
    KCP_TEST_SITE_CD = 'AO0QE'

    def __init__(
            self,
            request: Request,
            db: db_session,
            member_service: Annotated[MemberService, Depends()]
        ):
        self.request = request
        self.config  = request.state.config
        self.db = db
        self.member_service = member_service

        self.use_hp = getattr(request.state.config, "cf_use_hp", False)
        self.cert_use = getattr(request.state.config, "cf_cert_use", 0)
        self.cert_hp = getattr(request.state.config, "cf_cert_hp", None)
        self.cert_simple = getattr(request.state.config, "cf_cert_simple", None)
        self.cert_ipin = getattr(request.state.config, "cf_cert_ipin", None)
        self.cert_req = getattr(request.state.config, "cf_cert_req", 0)
        self.cert_limit = getattr(request.state.config, "cf_cert_limit", 0)

    def raise_exception(self, status_code: int, detail: str = None):
        raise AlertCloseException(status_code=status_code, detail=detail)

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

    def get_certificate_type(self, cert_type: str) -> str:
        """
        회원의 본인인증 방식을 반환합니다.
        """
        if cert_type == "hp":
            return "휴대폰"
        if cert_type == "simple":
            return "간편인증"
        if cert_type == "ipin":
            return "아이핀"
        return ""

    def get_kg_mid(self) -> str:
        """
        KG이니시스 본인인증을 위한 mid를 반환합니다.
        """
        if self.cert_use == 2:
            return f"{self.INICIS_MID_PREFIX}{self.config.cf_cert_kg_mid}"
        return self.INICIS_TEST_MID

    def get_kg_api_key(self) -> str:
        """
        KG이니시스 본인인증을 위한 api_key를 반환합니다.
        """
        if self.cert_use == 2:
            return self.config.cf_cert_kg_cd
        return self.INICIS_TEST_API_KEY

    def get_kcp_site_code(self) -> str:
        """
        KCP 본인인증을 위한 site_cd를 반환합니다.
        """
        if self.cert_use == 2:
            return f"{self.KCP_SITE_CD_PREFIX}{self.config.cf_cert_kcp_cd}"
        return self.KCP_TEST_SITE_CD

    def get_is_adult(self, birth_day: str) -> int:
        """만 19세 이상인지 여부를 반환합니다."""
        try:
            ago_19years = date.today() - timedelta(days=19*365)  # 19년전 오늘날짜 계산
            birthday = datetime.strptime(birth_day, "%Y%m%d").date()

            return 1 if birthday <= ago_19years else 0
        except Exception:
            return 0

    def get_cert_count(self, mb_id: str, cert_type: str) -> int:
        """회원의 본인인증 횟수를 반환합니다."""
        query = (select(func.count(CertHistory.cr_id))
                .where(CertHistory.cr_method == cert_type,
                        CertHistory.cr_date == date.today()))
        if mb_id:
            query = query.where(CertHistory.mb_id == mb_id)
        else:
            client_ip = get_client_ip(self.request)
            query = query.where(CertHistory.cr_ip == client_ip)

        return self.db.scalar(query)

    def create_dupinfo(self, ci: str):
        """
        본인인증 정보를 생성합니다.
        """
        return self.hashing_md5(f"{ci}{ci}")

    def create_cert_history(self, company: str, method: str, mb_id: str = '') -> None:
        """
        본인인증 이력을 생성합니다.
        """
        self.db.execute(
            insert(CertHistory).values(
                mb_id=mb_id,
                cr_company=company,
                cr_method=method,
                cr_ip=get_client_ip(self.request)
            )
        )
        self.db.commit()

    def create_member_cert_history(self, mb_id: str, mb_name: str,
                                   mb_hp: str, mb_birth: str, cert_type: str) -> None:
        """
        회원의 본인인증 변경 이력을 생성합니다.
        """
        self.db.execute(
            insert(MemberCertHistory).values(
                mb_id=mb_id,
                ch_name=mb_name,
                ch_hp=mb_hp,
                ch_birth=mb_birth,
                ch_type=cert_type
            )
        )
        self.db.commit()

    def remove_certificate_session(self):
        """
        본인인증 세션을 삭제합니다.
        """
        self.request.session.pop("ss_cert_no", None)
        self.request.session.pop("ss_cert_type", None)
        self.request.session.pop("ss_cert_hash", None)
        self.request.session.pop("ss_cert_adult", None)
        self.request.session.pop("ss_cert_birth", None)
        self.request.session.pop("ss_cert_dupinfo", None)

    def validate_certificate_limit(self, mb_id: str, cert_type: str) -> None:
        """
        본인인증 횟수 제한 검사
        """
        if self.cert_use == 2:
            return None
        if self.cert_limit == 0:
            return None
        if self.request.state.is_super_admin:
            return None

        cert_count = self.get_cert_count(mb_id, cert_type)
        if cert_count >= self.cert_limit:
            display_type = self.get_certificate_type(cert_type)
            self.raise_exception(400, f"오늘의 {display_type} 본인인증은 {self.cert_limit}회까지만 가능합니다.")

        return None

    def validate_member_dupinfo(self, dupinfo: str, member: Member):
        """이미 인증된 회원인지 검증합니다."""
        mb_certify = getattr(member, "mb_certify", "")
        mb_dupinfo = getattr(member, "mb_dupinfo", "")
        if (mb_certify and mb_dupinfo and len(mb_dupinfo) != 64):
            if mb_dupinfo != dupinfo:
                self.raise_exception(400, "해당 계정은 이미 다른명의로 본인인증 되어있는 계정입니다.")

    def validate_exists_dupinfo(self, dupinfo: str, mb_id: str):
        """이미 인증정보가 존재하는지 검증합니다."""
        exists_member = self.member_service.fetch_member_by_dupinfo(dupinfo, mb_id)
        if exists_member:
            self.raise_exception(400, f"입력하신 본인확인 정보로 이미 가입된 내역이 존재합니다.\
                                    \\n아이디 : {exists_member.mb_id}")

    def hasing_cert_hash(self, name: str, cert_type: str,
                         birth: str, cert_no: str, phone: str = None) -> str:
        """본인인증 데이터를 해싱하여 반환합니다."""
        if cert_type == "ipin":
            return self.hashing_md5(f"{name}{cert_type}{birth}{cert_no}")
        return self.hashing_md5(f"{name}{cert_type}{birth}{phone}{cert_no}")

    def hashing_md5(self, string: str) -> str:
        """문자열을 MD5로 해싱하여 반환합니다."""
        return hashlib.md5(string.encode()).hexdigest()

    def hashing_sha256(self, string: str) -> str:
        """문자열을 SHA256으로 해싱하여 반환합니다."""
        return hashlib.sha256(string.encode()).hexdigest()
