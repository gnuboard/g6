"""본인인증 Template Router"""
import base64
import hashlib
import json
from datetime import date, datetime, timedelta

import httpx
from OpenSSL import crypto
from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.templating import Jinja2Templates
from typing_extensions import Annotated

from core.database import db_session
from core.exception import AlertCloseException
from core.models import Member
from lib.dependency.auth import get_login_member_optional
from service.member_service import MemberService

router = APIRouter()
templates = Jinja2Templates(directory="lib/certificate")

MID = 'INIiasTest'
IV = 'SASKGINICIS00000'


@router.get("/certificate/{service}/{cert_type}")
async def get_certificate(
    request: Request,
    service: Annotated[str, Path()],
    cert_type: Annotated[str, Path()],
):
    """
    본인인증 페이지
    """
    if service == "inicis" and cert_type == "simple":
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

    elif service == "kcp" and cert_type == "hp":
        site_cd = 'AO0QE'
        ct_type = 'HAS'
        make_req_dt = datetime.now().strftime("%y%m%d%H%M%S")

        hash_data = f"{site_cd}^{ct_type}^{make_req_dt}"
        kcp_sign_data = make_sign_data(hash_data)

        # 본인인증 up_hash 생성 API URL
        g_conf_cert_url = "https://stg-spl.kcp.co.kr/std/certpass"
        # g_conf_cert_url = https://spl.kcp.co.kr/std/certpass  # 운영계
        key_path = 'lib/certificate/kcp/hp/key/splCert.pem'

        with open(key_path, 'r', encoding="UTF-8") as cert_file:
            g_conf_cert_info = cert_file.read().replace('\n', '')

        # up_hash 생성 REQ DATA
        req_data = {
            'site_cd' : site_cd,
            'ct_type' : ct_type,
            'make_req_dt' : make_req_dt,
            'kcp_cert_info' : g_conf_cert_info,
            'ordr_idxx' : 'test_orderid',
            'web_siteid' : '',
            'kcp_sign_data' : kcp_sign_data
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=g_conf_cert_url,
                json=req_data,
                headers={
                    'charset': 'UTF-8',
                    'Content-Type': 'application/json'
                },
                timeout=5.0,
            )
            result_data: dict = response.json()

        if result_data.get('res_cd') != '0000':
            raise AlertCloseException(result_data.res_msg)

        result_data.update(req_data)
        context = {
            "request": request,
            # "res_data": result_data,
            # "req_data": req_data
            "res_data": result_data
        }
        print(result_data)

        sb_param_data = {
            "ordr_idxx": result_data.get('ordr_idxx'),
            "up_hash": result_data.get('up_hash'),
            # 요청종류
            "req_tx": "cert",
            # 요청구분
            "cert_method": "01",
            "web_siteid": result_data.get('web_siteid'),
            "site_cd": result_data.get('site_cd'),
            "Ret_URL": str(request.url_for('result_certificate_kcp_hp')),  # 리턴 URL
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

        context = {
            "request": request,
            "sb_param": json.dumps(sb_param_data, ensure_ascii=False),
        }

    return templates.TemplateResponse(f"/{service}/{cert_type}/request.html", context)


@router.post("/certificate/inicis/simple/result")
async def result_certificate_inicis_simple(
    request: Request,
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    result_code: Annotated[str, Form(alias="resultCode")],
    result_msg: Annotated[str, Form(alias="resultMsg")],
    auth_request_url: Annotated[str, Form(alias="authRequestUrl")] = None,
    tx_id: Annotated[str, Form(alias="txId")] = None,
    token: Annotated[str, Form(alias="token")] = '',
):
    mb_id = getattr(member, "mb_id", "")
    cert_type = "simple"

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
        request.session['ss_cert_dupinfo'] = dupinfo

        context = {
            "request": request,
            "cert_type": cert_type,
            "md5_cert_no": md5_cert_no,
            "user_name": user_name,
            "user_phone": user_phone,
        }
        return templates.TemplateResponse("/inicis/simple/result.html", context)

    except Exception as e:
        raise AlertCloseException(f"인증 결과를 가져오는 중 오류가 발생했습니다.\n{e}") from e


@router.post("/certificate/kcp/hp/result")
async def result_certificate_kcp_hp(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    site_cd: Annotated[str, Form()],
    cert_no: Annotated[str, Form()],
    dn_hash: Annotated[str, Form()],  # dn_hash 검증 요청 전 가맹점 DB상의 주문번호와 동일한지 검증 후 요청 바랍니다.
    ordr_idxx: Annotated[str, Form()],
    enc_cert_data2: Annotated[str, Form()],
):
    mb_id = getattr(member, "mb_id", "")
    cert_type = "hp"

    g_conf_cert_url = "https://stg-spl.kcp.co.kr/std/certpass"
    # g_conf_cert_url = https://spl.kcp.co.kr/std/certpass  # 운영계
    headers = {'Content-Type': 'application/json', 'charset': 'UTF-8'}
    ct_type = "CHK"
    # sb_param_data = f_get_parm(request.form)

    dnhash_data = site_cd + "^" + ct_type + "^" + cert_no + "^" + dn_hash  #dn_hash 검증 서명 데이터
    kcp_sign_data = make_sign_data(dnhash_data)  #서명 데이터(무결성 검증)

    key_path = 'lib/certificate/kcp/hp/key/splCert.pem'
    with open(key_path, 'r', encoding="UTF-8") as cert_file:
        g_conf_cert_info = cert_file.read().replace('\n', '')

    req_data = {
        'kcp_cert_info' : g_conf_cert_info,
        'site_cd': site_cd,
        'ordr_idxx': ordr_idxx,
        'cert_no': cert_no,
        'dn_hash': dn_hash,
        'ct_type': ct_type,
        'kcp_sign_data': kcp_sign_data
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=g_conf_cert_url,
            json=req_data,
            headers=headers,
            timeout=5.0,
        )
        dn_result_data: dict = response.json()
        dn_res_cd = dn_result_data.get('res_cd')

    if dn_res_cd != '0000':
        raise AlertCloseException("dn_hash 변조 위험있음")

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
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=g_conf_cert_url,
            json=req_data,
            headers=headers,
            timeout=5.0,
        )
        result_data: dict = response.json()

    user_name = result_data.get('user_name')
    birth_day = result_data.get('birth_day')
    phone_no = result_data.get('phone_no')
    ci = result_data.get('ci')
    md5_cert_no = _hashing_md5(cert_no)
    hash_data = _hashing_md5(f"{user_name}{cert_type}{birth_day}{phone_no}{md5_cert_no}")


    # 성인인증결과
    ago_19years = date.today() - timedelta(days=19*365)  # 19년전 오늘날짜 계산
    birth_day_date = datetime.strptime(birth_day, "%Y%m%d").date()
    is_adult = 1 if birth_day_date <= ago_19years else 0


    dupinfo = _hashing_md5(f"{ci}{ci}")
    mb_certify = getattr(member, "mb_certify", "")
    mb_dupinfo = getattr(member, "mb_dupinfo", "")
    if (mb_certify and len(mb_dupinfo) != 64 and mb_dupinfo != dupinfo):
        raise AlertCloseException("해당 계정은 이미 다른명의로 본인인증 되어있는 계정입니다.")

    exists_member = member_service.fetch_member_by_dupinfo(mb_id, dupinfo)
    if exists_member:
        raise AlertCloseException(f"입력하신 본인확인 정보로 이미 가입된 내역이 존재합니다.\
                                    \\n아이디 : {exists_member.mb_id}")

    request.session["ss_cert_type"] = cert_type
    request.session["ss_cert_no"] = md5_cert_no
    request.session["ss_cert_hash"] = hash_data
    request.session["ss_cert_adult"] = is_adult
    request.session["ss_cert_birth"] = birth_day
    request.session['ss_cert_dupinfo'] = dupinfo

    print(result_data)

    context = {
        "request": request,
        "res_data": result_data,
        "sb_param": await request.form(),
        "md5_cert_no": md5_cert_no
    }
    return templates.TemplateResponse("/kcp/hp/result.html", context)


def _hashing_sha256(string: str) -> str:
    return hashlib.sha256(string.encode()).hexdigest()


def _hashing_md5(string: str) -> str:
    return hashlib.md5(string.encode()).hexdigest()


def make_sign_data(orgData: str) -> str:
    """
    서명데이터 생성 (kcp 휴대폰 인증)
    """
    # 개인키 READ``
    # "splPrikeyPKCS8.pem" 은 테스트용 개인키
    with open('lib/certificate/kcp/hp/key/splPrikeyPKCS8.pem', 'r', encoding="UTF-8") as key_file:
        key = key_file.read()

    # "changeit" 은 테스트용 개인키비밀번호
    password = 'changeit'.encode('utf-8')
    pkey = crypto.load_privatekey(crypto.FILETYPE_PEM, key, password)

    # 서명데이터생성
    sign = crypto.sign(pkey, orgData, 'sha256')
    kcp_sign_data = base64.b64encode(sign).decode()

    return kcp_sign_data
