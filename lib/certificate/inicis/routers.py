"""본인인증 Template Router"""
import hashlib

from typing_extensions import Annotated

from fastapi import APIRouter, Path, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="lib/certificate")


@router.get("/certificate/{cert_type}")
async def get_certificate(
    request: Request,
    cert_type: Annotated[str, Path()]
):
    """
    본인인증 페이지
    """
    mid = 'INIiasTest'
    api_key = 'TGdxb2l3enJDWFRTbTgvREU3MGYwUT09'
    m_tx_id ='test_20230327'
    req_svc_cd ='01'
    identifier = '테스트 서명'
    user_name = ''
    user_phone = ''
    user_birth =''

    context = {
        "request": request,
        "mid": mid,
        "api_key": api_key,
        "m_tx_id": m_tx_id,
        "req_svc_cd": req_svc_cd,
        "identifier": identifier,
        "user_name": user_name,
        "user_phone": user_phone,
        "user_birth": user_birth,
        "auth_hash": _hashing_inicis(f"{mid}{m_tx_id}{api_key}"),
        "user_hash": _hashing_inicis(f"{user_name}{mid}{user_phone}{m_tx_id}{user_birth}{req_svc_cd}"),
    }
    return templates.TemplateResponse(f"/{cert_type}/request.html", context)


def _hashing_inicis(string: str) -> str:
    return hashlib.sha256(string.encode()).hexdigest()
