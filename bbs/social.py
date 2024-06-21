"""소셜 로그인 Template Router"""
import logging
from datetime import datetime
from uuid import uuid4

from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from typing_extensions import Annotated

from core.exception import AlertCloseException, AlertException, JSONException
from core.formclass import MemberForm, RegisterSocialMemberForm
from core.models import Config, Member
from core.template import UserTemplates
from lib.common import SOCIAL_PATH, session_member_key
from lib.dependency.auth import get_login_member
from lib.dependency.social import (
    get_auth_token_from_session, get_provider_from_query,
    get_provider_from_session, get_provider_from_link, validate_use_social_login
)
from lib.mail import send_register_mail
from lib.pbkdf2 import create_hash
from lib.social.service import SocialAuthService
from lib.social.social import (
    get_provider_client_key, get_social_login_token, get_social_profile,
    load_provider_class, oauth, register_social_provider
)
from service.member_service import MemberService, ValidateMember
from service.point_service import PointService

router = APIRouter(dependencies=[Depends(validate_use_social_login)])
templates = UserTemplates()

log = logging.getLogger("authlib")
logging.basicConfig()
log.setLevel(logging.DEBUG)


@router.get('/social/login')
async def request_social_login(
    request: Request,
    provider: Annotated[str, Depends(get_provider_from_query)],
):
    """
    소셜 로그인 인증요청 페이지
    """
    config: Config = request.state.config

    # 소셜 로그인 별 client_id, secret_key 가져오기
    client_id, secret_key = get_provider_client_key(provider, config)

    # 카카오 client_secret 은 선택사항
    if not (client_id and (secret_key or provider == 'kakao')):
        raise AlertException("소셜 로그인 설정이 등록되지 않았습니다. 관리자에게 문의하십시오.", 400)

    # 소셜 로그인 정보 등록
    register_social_provider(provider, client_id, secret_key)

    # 소셜 로그인 인증 페이지 요청
    oauth2_app: StarletteOAuth2App = getattr(oauth, provider)
    redirect_uri = f"{str(request.url_for('authorize_social_login'))}?provider={provider}"

    return await oauth2_app.authorize_redirect(request, redirect_uri.replace(":443", ""))


@router.get('/social/login/callback')
async def authorize_social_login(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    social_service: Annotated[SocialAuthService, Depends()],
    provider: Annotated[str, Depends(get_provider_from_query)],
):
    """
    소셜 로그인 인증 콜백
    """
    auth_token = await get_social_login_token(request, provider)
    if not auth_token:
        raise AlertException(status_code=400, detail="잠시후에 다시 시도해 주세요.",
                             url=request.url_for('login'))

    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)
    profile = provider_class.extract_social_profile(response)
    if not profile.identifier:
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=str(request.url_for('login')))

    # 회원정보수정 > 소셜계정 연결 (이미 로그인된 계정은 연결으로 처리)
    if request.state.login_member:
        social_profile = social_service.get_profile_by_identifier(profile.identifier, provider)
        if social_profile:
            raise AlertCloseException(
                detail=f"해당 {provider}소셜 계정은 이미 연결된 회원이 존재합니다.",
                status_code=409
            )

        member = member_service.get_member(request.state.login_member.mb_id)
        if social_service.check_exists_by_mb_id(provider, member.mb_id):
            raise AlertCloseException(
                detail=f"이미 연결된 {provider} 소셜계정이 존재합니다.",
                status_code=409
            )

        social_service.link_social_login(member.mb_id, provider, profile)

        context = {"request": request, "provider": provider}
        template = Jinja2Templates(directory=SOCIAL_PATH)
        return template.TemplateResponse("link_result.html", context)

    # 가입정보가 있을 경우 로그인 처리
    social_profile = social_service.get_profile_by_identifier(profile.identifier, provider)
    if social_profile:
        member = member_service.get_member(social_profile.mb_id)

        request.session["ss_mb_id"] = member.mb_id
        request.session["ss_mb_key"] = session_member_key(request, member)  # XSS 공격 대응
        request.session["ss_social_provider"] = provider
        return RedirectResponse(url=request.url_for('index'), status_code=302)

    # 소셜 회원가입 페이지로 이동
    request.session['ss_social_provider'] = provider
    return RedirectResponse(url=request.url_for('get_social_register_form'), status_code=302)


