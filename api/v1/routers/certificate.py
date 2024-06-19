"""본인인증 API Router"""
from enum import Enum
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from api.v1.dependencies.certificate import get_certificate_class
from api.v1.dependencies.certificate import validate_certificate_limit
from api.v1.dependencies.member import get_current_member_optional
from api.v1.models.certificate import (
    CertificatePageRequest, CertificatePageResponse, CertificateRequest
)
from api.v1.models.response import response_404, response_422
from api.v1.service.certificate import CertificateServiceAPI
from core.models import Member
from lib.certificate.base import CertificateBase, create_result_url
from lib.common import hashing_md5

router = APIRouter()


@router.get("/certificate/{provider}/{cert_type}/{page_type}",
            summary="본인인증 페이지 요청 데이터 조회",
            dependencies=[Depends(validate_certificate_limit)],
            responses={**response_404, **response_422})
async def get_certificate_api(
    request: Request,
    provider_class: Annotated[CertificateBase, Depends(get_certificate_class)],
    data: Annotated[CertificatePageRequest, Depends()],
) -> CertificatePageResponse:
    """
    본인인증 페이지 요청
    """
    data_dict = {}
    for key, value in data.__dict__.items():
        if isinstance(value, Enum):
            data_dict[key] = value.value
        else:
            data_dict[key] = value

    # 결과 URL
    result_url = create_result_url(request, 'result_certificate_api', **data_dict)
    data_dict.update({"result_url": result_url})

    return CertificatePageResponse(
        request_url=provider_class.get_request_cert_page_url(),
        request_form=await provider_class.get_request_data(**data_dict)
    )


@router.post("/certificate/{provider}/{cert_type}/{page_type}/result",
             summary="본인인증 결과 데이터 처리",
             dependencies=[Depends(validate_certificate_limit)],
             include_in_schema=False
             )
async def result_certificate_api(
    request: Request,
    cert_service: Annotated[CertificateServiceAPI, Depends()],
    provider_class: Annotated[CertificateBase, Depends(get_certificate_class)],
    member: Annotated[Member, Depends(get_current_member_optional)],
    data: Annotated[CertificateRequest, Depends()],
):
    """
    본인인증 결과 데이터를 처리하여 인증정보를 반환합니다.
    - PG사의 본인인증 처리를 통해 데이터를 통해 인증정보를 반환합니다.
    - 인증정보를 회원가입시 Request Body 로 그대로 전달합니다.

    * 이 API는 PG사에서 요청하는 Callback URL 로 사용되기 때문에
    * API 문서에는 노출되지 않습니다.
    """
    provider = data.provider.value
    cert_type = data.cert_type.value
    page_type = data.page_type.value

    mb_id = getattr(member, "mb_id", "")
    result_data = await provider_class.get_result_data(await request.form())

    cert_no = result_data.get('cert_no')
    ci = result_data.get('ci')
    user_name = result_data.get('user_name', '')
    user_phone = result_data.get('user_phone', '')
    user_birthday = result_data.get('user_birth', '')

    # 인증정보 생성 및 검증
    dupinfo = hashing_md5(f"{ci}{ci}")
    if page_type == "register":
        cert_service.validate_exists_dupinfo(dupinfo, mb_id)

    # 성인인증 결과
    is_adult = cert_service.get_is_adult(user_birthday)

    # 결과 데이터 md5 해싱
    md5_cert_no = hashing_md5(cert_no)
    hash_data   = cert_service.hasing_cert_hash(
        user_name, cert_type, md5_cert_no, user_birthday, user_phone)

    # 인증 결과 이력 생성
    cert_service.create_cert_history(provider, cert_type, mb_id)

    return {
        "cert_type": cert_type,
        "cert_no": md5_cert_no,
        "cert_hash": hash_data,
        "cert_adult": is_adult,
        "cert_dupinfo": dupinfo,
        "cert_user_name": user_name,
        "cert_user_phone": user_phone,
        "cert_user_birthday": user_birthday,
    }
