"""본인인증 Template Router"""
from dataclasses import dataclass
from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.templating import Jinja2Templates
from typing_extensions import Annotated

from core.models import Member
from lib.certificate.base import CertificateBase, create_result_url
from lib.common import hashing_md5
from lib.dependency.dependencies import get_certificate_class, validate_certificate_limit
from lib.dependency.auth import get_login_member_optional
from service.certificate_service import CertificateService

router = APIRouter()
templates = Jinja2Templates(directory="lib/certificate")


@dataclass
class CertificatePageRequest:
    """본인인증 페이지 요청 데이터"""
    provider: str = Path()
    cert_type: str = Path()
    page_type: str = Path()
    direct_agency: str = Query("")
    web_siteid: str = Query("")


@router.get("/certificate/{provider}/{cert_type}/{page_type}",
            dependencies=[Depends(validate_certificate_limit)])
async def get_certificate(
    request: Request,
    provider_class: Annotated[CertificateBase, Depends(get_certificate_class)],
    data: Annotated[CertificatePageRequest, Depends()]
    # provider: Annotated[str, Path()],
    # cert_type: Annotated[str, Path()],
    # page_type: Annotated[str, Path()],
    # direct_agency: Annotated[str, Query()] = "",
    # web_siteid: Annotated[str, Query()] = ""
):
    """
    본인인증 페이지 요청
    """
    data_dict = data.__dict__

    # 결과 URL
    result_url = create_result_url(request, 'result_certificate', **data_dict)
    data_dict.update({"result_url": result_url})

    context = {
        "request": request,
        "request_url": provider_class.get_request_cert_page_url(),
        "request_form": await provider_class.get_request_data(**data_dict)
    }
    return templates.TemplateResponse(f"/{data.provider}/{data.cert_type}/request.html", context)


@router.post("/certificate/{provider}/{cert_type}/{page_type}/result",
             dependencies=[Depends(validate_certificate_limit)])
async def result_certificate(
    request: Request,
    cert_service: Annotated[CertificateService, Depends()],
    provider_class: Annotated[CertificateBase, Depends(get_certificate_class)],
    member: Annotated[Member, Depends(get_login_member_optional)],
    provider: Annotated[str, Path()],
    cert_type: Annotated[str, Path()],
    page_type: Annotated[str, Path()]
):
    """
    본인인증 요청 결과 처리
    """
    mb_id = getattr(member, "mb_id", "")
    result_data = await provider_class.get_result_data(await request.form())

    cert_no = result_data.get('cert_no')
    ci = result_data.get('ci')
    user_name = result_data.get('user_name')
    user_phone = result_data.get('user_phone')
    user_birthday = result_data.get('user_birth')

    # 인증정보 생성 및 검증
    dupinfo = hashing_md5(f"{ci}{ci}")
    if page_type == "register":
        cert_service.validate_exists_dupinfo(dupinfo, mb_id)

    # 성인인증 결과
    is_adult = cert_service.get_is_adult(user_birthday)

    # 결과 데이터 md5 해싱
    md5_cert_no = hashing_md5(cert_no)
    hash_data   = cert_service.hasing_cert_hash(user_name, cert_type,
                                                user_birthday, md5_cert_no, user_phone)
    # 세션 저장
    request.session["ss_cert_type"] = cert_type
    request.session["ss_cert_no"] = md5_cert_no
    request.session["ss_cert_hash"] = hash_data
    request.session["ss_cert_adult"] = is_adult
    request.session["ss_cert_birth"] = user_birthday
    request.session['ss_cert_dupinfo'] = dupinfo

    # 인증 결과 이력 생성
    cert_service.create_cert_history(provider, cert_type, mb_id)

    # ID/PW 찾기
    if page_type == "find":
        context = {
            "request": request,
            "user_name": user_name,
            "dupinfo": dupinfo,
        }
        return templates.TemplateResponse(f"/{provider}/{cert_type}/find_result.html", context)

    # 회원가입
    context = {
        "request": request,
        "cert_type": cert_type,
        "md5_cert_no": md5_cert_no,
        "user_name": user_name,
        "user_phone": user_phone,
    }
    return templates.TemplateResponse(f"/{provider}/{cert_type}/result.html", context)