@router.get('/social/register')
async def get_social_register_form(
    request: Request,
    validate: Annotated[ValidateMember, Depends()],
    provider: Annotated[str, Depends(get_provider_from_session)],
    auth_token: Annotated[dict, Depends(get_auth_token_from_session)],
):
    """
    소셜 회원가입 폼
    """
    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)

    profile = provider_class.extract_social_profile(response)
    social_email = provider_class.extract_email(response)

    form_context = {
        "social_nickname": profile.displayname,
        "social_email": social_email,
        "action_url": request.url_for('post_social_register'),
        "is_exists_email": validate.is_exists_email(social_email) if social_email else False,
    }
    context = {
        "request": request,
        "form": form_context,
        "provider": provider,
    }
    return templates.TemplateResponse("/social/social_register_member.html", context)


@router.post('/social/register')
async def post_social_register(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    point_service: Annotated[PointService, Depends()],
    social_service: Annotated[SocialAuthService, Depends()],
    validate: Annotated[ValidateMember, Depends()],
    background_tasks: BackgroundTasks,
    provider: Annotated[str, Depends(get_provider_from_session)],
    auth_token: Annotated[dict, Depends(get_auth_token_from_session)],
    member_form: MemberForm = Depends(),
):
    """
    신규 소셜 회원등록
    """
    config: Config = request.state.config

    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)
    profile = provider_class.extract_social_profile(response)

    # token valid
    if not profile.identifier:
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=request.url_for('login'))

    # 소셜 아이디 검사
    gnu_social_id = social_service.g6_convert_social_id(profile.identifier, provider)
    validate.valid_id(gnu_social_id)

    # 이메일 유효성 검사
    validate.valid_email(member_form.mb_email)

    # 닉네임 유효성 검사
    mb_nick = member_form.mb_nick or gnu_social_id.split('_')[1]
    validate.valid_nickname(mb_nick)

    # 회원가입
    member_data = RegisterSocialMemberForm(
        mb_id=gnu_social_id,
        mb_password=create_hash(str(datetime.now().microsecond) + uuid4().hex),
        mb_name=mb_nick,
        mb_nick=mb_nick,
        mb_email=member_form.mb_email,
        mb_level=config.cf_register_level,
    )
    member = member_service.create_member(member_data)
    social_service.link_social_login(member.mb_id, provider, profile)

    # 회원가입 포인트 부여
    register_point = getattr(config, "cf_register_point", 0)
    point_service.save_point(member.mb_id, register_point, "회원가입 축하",
                             "@member", member.mb_id, "회원가입")

    # 회원가입메일 발송 처리(백그라운드)
    background_tasks.add_task(send_register_mail, request, member)

    return RedirectResponse(url="/", status_code=302)


@router.post('/social/register/link')
async def social_register_link(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    social_service: Annotated[SocialAuthService, Depends()],
    provider: Annotated[str, Depends(get_provider_from_session)],
    auth_token: Annotated[dict, Depends(get_auth_token_from_session)],
    mb_id: str = Form(...),
    mb_password: str = Form(...),
):
    """
    기존 회원에 소셜계정 연결
    """
    # 로그인 검증
    member = member_service.authenticate_member(mb_id, mb_password)

    # 이미 소셜계정이 연결되어 있는지 확인
    is_exists = social_service.check_exists_by_mb_id(provider, member.mb_id)
    if is_exists:
        raise AlertException(detail=f"이미 {provider} ID가 연결된 계정입니다.", status_code=400)

    # 소셜계정 연결
    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)
    profile = provider_class.extract_social_profile(response)

    social_service.link_social_login(member.mb_id, provider, profile)

    # 로그인 세션 생성
    request.session["ss_mb_id"] = member.mb_id
    request.session["ss_mb_key"] = session_member_key(request, member)

    raise AlertException(detail="소셜계정이 연결되었습니다.",
                         status_code=200,
                         url=request.url_for('index'))


@router.post('/social/unlink')
async def unlink_social_profile(
    social_service: Annotated[SocialAuthService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    provider: Annotated[str, Depends(get_provider_from_link)],
):
    """
    소셜계정 연결해제
    """
    if not social_service.check_exists_by_mb_id(provider, member.mb_id):
        raise JSONException(message="연결된 소셜계정이 없습니다.", status_code=404)

    social_service.unlink_social_login(member.mb_id, provider)
    return JSONResponse(
        {"success": True, "message": f"{provider} 계정이 연결해제 되었습니다."},
        status_code=200
    )
