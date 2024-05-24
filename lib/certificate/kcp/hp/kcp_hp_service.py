"""KCP 휴대폰인증 서비스를 위한 클래스를 정의합니다."""
import base64
import json
from datetime import datetime
from typing_extensions import Annotated

from OpenSSL import crypto
from fastapi import Depends, Request
from fastapi.datastructures import FormData

from core.exception import AlertCloseException
from lib.certificate.base import CertificateBase, post_request
from service import BaseService
from service.certificate_service import CertificateService

KCP_KEY_PATH = 'lib/certificate/kcp/hp/key/splPrikeyPKCS8.pem'
KCP_CERT_PATH = 'lib/certificate/kcp/hp/key/splCert.pem'


class KcpHpService(CertificateBase, BaseService):
    """KCP 휴대폰인증 서비스를 위한 클래스입니다."""
    CERT_URL_TEST = "https://stg-spl.kcp.co.kr/std/certpass"
    CERT_URL_PRODUCT = "https://spl.kcp.co.kr/std/certpass"

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

    def get_cert_url(self) -> str:
        """KCP 인증요청 처리 URL을 반환합니다."""
        if self.config.cf_cert_use == 2:
            return self.CERT_URL_PRODUCT
        return self.CERT_URL_TEST

    async def get_request_data(self) -> dict:
        """KCP 휴대폰인증 창을 띄우기 위한 데이터를 반환합니다."""
        site_cd = self.cert_service.get_kcp_site_code()
        ct_type = 'HAS'
        make_req_dt = datetime.now().strftime("%y%m%d%H%M%S")

        hash_data = f"{site_cd}^{ct_type}^{make_req_dt}"
        kcp_sign_data = make_sign_data(hash_data)

        # 본인인증 up_hash 생성 요청
        cert_url = self.get_cert_url()
        cert_info = await fetch_kcp_cert_info()
        req_data = {
            'site_cd' : site_cd,
            'ct_type' : ct_type,
            'make_req_dt' : make_req_dt,
            'kcp_cert_info' : cert_info,
            'ordr_idxx' : 'test_orderid',
            'web_siteid' : '',
            'kcp_sign_data' : kcp_sign_data
        }
        result_data = await post_request(cert_url, req_data)
        if result_data.get('res_cd') != '0000':
            self.raise_exception(500, result_data.get('res_msg'))

        result_data.update(req_data)

        sb_param_data = {
            "ordr_idxx": result_data.get('ordr_idxx'),
            "up_hash": result_data.get('up_hash'),
            # 요청종류
            "req_tx": "cert",
            # 요청구분
            "cert_method": "01",
            "web_siteid": result_data.get('web_siteid'),
            "site_cd": result_data.get('site_cd'),
            "Ret_URL": str(self.request.url_for('result_certificate',
                                                provider='kcp',
                                                cert_type='hp')),
            "cert_otp_use": "Y",  # Y : 실명 확인 + OTP 점유 확인 , N : 실명 확인 only
            # 리턴 암호화 고도화
            "cert_enc_use_ext": "Y",
            "res_cd": "",
            "res_msg": "",
            # web_siteid 검증 을 위한 필드
            "web_siteid_hashYN": result_data.get('web_siteid_hashYN'),
            "kcp_merchant_time": result_data.get('kcp_merchant_time'),
            "kcp_cert_lib_ver": result_data.get('kcp_cert_lib_ver'),
            # 가맹점 사용 필드 (인증완료시 리턴)
            "param_opt_1": "opt1",
            "param_opt_2": "opt2",
            "param_opt_3": "opt3",
            # 페이지 전환 방식 사용여부
            "kcp_page_submit_yn": "",
        }

        return {
            "sb_param": json.dumps(sb_param_data, ensure_ascii=False),
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
        g_conf_cert_info = await fetch_kcp_cert_info()

        # dn_hash 검증
        ct_type = "CHK"
        dnhash_data = f"{site_cd}^{ct_type}^{cert_no}^{dn_hash}"  #dn_hash 검증 서명 데이터
        kcp_sign_data = make_sign_data(dnhash_data)  #서명 데이터(무결성 검증)
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
        kcp_sign_data = make_sign_data(decrypt_data)  #서명 데이터(무결성 검증)
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


def make_sign_data(org_data: str) -> str:
    """
    서명데이터 생성 (kcp 휴대폰 인증)
    """
    # 개인키 READ``
    # "splPrikeyPKCS8.pem" 은 테스트용 개인키
    with open(KCP_KEY_PATH, 'r', encoding="UTF-8") as key_file:
        key = key_file.read()

    # "changeit" 은 테스트용 개인키비밀번호
    password = 'changeit'.encode('utf-8')
    pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key, password)

    # 서명데이터생성
    sign = crypto.sign(pkey, org_data, 'sha256')
    return base64.b64encode(sign).decode()


async def fetch_kcp_cert_info():
    """KCP 개인 인증 키 정보 조회"""
    with open(KCP_CERT_PATH, 'r', encoding="UTF-8") as cert_file:
        return cert_file.read().replace('\n', '')
