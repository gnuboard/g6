"""소셜 로그인 Template Router"""
import hashlib
import logging
import zlib
from datetime import datetime
from typing import Optional
from uuid import uuid4

from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Query, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, exists, select
from starlette.responses import RedirectResponse
from typing_extensions import Annotated

from core.database import DBConnect, db_session
from core.exception import AlertCloseException, AlertException, JSONException
from core.formclass import MemberForm, RegisterSocialMemberForm
from core.models import Config, Member, MemberSocialProfiles
from core.template import UserTemplates
from lib.common import SOCIAL_PATH, session_member_key
from lib.dependency.auth import get_login_member
from lib.dependency.social import (
    get_auth_token_by_session, get_provider_by_query,
    get_provider_by_session, validate_link_social, validate_use_social_login
)
from lib.mail import send_register_mail
from lib.pbkdf2 import create_hash
from lib.social.social import (
    get_provider_client_key, get_social_login_token, get_social_profile, oauth, load_provider_class, register_social_provider
)
from service.member_service import MemberService, ValidateMember
from service.point_service import PointService


router = APIRouter(dependencies=[Depends(validate_use_social_login)])
templates = UserTemplates()

log = logging.getLogger("authlib")
logging.basicConfig()
log.setLevel(logging.DEBUG)

SessionLocal = DBConnect().sessionLocal


@router.get('/social/login')
async def request_social_login(
    request: Request,
    provider: Annotated[str, Depends(get_provider_by_query)],
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
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    provider: Annotated[str, Depends(get_provider_by_query)],
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
    social_email, profile = provider_class.convert_gnu_profile_data(response)
    if not profile.identifier:
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=str(request.url_for('login')))

    # 회원정보수정 > 소셜계정 연결
    if request.state.login_member:
        # 가입된 소셜 서비스 아이디가 존재하는지 확인
        social_profile = SocialAuthService.get_profile_by_identifier(profile.identifier, provider)
        if social_profile:
            raise AlertCloseException(detail=f"{provider} 소셜계정은 이미 연결된 계정이 존재합니다.", status_code=409)

        member = member_service.get_member(request.state.login_member.mb_id)
        if SocialAuthService.check_exists_by_mb_id(provider, member.mb_id):
            raise AlertCloseException(detail=f"본 계정은 이미 연결된 {provider} 소셜계정이 존재합니다.", status_code=409)

        # 소셜계정 연결
        provider_class = load_provider_class(provider)
        response = await get_social_profile(request, provider_class, auth_token)
        social_email, profile = provider_class.convert_gnu_profile_data(response)

        member_social_profiles = MemberSocialProfiles()
        member_social_profiles.mb_id = member.mb_id
        member_social_profiles.provider = provider
        member_social_profiles.identifier = profile.identifier
        member_social_profiles.displayname = profile.displayname
        member_social_profiles.profileurl = profile.profile_url
        member_social_profiles.photourl = profile.photourl
        db.add(member_social_profiles)
        db.commit()

        context = {
            "request": request,
            "provider": provider,
        }

        template = Jinja2Templates(directory=SOCIAL_PATH)
        return template.TemplateResponse("link_result.html", context)
    # 회원가입
    else:
        # 가입된 소셜 서비스 아이디가 존재하는지 확인
        social_profile = SocialAuthService.get_profile_by_identifier(profile.identifier, provider)

        # 가입정보가 있을 경우 로그인 처리
        if social_profile:
            member = member_service.get_member(social_profile.mb_id)

            request.session["ss_mb_id"] = member.mb_id
            request.session["ss_mb_key"] = session_member_key(request, member)  # XSS 공격 대응
            request.session["ss_social_provider"] = provider
            return RedirectResponse(url=request.url_for('index'), status_code=302)

        # 기존 회원정보에 소셜 가입 연결
        # FIXME: ss_social_link세션을 설정하는 부분이 없음
        if 'ss_social_link' in request.session and request.state.login_member.mb_id:
            member = request.state.login_member
            profile.mb_id = member.mb_id
            db.add(profile)
            db.commit()

            return RedirectResponse(url=request.url_for('index'), status_code=302)

        # 소셜 회원가입 페이지로 이동
        request.session['ss_social_provider'] = provider
        request.session['ss_social_email'] = social_email
        return RedirectResponse(url=request.url_for('get_social_register_form'), status_code=302)


