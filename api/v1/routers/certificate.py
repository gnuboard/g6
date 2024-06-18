"""본인인증 API Router"""
from enum import Enum
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from api.v1.dependencies.certificate import get_certificate_class
from api.v1.dependencies.certificate import validate_certificate_limit
from api.v1.models.certificate import CertificatePageRequest, CertificatePageResponse
from api.v1.models.response import response_404, response_422
from lib.certificate.base import CertificateBase, create_result_url

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
             dependencies=[Depends(validate_certificate_limit)])
async def result_certificate_api():
    """
    본인인증 요청 결과 처리
    """
    pass
