import secrets
import zlib
from urllib.parse import parse_qs
from uuid import uuid4

from fastapi import APIRouter, Depends
from starlette.responses import RedirectResponse

from bbs.member_profile import validate_nickname, validate_userid
from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import MemberSocialProfiles
from core.template import UserTemplates
from lib.common import *
from lib.pbkdf2 import create_hash
from lib.point import insert_point
from lib.social import providers
from lib.social.social import (
    get_social_profile, get_social_login_token, oauth, SocialProvider,
)
from lib.template_filters import default_if_none

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none

log = logging.getLogger("authlib")
logging.basicConfig()
log.setLevel(logging.DEBUG)

SessionLocal = DBConnect().sessionLocal


@router.get('/social/login')
async def social_login(request: Request):
    """
    소셜 로그인
    """
    config: Config = request.state.config
    provider: List = parse_qs(request.url.query).get('provider', [])
    if provider.__len__() == 0:
        raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다.")

    provider_name = provider[0]

    if provider_name not in config.cf_social_servicelist:
        raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다. 관리자에게 문의하십시오.")

    # 소셜프로바이더 등록 - 다형성으로 호출
    provider_module_name = getattr(providers, f"{provider_name}")
    provider_class: SocialProvider = getattr(provider_module_name, f"{provider_name.capitalize()}")

    # 변경되는 설정값을 반영하기위해 여기서 client_id, secret 키를 등록한다.
    if provider_name == "naver":
        if not (config.cf_naver_clientid.strip() and config.cf_naver_secret.strip()):
            raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다. 관리자에게 문의하십시오.")
        provider_class.register(oauth, config.cf_naver_clientid.strip(), config.cf_naver_secret.strip())

    elif provider_name == 'kakao':
        if not config.cf_kakao_rest_key:
            raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다. 관리자에게 문의하십시오.")

        # 카카오 client_secret 은 선택사항
        provider_class.register(oauth, config.cf_kakao_rest_key.strip(), config.cf_kakao_client_secret.strip())

    elif provider_name == 'google':
        if not (config.cf_google_clientid.strip() and config.cf_google_secret.strip()):
            raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다. 관리자에게 문의하십시오.")

        provider_class.register(oauth, config.cf_google_clientid.strip(), config.cf_google_secret.strip())

    elif provider_name == 'twitter':
        if not (config.cf_twitter_key.strip() and config.cf_twitter_secret.strip()):
            raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다. 관리자에게 문의하십시오.")

        provider_class.register(oauth, config.cf_twitter_key.strip(), config.cf_twitter_secret.strip())

    elif provider_name == 'facebook':
        if not (config.cf_facebook_appid.strip() and config.cf_facebook_secret.strip()):
            raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다. 관리자에게 문의하십시오.")

        provider_class.register(oauth, config.cf_facebook_appid.strip(), config.cf_facebook_secret.strip())

    redirect_uri = (f"{request.url_for('authorize_social_login').__str__()}?provider={provider_name}"
                    .replace(":443", ""))

    return await oauth.__getattr__(provider_name).authorize_redirect(request, redirect_uri)