@router.get('/social/register')
async def get_social_register_form(
    request: Request,
    validate: Annotated[ValidateMember, Depends()],
    provider: Annotated[str, Depends(get_provider_by_session)],
    auth_token: Annotated[dict, Depends(get_auth_token_by_session)],
):
    """
    소셜 회원가입 폼
    """
    social_email = request.session.get('ss_social_email', None)
    if social_email:
        is_exists_email = validate.is_exists_email(social_email)
    else:
        is_exists_email = False

    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)
    social_email, profile = provider_class.convert_gnu_profile_data(response)

    form_context = {
        "social_nickname": profile.displayname,
        "social_email": social_email,
        "action_url": request.url_for('post_social_register'),
        "is_exists_email": is_exists_email,
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
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    point_service: Annotated[PointService, Depends()],
    validate: Annotated[ValidateMember, Depends()],
    background_tasks: BackgroundTasks,
    provider: Annotated[str, Depends(get_provider_by_session)],
    auth_token: Annotated[dict, Depends(get_auth_token_by_session)],
    member_form: MemberForm = Depends(),
):
    """
    신규 소셜 회원등록
    """
    config: Config = request.state.config

    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)
    social_email, profile = provider_class.convert_gnu_profile_data(response)

    # token valid
    if not profile.identifier:
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=request.url_for('login'))

    # 소셜 아이디 검사
    gnu_social_id = SocialAuthService.g6_convert_social_id(profile.identifier, provider)
    validate.valid_id(gnu_social_id)

    # 이메일 유효성 검사
    validate.valid_email(member_form.mb_email)

    # 닉네임 유효성 검사
    mb_nick = member_form.mb_nick
    if not mb_nick:
        mb_nick = gnu_social_id.split('_')[1]
    validate.valid_nickname(mb_nick)

    # 유효성 검증 통과
    member_social_profiles = MemberSocialProfiles()
    member_social_profiles.mb_id = gnu_social_id
    member_social_profiles.provider = provider
    member_social_profiles.identifier = profile.identifier
    member_social_profiles.displayname = profile.displayname
    member_social_profiles.profileurl = profile.profile_url
    member_social_profiles.photourl = profile.photourl

    member_data = RegisterSocialMemberForm(
        mb_id=gnu_social_id,
        mb_password=create_hash(str(datetime.now().microsecond) + uuid4().hex),
        mb_name=mb_nick,
        mb_nick=mb_nick,
        mb_email=member_form.mb_email,
        mb_level=config.cf_register_level,
    )
    member = member_service.create_member(member_data)

    db.add(member_social_profiles)
    db.commit()

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
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    provider: Annotated[str, Depends(get_provider_by_session)],
    auth_token: Annotated[dict, Depends(get_auth_token_by_session)],
    mb_id: str = Form(...),
    mb_password: str = Form(...),
):
    """
    기존 회원에 소셜계정 연결
    """
    # 로그인 검증
    member = member_service.authenticate_member(mb_id, mb_password)

    # 이미 소셜계정이 연결되어 있는지 확인
    is_exists = SocialAuthService.check_exists_by_mb_id(provider, member.mb_id)
    if is_exists:
        raise AlertException(detail=f"이미 {provider} ID가 연결된 계정입니다.", status_code=400)

    # 소셜계정 연결
    provider_class = load_provider_class(provider)
    response = await get_social_profile(request, provider_class, auth_token)
    social_email, profile = provider_class.convert_gnu_profile_data(response)

    member_social_profiles = MemberSocialProfiles()
    member_social_profiles.mb_id = member.mb_id
    member_social_profiles.provider = provider
    member_social_profiles.identifier = profile.identifier
    member_social_profiles.displayname = profile.displayname
    member_social_profiles.profileurl = profile.profile_url
    member_social_profiles.photourl = profile.photourl
    db.add(member_social_profiles)
    db.commit()

    # 로그인 세션 생성
    request.session["ss_mb_id"] = member.mb_id
    ss_mb_key = session_member_key(request, member)  # XSS 공격 대응
    request.session["ss_mb_key"] = ss_mb_key

    raise AlertException(detail="소셜계정이 연결되었습니다.",
                         status_code=200,
                         url=request.url_for('index'))


