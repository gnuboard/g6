"""본인인증 Template Router"""
from datetime import date, timedelta
import hashlib
import httpx
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.templating import Jinja2Templates

from core.database import db_session
from core.exception import AlertCloseException
from core.models import Member
from lib.dependency.auth import get_login_member_optional
from service.member_service import MemberService

router = APIRouter()
templates = Jinja2Templates(directory="lib/certificate")

MID = 'INIiasTest'
IV = 'SASKGINICIS00000'


@router.get("/certificate/{cert_type}")
async def get_certificate(
    request: Request,
    cert_type: Annotated[str, Path()]
):
    """
    본인인증 페이지
    """
    api_key = 'TGdxb2l3enJDWFRTbTgvREU3MGYwUT09'
    m_tx_id ='test_20230327'
    req_svc_cd ='01'
    identifier = '테스트 서명'
    user_name = ''
    user_phone = ''
    user_birth =''

    context = {
        "request": request,
        "mid": MID,
        "api_key": api_key,
        "m_tx_id": m_tx_id,
        "req_svc_cd": req_svc_cd,
        "identifier": identifier,
        "user_name": user_name,
        "user_phone": user_phone,
        "user_birth": user_birth,
        "auth_hash": _hashing_sha256(f"{MID}{m_tx_id}{api_key}"),
        "user_hash": _hashing_sha256(
            f"{user_name}{MID}{user_phone}{m_tx_id}{user_birth}{req_svc_cd}"),
    }
    return templates.TemplateResponse(f"/{cert_type}/request.html", context)


@router.post("/certificate/{cert_type}/result")
async def result_certificate(
    request: Request,
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    cert_type: Annotated[str, Path()],
    result_code: Annotated[str, Form(alias="resultCode")],
    result_msg: Annotated[str, Form(alias="resultMsg")],
    auth_request_url: Annotated[str, Form(alias="authRequestUrl")] = None,
    tx_id: Annotated[str, Form(alias="txId")] = None,
    token: Annotated[str, Form(alias="token")] = '',
):
    mb_id = getattr(member, "mb_id", "")

    if result_code != "0000":
        raise AlertCloseException(result_msg)

    if not (auth_request_url.startswith("https://kssa.inicis.com")
            or auth_request_url.startswith("https://fcsa.inicis.com")):
        raise AlertCloseException("올바르지 않은 인증요청 URL입니다.")

    try:
        data = {
            'mid': MID,
            'txId': tx_id
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=auth_request_url,
                json=data,
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                timeout=5.0,
            )
        result_data: dict = response.json()
        print("result_data", result_data)

        if result_data['resultCode'] != '0000':
            raise AlertCloseException(result_data['resultMsg'])

        # 결과 데이터
        cert_no: str = result_data.get('txId')
        ci: str = result_data.get('userCi', '')
        user_name: str = result_data.get('userName', '')
        user_phone: str = result_data.get('userPhone', '')
        user_birthday: str = result_data.get('userBirth', '')

        # 본인인증 결과 검증
        if not user_phone:
            raise AlertCloseException("핸드폰 번호가 없습니다. 본인인증에 실패하였습니다.")

        dupinfo = _hashing_md5(f"{ci}{ci}")
        mb_certify = getattr(member, "mb_certify", "")
        mb_dupinfo = getattr(member, "mb_dupinfo", "")
        if (mb_certify and len(mb_dupinfo) != 64 and mb_dupinfo != dupinfo):
            raise AlertCloseException("해당 계정은 이미 다른명의로 본인인증 되어있는 계정입니다.")

        exists_member = member_service.fetch_member_by_dupinfo(mb_id, dupinfo)
        if exists_member:
            raise AlertCloseException(f"입력하신 본인확인 정보로 이미 가입된 내역이 존재합니다.\
                                        \\n아이디 : {exists_member.mb_id}")
        # 결과 데이터 md5 해싱
        md5_cert_no = _hashing_md5(cert_no)
        hash_data   = _hashing_md5(f"{user_name}{cert_type}{user_birthday}{user_phone}{md5_cert_no}")

        # 성인인증결과
        # 19년전 오늘날짜 계산
        ago_19years = date.today() - timedelta(days=19*365)
        # TODO: 복호화가 안됬으므로 임시 데이터 삽입
        # KISA에서 제공하는 SEED 암호화(CBC)에는 파이썬 버전이 없다..
        # user_birthday = date.fromisoformat(user_birthday)
        user_birthday = date.today().strftime("%Y-%m-%d")
        is_adult = 1 if date.today() <= ago_19years else 0

        request.session["ss_cert_type"] = cert_type
        request.session["ss_cert_no"] = md5_cert_no
        request.session["ss_cert_hash"] = hash_data
        request.session["ss_cert_adult"] = is_adult
        request.session["ss_cert_birth"] = user_birthday
        request.session['ss_cert_dupinfo'] = mb_dupinfo

        context = {
            "request": request,
            "cert_type": cert_type,
            "md5_cert_no": md5_cert_no,
            "user_name": user_name,
            "user_phone": user_phone,
        }
        return templates.TemplateResponse(f"/{cert_type}/result.html", context)

    except Exception as e:
        raise AlertCloseException(f"인증 결과를 가져오는 중 오류가 발생했습니다.\n{e}") from e


def _hashing_sha256(string: str) -> str:
    return hashlib.sha256(string.encode()).hexdigest()


def _hashing_md5(string: str) -> str:
    return hashlib.md5(string.encode()).hexdigest()