@router.get('/social/login/callback')
async def authorize_social_login(
    request: Request,
    db: db_session
):
    """소셜 로그인 인증 콜백
    Args:
        request (Request): starlette request
        db (SessionLocal): db session
    Returns:
        RedirectResponse
    """
    provider: List = parse_qs(request.url.query).get('provider', [])
    if provider.__len__() == 0:
        raise AlertException(status_code=400, detail="사용하지 않는 서비스 입니다.")
    provider_name: str = provider[0]

    auth_token = await get_social_login_token(provider_name, request)
    if auth_token is None:
        raise AlertException(status_code=400, detail="잠시후에 다시 시도해 주세요.",
                             url=request.url_for('login').__str__())

    provider_module_name = getattr(providers, f"{provider_name}")
    provider_class: SocialProvider = getattr(provider_module_name, f"{provider_name.capitalize()}")

    request.session['ss_social_access'] = auth_token
    response = await get_social_profile(auth_token, provider_name, request)

    social_email, profile = provider_class.convert_gnu_profile_data(response)
    identifier = str(profile.identifier)
    if not identifier:
        logging.critical(
            f'social login identifier is empty, gnu profile convert parsing error. '
            f'social_provider: {provider}, profile: {profile}')
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=request.url_for('login').__str__())

    # 가입된 소셜 서비스 아이디가 존재하는지 확인
    social_profile = SocialAuthService.get_profile_by_identifier(identifier, provider_name)
    if social_profile:
        config = request.state.config
        # 이미 가입된 회원이라면 로그인
        member = db.scalar(
            select(Member).where(Member.mb_id == social_profile.mb_id)
        )
        if not member:
            raise AlertException(
                status_code=400, detail="유효하지 않은 요청입니다.",
                url=request.url_for('login').__str__())
        elif member.mb_leave_date or member.mb_intercept_date:
            raise AlertException("탈퇴 또는 차단된 회원입니다.", 404)
        elif config.cf_use_email_certify and member.mb_email_certify == datetime(1, 1, 1, 0, 0, 0):
            raise AlertException(f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다.", 404)

        # 로그인
        request.session["ss_mb_id"] = member.mb_id
        # XSS 공격에 대응하기 위하여 회원의 고유키를 생성해 놓는다.
        request.session["ss_mb_key"] = session_member_key(request, member)
        request.session["ss_social_provider"] = provider_name
        return RedirectResponse(url="/", status_code=302)

    if 'ss_social_link' in request.session and request.state.login_member.mb_id:
        # 소셜 가입 연결
        member = request.state.login_member
        profile.mb_id = member.mb_id
        db.add(profile)
        db.commit()

        return RedirectResponse(url=request.url_for('index'), status_code=302)

    # 회원가입
    request.session['ss_social_provider'] = provider_name
    request.session['ss_social_email'] = social_email
    return RedirectResponse(url=request.url_for('get_social_register_form'), status_code=302)


@router.get('/social/register')
async def get_social_register_form(request: Request):
    """
    소셜 회원가입 폼
    """
    config = request.state.config
    if not config.cf_social_login_use:
        raise AlertException(status_code=400, detail="소셜로그인을 사용하지 않습니다.")

    provider_name = request.session.get("ss_social_provider", None)
    if (request.session.get('ss_social_access', None) is None) or (provider_name is None):
        raise AlertException(status_code=400, detail="먼저 소셜로그인을 하셔야됩니다.",
                             url=request.url_for('login').__str__())
    social_email = request.session.get('ss_social_email', None)
    is_exists_email = False if social_email is None else True

    form_context = {
        "social_member_id": "",  # g5 user_id
        "social_member_email": social_email,  # user_email
        "action_url": request.url_for('post_social_register'),
        "is_exists_email": is_exists_email,
    }
    return templates.TemplateResponse("/social/social_register_member.html", {
        "request": request,
        "config": config,
        "form": form_context,
        "provider_name": provider_name,
    })


@router.post('/social/register')
async def post_social_register(
    request: Request,
    db: db_session,
    member_form: MemberForm = Depends(),
):
    """
    신규 소셜 회원등록
    """
    config = request.state.config
    if not config.cf_social_login_use:
        raise AlertException(status_code=400, detail="소셜로그인을 사용하지 않습니다.",
                             url=request.url_for('login').__str__())

    provider_name = request.session.get("ss_social_provider", None)
    if (request.session.get('ss_social_access', None) is None) or (provider_name is None):
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=request.url_for('login').__str__())

    auth_token = request.session.get('ss_social_access', None)
    provider_module_name = getattr(providers, f"{provider_name}")
    provider_class: SocialProvider = getattr(provider_module_name, f"{provider_name.capitalize()}")
    response = await get_social_profile(auth_token, provider_name, request)
    social_email, profile = provider_class.convert_gnu_profile_data(response)

    # token valid

    identifier = str(profile.identifier)
    if not identifier:
        logging.critical(
            f'social login identifier is empty, gnu profile convert parsing error. '
            f'social_provider: {provider_name}, profile: {profile}')
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=request.url_for('login').__str__())

    gnu_social_id = SocialAuthService.g6_convert_social_id(identifier, provider_name)
    exists_social_member = db.scalar(select(Member).where(Member.mb_id == gnu_social_id))
    # 유효성 검증
    if exists_social_member:
        raise AlertException(status_code=400, detail="이미 소셜로그인으로 가입된 회원아이디 입니다.",
                             url=request.url_for('login').__str__())

    result = validate_userid(gnu_social_id, config.cf_prohibit_id)
    if result["msg"]:
        raise AlertException(status_code=400, detail=result["msg"])

    if not valid_email(member_form.mb_email):
        raise AlertException(status_code=400, detail="이메일 양식이 올바르지 않습니다.")

    exists_email = db.scalar(
        exists(Member.mb_email)
        .where(Member.mb_email == member_form.mb_email).select()
    )
    if exists_email:
        raise AlertException(status_code=400, detail="이미 존재하는 이메일 입니다.")

    result = validate_nickname(member_form.mb_nick, config.cf_prohibit_id)
    if result["msg"]:
        raise AlertException(status_code=400, detail=result["msg"])

    # nick
    mb_nick = member_form.mb_nick
    if not mb_nick:
        mb_nick = gnu_social_id.split('_')[1]

    request_time = datetime.now()

    # 유효성 검증 통과
    member_social_profiles = MemberSocialProfiles()
    member_social_profiles.mb_id = gnu_social_id
    member_social_profiles.provider = provider_name
    member_social_profiles.identifier = identifier
    member_social_profiles.nickname = mb_nick
    member_social_profiles.profile_url = profile.profile_url
    member_social_profiles.photourl = profile.photourl
    member_social_profiles.object_sha = ""  # 사용하지 않는 데이터.
    member_social_profiles.mp_register_day = request_time

    member = Member()
    member.mb_id = gnu_social_id
    member.mb_password = create_hash(str(request_time.microsecond) + uuid4().hex)
    member.mb_name = mb_nick
    member.mb_nick = mb_nick
    member.mb_email = member_form.mb_email
    member.mb_datetime = request_time
    member.mb_today_login = request_time
    member.mb_level = config.cf_register_level

    # 메일인증
    if config.cf_use_email_certify:
        # 일회용 인증키 생성
        member.mb_email_certify2 = secrets.token_hex(16)
    else:
        # 메일인증을 사용하지 않을 경우 바로 인증처리
        member.mb_email_certify = datetime.now()

    db.add(member)
    db.add(member_social_profiles)
    db.commit()

    # 회원가입 포인트 부여
    insert_point(request, member.mb_id, config.cf_register_point,  "회원가입 축하", "@member", member.mb_id, "회원가입")

    # 회원에게 인증메일 발송
    if config.cf_use_email_certify:
        subject = f"[{config.cf_title}] 회원가입 인증메일 발송"
        body = templates.TemplateResponse(
            "bbs/mail_form/register_certify_mail.html",
            {
                "request": request,
                "member": member,
                "certify_href": f"{request.base_url.__str__()}bbs/email_certify/{member.mb_id}?certify={member.mb_email_certify2}",
            }
        ).body.decode("utf-8")
        mailer(member.mb_email, subject, body)

    # 최고관리자에게 회원가입 메일 발송
    if config.cf_email_mb_super_admin:
        subject = f"[{config.cf_title}] {member.mb_nick} 님께서 회원으로 가입하셨습니다."
        body = templates.TemplateResponse(
            "bbs/mail_form/register_send_admin_mail.html",
            {
                "request": request,
                "member": member,
            }
        ).body.decode("utf-8")
        mailer(config.cf_admin_email, subject, body)

    return RedirectResponse(url="/", status_code=302)


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
    def check_exists_by_social_id(cls, identifier, provider) -> bool:
        """소셜 서비스 아이디가 존재하는지 확인
        Args:
            identifier (str) : 소셜서비스 사용자 식별 id
            provider (str) : 소셜 제공자
        Returns:
            True or False
        """
        with SessionLocal() as db:
            result = db.scalar(
                exists(MemberSocialProfiles.mp_no)
                .where(
                    MemberSocialProfiles.provider == provider,
                    MemberSocialProfiles.identifier == identifier
                ).select()
            )
        if result:
            return True

        return False

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
    def unlink_social_login(cls, member_id):
        """소셜계정 연결해제
        """
        with SessionLocal() as db:
            db.execute(
                delete(MemberSocialProfiles)
                .where(MemberSocialProfiles.mb_id == member_id)
            )
            db.commit()
