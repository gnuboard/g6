"""본인인증 Template Router"""
from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.templating import Jinja2Templates
from typing_extensions import Annotated

from core.models import Member
from lib.certificate.base import CertificateBase
from lib.dependency.dependencies import get_certificate_class, validate_certificate_limit
from lib.dependency.auth import get_login_member_optional
from service.certificate_service import CertificateService

router = APIRouter()
templates = Jinja2Templates(directory="lib/certificate")


@router.get("/certificate/{provider}/{cert_type}",
            dependencies=[Depends(validate_certificate_limit)])
async def get_certificate(
    request: Request,
    cert_service: Annotated[CertificateService, Depends()],
    provider_class: Annotated[CertificateBase, Depends(get_certificate_class)],
    provider: Annotated[str, Path()],
    cert_type: Annotated[str, Path()],
    page_type: Annotated[str, Query(alias="pageType")] = None
):
    """
    본인인증 페이지 요청
    """
    request_data = await provider_class.get_request_data()
    context = {"request": request}
    context.update(request_data)
    context.update({
        "cert_use": cert_service.cert_use,
        "page_type": page_type
    })
    return templates.TemplateResponse(f"/{provider}/{cert_type}/request.html", context)


@router.post("/certificate/{provider}/{cert_type}/result",
             dependencies=[Depends(validate_certificate_limit)])
async def result_certificate(
    request: Request,
    cert_service: Annotated[CertificateService, Depends()],
    provider_class: Annotated[CertificateBase, Depends(get_certificate_class)],
    member: Annotated[Member, Depends(get_login_member_optional)],
    provider: Annotated[str, Path()],
    cert_type: Annotated[str, Path()],
    page_type: Annotated[str, Query(alias="pageType")] = None
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
    dupinfo = cert_service.create_dupinfo(f"{ci}{ci}")
    if page_type == "register":
        cert_service.validate_exists_dupinfo(dupinfo, mb_id)

    # 성인인증 결과
    is_adult = cert_service.get_is_adult(user_birthday)

    # 결과 데이터 md5 해싱
    md5_cert_no = cert_service.hashing_md5(cert_no)
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

    # ID 찾기
    if page_type == "find_id":
        context = {
            "request": request,
            "user_name": user_name,
            "dupinfo": dupinfo,
        }
        return templates.TemplateResponse(f"/{provider}/{cert_type}/id_find_result.html", context)

    # PW 찾기
    elif page_type == "find_pw":
        pass

    # 회원가입
    context = {
        "request": request,
        "cert_type": cert_type,
        "md5_cert_no": md5_cert_no,
        "user_name": user_name,
        "user_phone": user_phone,
    }
    return templates.TemplateResponse(f"/{provider}/{cert_type}/result.html", context)
