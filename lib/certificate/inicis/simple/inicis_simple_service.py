"""KG이니시스 간편인증 서비스를 위한 클래스를 정의합니다."""
from datetime import datetime
import random
import urllib.parse

from cryptography.hazmat.primitives.ciphers import modes
from fastapi import Depends, Request
from fastapi.datastructures import FormData
from typing_extensions import Annotated

from core.exception import AlertCloseException
from lib.certificate.base import CertificateBase
from lib.certificate.base import post_request
from lib.certificate.inicis.simple.lib.seed import SEED128
from service import BaseService
from service.certificate_service import CertificateService


class InicisSimpleService(CertificateBase, BaseService):
    """KG이니시스 간편인증 서비스를 위한 클래스입니다."""
    VALID_URLS = ["https://kssa.inicis.com", "https://fcsa.inicis.com"]
    INICIS_SEEDIV = 'SASKGINICIS00000'  # SEED 복호화에 사용되는 IV

    def __init__(
            self,
            request: Request,
            cert_service: Annotated[CertificateService, Depends()],
        ) -> None:
        self.request = request
        self.cert_service = cert_service

    def raise_exception(self, status_code: int, detail: str = None):
        raise AlertCloseException(status_code=status_code, detail=detail)

    async def get_request_data(self) -> dict:
        """KG이니시스 본인인증 창을 띄우기 위한 데이터를 반환합니다."""
        mid = self.cert_service.get_kg_mid()
        api_key = self.cert_service.get_kg_api_key()

        timestamp = int(datetime.now().timestamp())
        random_num = random.randint(1000, 9999)
        m_tx_id = f"SIR_{timestamp}{random_num}"
        req_svc_cd = '01'
        user_name = ''
        user_phone = ''
        user_birth = ''

        return {
            "mid": mid,
            "api_key": api_key,
            "m_tx_id": m_tx_id,
            "req_svc_cd": req_svc_cd,
            "identifier": '테스트 서명',
            "user_name": user_name,
            "user_phone": user_phone,
            "user_birth": user_birth,
            "auth_hash": self.cert_service.hashing_sha256(f"{mid}{m_tx_id}{api_key}"),
            "user_hash": self.cert_service.hashing_sha256(
                f"{user_name}{mid}{user_phone}{m_tx_id}{user_birth}{req_svc_cd}"),
        }

    async def get_result_data(self, response: FormData) -> dict:
        """KG이니시스 본인인증 결과 데이터를 반환합니다."""
        # 인증응답 데이터
        result_code = response.get('resultCode')
        result_msg = response.get('resultMsg')
        result_msg = urllib.parse.unquote(result_msg.replace('+', ' '))
        auth_request_url = response.get('authRequestUrl')
        tx_id = response.get('txId')
        token = response.get('token')

        self._validate_result_code(result_code, result_msg)
        self._validate_url(auth_request_url)

        # 결과 조회 요청
        data = {
            'mid': self.cert_service.get_kg_mid(),
            'txId': tx_id
        }
        result_data = await post_request(auth_request_url, data, {'Accept': 'application/json'})

        self._validate_result_code(result_data['resultCode'], result_data['resultMsg'])

        # 결과 데이터
        cert_no = result_data.get('txId')
        ci = result_data.get('userCi', '')
        user_name = result_data.get('userName', '')
        user_phone = result_data.get('userPhone', '')
        user_birthday = result_data.get('userBirthDay', '')

        seed = SEED128(self.INICIS_SEEDIV, token)
        user_name = seed.decode(modes.CBC, user_name)
        user_phone = seed.decode(modes.CBC, user_phone)
        user_birthday = seed.decode(modes.CBC, user_birthday)

        self._validate_phone(user_phone)

        return {
            "cert_no": cert_no,
            "ci": ci,
            "user_name": user_name,
            "user_phone": user_phone,
            "user_birthday": user_birthday,
        }

    def _validate_result_code(self, result_code: str, result_msg: str):
        """결과 코드를 검증합니다."""
        if result_code != "0000":
            self.raise_exception(400, result_msg)

    def _validate_url(self, url: str):
        """인증요청 URL을 검증합니다."""
        if not any(url.startswith(valid_url) for valid_url in self.VALID_URLS):
            self.raise_exception(400, "올바르지 않은 인증요청 URL입니다.")

    def _validate_phone(self, phone: str):
        """핸드폰 번호를 검증합니다."""
        if not phone:
            self.raise_exception(400, "핸드폰 번호가 없습니다. 본인인증에 실패하였습니다.")
