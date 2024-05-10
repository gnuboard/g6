"""인증 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
import re
from datetime import datetime
from sqlalchemy import select
from typing_extensions import Annotated
from fastapi import Depends, Query, Request, Response
from sqlalchemy.orm import Session

from core.database import db_session, get_db
from core.exception import AlertException
from core.models import Config, Member
from core.settings import settings
from lib.common import session_member_key
from lib.member import is_super_admin
from lib.point import insert_point
from service.member_service import MemberService


def get_login_member(request: Request):
    """현재 로그인 여부 검사 진행 후 로그인 멤버를 반환한다."""
    member: Member = request.state.login_member
    if not member:
        path = request.url.path
        url = request.url_for("login_form").replace_query_params(url=path)
        raise AlertException("로그인 후 이용 가능합니다.", 403, url=url)

    return member


def get_login_member_optional(request: Request) -> Member:
    """현재 로그인 멤버를 반환한다. 로그인이 되어 있지 않으면 None을 반환한다."""
    member: Member = request.state.login_member
    return member



def dependency_provider(class_type):
    async def dependency():
        instance = class_type()
        # if hasattr(instance, 'async_init'):
        #     with SyncSessionLocal() as db:
        #         await instance.async_init(db)
        return instance
    return dependency


class TestService:
    def __init__(self, db: Session):
        self.db = db
        config = self.db.scalars(select(Config)).first()
        print("TestService init...", config.cf_title)
        # self.db = db

    @classmethod
    async def async_init(cls, db: db_session, id: Annotated[int, Query()] = 1):
        print("TestService async_init...")
        instance = await cls(db)
        return instance

async def manage_member_authentication(
        request: Request,
        response: Response,
        db: db_session,
        service: Annotated[TestService, Depends(TestService.async_init)]
        # service: Annotated[TestService, Depends()]
        # service: Annotated[MemberService, Depends()]
    ):
    """로그인 세션 및 자동로그인 등 사용자 인증을 관리합니다."""
    # print("manage_member_authentication", db)
    member = None
    # is_autologin = False
    # ss_mb_key = None
    # session_mb_id = request.session.get("ss_mb_id", "")
    # cookie_mb_id = request.cookies.get("ck_mb_id", "")
    # cookie_domain = settings.COOKIE_DOMAIN

    # try:
    #     # 로그인 세션 유지 중이라면
    #     if session_mb_id:
    #         member = service.get_member(session_mb_id)
    #         # 회원 정보가 없거나 탈퇴한 회원이라면 세션을 초기화
    #         if not service.is_activated(member)[0]:
    #             request.session.clear()
    #             member = None

    #     # 자동 로그인 쿠키가 있다면
    #     elif cookie_mb_id:
    #         mb_id = re.sub("[^a-zA-Z0-9_]", "", cookie_mb_id)[:20]
    #         member = service.get_member(session_mb_id)

    #         # 최고관리자는 보안상 자동로그인 기능을 사용하지 않는다.
    #         if (not is_super_admin(request, mb_id)
    #                 and service.is_member_email_certified(member)[0]
    #                 and service.is_activated(member)[0]):
    #             # 쿠키에 저장된 키와 서버에서 생성한 키가 일치하는지 검사
    #             ss_mb_key = session_member_key(request, member)
    #             if request.cookies.get("ck_auto") == ss_mb_key:
    #                 request.session["ss_mb_id"] = cookie_mb_id
    #                 is_autologin = True
    # except Exception:
    #     response.delete_cookie("ck_auto")
    #     response.delete_cookie("ck_mb_id")
    #     request.session.clear()

    # # 로그인한 회원 정보
    # request.state.login_member = member
    # # 최고관리자 여부
    # request.state.is_super_admin = is_super_admin(request, getattr(member, "mb_id", None))

    # if member:
    #     # 오늘 처음 로그인 이라면 포인트 지급 및 로그인 정보 업데이트
    #     ymd_str = datetime.now().strftime("%Y-%m-%d")
    #     if member.mb_today_login.strftime("%Y-%m-%d") != ymd_str:
    #         insert_point(request, db, member.mb_id, request.state.config.cf_login_point,
    #                      ymd_str + " 첫로그인", "@login", member.mb_id, ymd_str)

    #         member.mb_today_login = datetime.now()
    #         member.mb_login_ip = request.client.host
    #         db.commit()

    # # 자동로그인 쿠키 재설정
    # # is_autologin과 세션을 확인해서 로그아웃 처리 이후 쿠키가 재설정되는 것을 방지
    # if is_autologin and request.session.get("ss_mb_id"):
    #     response.set_cookie(key="ck_mb_id", value=cookie_mb_id,
    #                         max_age=60 * 60 * 24 * 30, domain=cookie_domain)
    #     response.set_cookie(key="ck_auto", value=ss_mb_key,
    #                         max_age=60 * 60 * 24 * 30, domain=cookie_domain)
