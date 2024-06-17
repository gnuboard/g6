"""API 본인인증 관련 기능 구현 모듈"""
from fastapi import HTTPException

from lib.certificate.inicis.simple.inicis_simple_service import InicisSimpleService
from lib.certificate.kcp.hp.kcp_hp_service import KcpHpService
from service.certificate_service import CertificateService


class CertificateServiceAPI(CertificateService):
    """
    API 요청에 사용되는 CertificateService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class InicisSimpleServiceAPI(InicisSimpleService):
    """
    API 요청에 사용되는 InicisSimpleService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class KcpHpServiceAPI(KcpHpService):
    """
    API 요청에 사용되는 KcpHpService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
