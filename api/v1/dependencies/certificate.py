"""본인인증 관련 의존성 함수를 정의합니다."""
from fastapi import Depends, HTTPException, Path
from typing_extensions import Annotated

from api.v1.dependencies.member import get_current_member_optional
from api.v1.models.certificate import CertificatePageRequest
from api.v1.service.certificate import (
    CertificateServiceAPI, InicisSimpleServiceAPI, KcpHpServiceAPI
)
from core.models import Member


def get_certificate_class(
    inicis_simple_service: Annotated[InicisSimpleServiceAPI, Depends()],
    kcp_hp_service: Annotated[KcpHpServiceAPI, Depends()],
    data: Annotated[CertificatePageRequest, Depends()],
):
    """
    본인인증 서비스를 제공하는 클래스를 반환합니다.
    """
    provider = data.provider.value
    cert_type = data.cert_type.value

    if provider == "inicis" and cert_type == "simple":
        return inicis_simple_service
    if provider == "kcp" and cert_type == "hp":
        return kcp_hp_service

    raise HTTPException(404, "Unsupported service type")


def validate_certificate_limit(
    member: Annotated[Member, Depends(get_current_member_optional)],
    cert_service: Annotated[CertificateServiceAPI, Depends()],
    cert_type: Annotated[str, Path()],
) -> None:
    """
    본인인증 횟수 제한 검사
    """
    mb_id = getattr(member, "mb_id", "")
    cert_service.validate_certificate_limit(mb_id, cert_type)