@router.post('/social/unlink',
             dependencies=[Depends(validate_link_social)])
async def unlink_social_profile(
    member: Annotated[Member, Depends(get_login_member)],
    provider: Annotated[str, Query()] = "",
):
    """
    소셜계정 연결해제
    """
    if not SocialAuthService.check_exists_by_mb_id(provider, member.mb_id):
        raise JSONException(message="연결된 소셜계정이 없습니다.", status_code=404)

    SocialAuthService.unlink_social_login(member.mb_id, provider)
    return JSONResponse(
        {"success": True, "message": f"{provider} 계정이 연결해제 되었습니다."},
        status_code=200
    )


class SocialAuthService:

    @classmethod
    def get_profile_by_identifier(cls, identifier, provider) -> Optional[str]:
        """ 소셜 서비스 identifier 로 회원 아이디를 가져옴

        Args:
            identifier (str) : 소셜서비스 사용자 식별 id
            provider (str) : 소셜 제공자

        Returns:
            g5 user_id
        """
        with SessionLocal() as db:
            result = db.scalar(
                select(MemberSocialProfiles)
                .where(
                    MemberSocialProfiles.provider == provider,
                    MemberSocialProfiles.identifier == identifier
                )
            )
        if result:
            return result

        return None

    @classmethod
    def check_exists_by_mb_id(cls, provider: str, mb_id: str) -> bool:
        """소셜 서비스 아이디가 존재하는지 확인
        Args:
            provider (str) : 소셜 제공자
            mb_id (str) : 회원 아이디
        Returns:
            bool
        """
        with SessionLocal() as db:
            result = db.scalar(
                exists(MemberSocialProfiles.mp_no)
                .where(
                    MemberSocialProfiles.provider == provider,
                    MemberSocialProfiles.mb_id == mb_id
                ).select()
            )

        return result

    @classmethod
    def check_exists_by_member_id(cls, member_id) -> bool:
        """회원아이디가 존재하는지 확인
        Args:
            member_id (str) : 회원 아이디
        Returns:
            True or False
        """
        with SessionLocal() as db:
            result = db.scalar(
                exists(MemberSocialProfiles.mb_id)
                .where(MemberSocialProfiles.mb_id == member_id)
                .select()
            )
        if result:
            return True

        return False

    @classmethod
    def g6_convert_social_id(cls, identifier, provider: str):
        """소셜 id 생성 함수
        - 그누보드5의 get_social_convert_id() 함수를 참고하여 작성
        - provider + uid로 부터 고유 해시값생성

        Args:
            identifier (str) : 소셜서비스 사용자 식별 id
            provider (str) : 소셜 제공자

        Returns:
            provider_hax(adler32(md5(identifier)))
        """
        md5_hash = hashlib.md5(identifier.encode()).hexdigest()
        # Adler-32 hash on the hexadecimal MD5 hash
        adler32_hash = zlib.adler32(md5_hash.encode())

        return f"{provider}_{hex(adler32_hash)[2:]}"

    @classmethod
    def link_social_login(cls, mb_id: str, provider: str = None):
        """
        소셜계정 연결
        """
        pass
        # with SessionLocal() as db:
        #     query = delete(MemberSocialProfiles).where(MemberSocialProfiles.mb_id == mb_id)
        #     if provider:
        #         query = query.where(MemberSocialProfiles.provider == provider)
        #     db.execute(query)
        #     db.commit()

    @classmethod
    def unlink_social_login(cls, mb_id: str, provider: str = None):
        """소셜계정 연결해제
        """
        with SessionLocal() as db:
            query = delete(MemberSocialProfiles).where(MemberSocialProfiles.mb_id == mb_id)
            if provider:
                query = query.where(MemberSocialProfiles.provider == provider)
            db.execute(query)
            db.commit()
