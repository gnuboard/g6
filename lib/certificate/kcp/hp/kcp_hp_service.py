"""KCP 휴대폰인증 서비스를 위한 클래스를 정의합니다."""
import base64
import os
from datetime import datetime
from typing_extensions import Annotated

from fastapi import Depends, Request
from fastapi.datastructures import FormData
from OpenSSL import crypto

from core.exception import AlertCloseException
from core.settings import settings
from lib.certificate.base import CertificateBase, create_cert_unique_id, post_request
from service import BaseService
from service.certificate_service import CertificateService

KCP_TEST_KEY_PATH = 'lib/certificate/kcp/hp/key/test/splPrikeyPKCS8.pem'
KCP_TEST_CERT_PATH = 'lib/certificate/kcp/hp/key/test/splCert.pem'


class KcpHpService(CertificateBase, BaseService):
    """KCP 휴대폰인증 서비스를 위한 클래스입니다."""
    CERT_URL_TEST = "https://stg-spl.kcp.co.kr/std/certpass"
    CERT_URL_PRODUCT = "https://spl.kcp.co.kr/std/certpass"

    REQUEST_PAGE_URL_TEST = "https://testcert.kcp.co.kr/kcp_cert/cert_view.jsp"
    REQUEST_PAGE_URL_PRODUCT = "https://cert.kcp.co.kr/kcp_cert/cert_view.jsp"

    KCP_SITE_CD_PREFIX = 'SM'
    KCP_TEST_SITE_CD = 'AO0QE'

    def __init__(
        self,
        request: Request,
        cert_service: Annotated[CertificateService, Depends()],
    ) -> None:
        self.request = request
        self.config = request.state.config
        self.cert_service = cert_service

    def raise_exception(self, status_code: int, detail: str = None):
        raise AlertCloseException(status_code=status_code, detail=detail)

    def get_site_code(self) -> str:
        """KCP 본인인증을 위한 site_cd를 반환합니다."""
        if self.cert_service.cert_use == 2:
            code = getattr(self.config, 'cf_cert_kcp_cd', '')
            return f"{self.KCP_SITE_CD_PREFIX}{code}"
        return self.KCP_TEST_SITE_CD

    def get_cert_url(self) -> str:
        """KCP 인증요청 처리 URL을 반환합니다."""
        if self.cert_service.cert_use == 2:
            return self.CERT_URL_PRODUCT
        return self.CERT_URL_TEST

    def get_request_cert_page_url(self) -> str:
        """KCP 휴대폰 인증 페이지를 요청할 URL을 반환합니다."""
        if self.cert_service.cert_use == 2:
            return self.REQUEST_PAGE_URL_PRODUCT
        return self.REQUEST_PAGE_URL_TEST

    async def get_request_data(self, **kwargs) -> dict:
        """KCP 휴대폰인증 창을 띄우기 위한 데이터를 반환합니다."""
        site_cd = self.get_site_code()
        ct_type = "HAS"
        make_req_dt = datetime.now().strftime("%y%m%d%H%M%S")
        ordr_idxx = create_cert_unique_id()
        web_siteid = kwargs.get('web_siteid', '')

        # 본인인증 up_hash 생성 요청
        req_data = {
            # 상점정보
            'site_cd' : site_cd,
            'kcp_cert_info' : await self.fetch_kcp_cert_info(),
            'ordr_idxx' : ordr_idxx,
            # 등록 요청정보
            'ct_type' : 'HAS',
            # 해쉬 생성 요청정보
            'web_siteid': web_siteid,
            'make_req_dt': make_req_dt,
            'kcp_sign_data': self.make_sign_data(f"{site_cd}^{ct_type}^{make_req_dt}")
        }
        result_data = await post_request(self.get_cert_url(), req_data)
        if result_data.get('res_cd') != '0000':
            self.raise_exception(500, result_data.get('res_msg'))

        return {
            "site_cd": site_cd,
            "ordr_idxx": ordr_idxx,
            "req_tx": "cert",
            "cert_method": "01",
            "up_hash": result_data.get('up_hash'),
            "cert_otp_use": "Y",  # Y : 실명 확인 + OTP 점유 확인 , N : 실명 확인 only
            "web_siteid_hashYN": "Y" if web_siteid else "",
            "web_siteid": web_siteid,
            # 가맹점 사용 필드 (인증완료시 리턴)
            "param_opt_1": "",
            "param_opt_2": "",
            "param_opt_3": "",
            "Ret_URL": kwargs.get('result_url'),
            # 리턴 암호화 고도화
            "cert_enc_use_ext": "Y",
            "kcp_merchant_time": result_data.get('kcp_merchant_time'),
            "kcp_cert_lib_ver": result_data.get('kcp_cert_lib_ver'),
            # 페이지 전환 방식 사용여부
            "kcp_page_submit_yn": "",
        }

    async def get_result_data(self, response: FormData) -> dict:
        """KCP 본인인증 결과 데이터를 반환합니다."""
        # 인증응답 데이터
        site_cd = response.get('site_cd')
        cert_no = response.get('cert_no')
        dn_hash = response.get('dn_hash')
        ordr_idxx = response.get('ordr_idxx')  # dn_hash 검증 요청 전 가맹점 DB상의 주문번호와 동일한지 검증 후 요청 바랍니다.
        enc_cert_data2 = response.get('enc_cert_data2')

        g_conf_cert_url = self.get_cert_url()
        g_conf_cert_info = await self.fetch_kcp_cert_info()

        # dn_hash 검증
        ct_type = "CHK"
        dnhash_data = f"{site_cd}^{ct_type}^{cert_no}^{dn_hash}"  #dn_hash 검증 서명 데이터
        kcp_sign_data = self.make_sign_data(dnhash_data)
        req_data = {
            'kcp_cert_info' : g_conf_cert_info,
            'site_cd': site_cd,
            'ordr_idxx': ordr_idxx,
            'cert_no': cert_no,
            'dn_hash': dn_hash,
            'ct_type': ct_type,
            'kcp_sign_data': kcp_sign_data
        }
        dn_result_data = await post_request(g_conf_cert_url, req_data)
        if dn_result_data.get('res_cd') != '0000':
            self.raise_exception(500, "dn_hash 변조 위험있음")

        # 본인인증 결과 조회
        ct_type = "DEC"
        decrypt_data = site_cd + "^" + ct_type + "^" + cert_no  # 데이터 복호화 검증 서명 데이터
        kcp_sign_data = self.make_sign_data(decrypt_data)
        req_data = {
            'kcp_cert_info' : g_conf_cert_info,
            'site_cd': site_cd,
            'ordr_idxx': ordr_idxx,
            'cert_no': cert_no,
            'ct_type': ct_type,
            'enc_cert_Data': enc_cert_data2,
            'kcp_sign_data': kcp_sign_data
        }
        result_data = await post_request(g_conf_cert_url, req_data)

        return {
            "cert_no": cert_no,
            "ci": result_data.get('ci', ''),
            "user_name": result_data.get('user_name', ''),
            "user_phone": result_data.get('phone_no', ''),
            "user_birthday": result_data.get('birth_day', ''),
        }

    def make_sign_data(self, org_data: str) -> str:
        """
        서명데이터 생성 (kcp 휴대폰 인증)
        - 무결성 검증
        """
        cert_use = self.cert_service.cert_use
        key_path = settings.KCP_KEY_PATH if cert_use == 2 else KCP_TEST_KEY_PATH
        if not os.path.exists(key_path):
            self.raise_exception(400, "KCP 개인키 경로가 설정되지 않았습니다.")

        # 개인키 READ
        with open(key_path, 'r', encoding="UTF-8") as key_file:
            key = key_file.read()

        # "changeit" 은 테스트용 개인키비밀번호
        password = 'changeit'.encode('utf-8')
        pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key, password)

        # 서명데이터생성
        sign = crypto.sign(pkey, org_data, 'sha256')
        return base64.b64encode(sign).decode()

    async def fetch_kcp_cert_info(self):
        """KCP 서비스인증서 파일 조회"""
        cert_use = self.cert_service.cert_use
        cert_path = settings.KCP_CERT_PATH if cert_use == 2 else KCP_TEST_CERT_PATH
        if not os.path.exists(cert_path):
            self.raise_exception(400, "KCP 서비스인증서 경로가 설정되지 않았습니다.")

        with open(cert_path, 'r', encoding="UTF-8") as cert_file:
            return cert_file.read().replace('\n', '')
