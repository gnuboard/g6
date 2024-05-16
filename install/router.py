"""설치 Template Router"""
import os
import secrets
import shutil
import sys

import fastapi
from cachetools import TTLCache
from dotenv import set_key
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import exists, insert, MetaData, select, Table
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from core import models
from core.database import DBConnect
from core.exception import AlertException
from core.formclass import InstallFrom
from core.plugin import read_plugin_state, write_plugin_state
from core.settings import ENV_PATH, settings
from install.default_values import (
    default_board_data, default_boards, default_cache_directory, default_config,
    default_contents, default_data_directory, default_faq_master, default_gr_id,
    default_group, default_member, default_qa_config, default_version
)
from lib.common import dynamic_create_write_table, read_license
from lib.dependency.dependencies import validate_install, validate_token
from lib.pbkdf2 import create_hash


INSTALL_TEMPLATES = "install/templates"

router = APIRouter(prefix="/install",
                   tags=["install"],
                   include_in_schema=False)
templates = Jinja2Templates(directory=INSTALL_TEMPLATES)
templates.env.globals["default_version"] = default_version

form_cache = TTLCache(maxsize=1, ttl=60)


@router.get("/",
            name="install_main",
            dependencies=[Depends(validate_install)])
async def main(request: Request):
    """설치 메인 페이지"""
    # 파이썬 버전
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    # fastapi 버전
    fastapi_version = f"{fastapi.__version__}"
    context = {
        "request": request,
        "python_version": python_version,
        "fastapi_version": fastapi_version,
    }
    return templates.TemplateResponse("main.html", context)


@router.get("/license",
            name="install_license",
            dependencies=[Depends(validate_install)])
async def install_license(request: Request):
    """라이선스 동의 페이지"""
    context = {
        "request": request,
        "license": read_license(),
    }
    return templates.TemplateResponse("license.html", context)


@router.get("/form",
            dependencies=[Depends(validate_install)])
async def redirect_licence(request: Request):
    """라이선스 동의 페이지로 Redirect"""
    return RedirectResponse(url=request.url_for("install_license"))


@router.post("/form",
             name="install_form",
             dependencies=[Depends(validate_install)])
async def install_form(request: Request, agree: str = Form(None)):
    """설치 폼 페이지"""
    if agree != "동의함":
        raise AlertException("라이선스에 동의하셔야 설치 가능합니다.", 400)
    context = {
        "request": request,
    }
    return templates.TemplateResponse("form.html", context)


@router.post("/",
             name="install",
             dependencies=[Depends(validate_token),
                           Depends(validate_install)])
async def install(
    request: Request,
    form_data: InstallFrom = Depends(),
):
    """설치 시작 전 데이터베이스 연결 및 초기화"""
    try:
        # example.env 파일이 있는 경우 .env 파일로 복사
        if os.path.exists("example.env"):
            shutil.copyfile("example.env", ENV_PATH)

        # .env 파일에 데이터베이스 정보 추가
        set_key(ENV_PATH, "DB_ENGINE", form_data.db_engine)
        set_key(ENV_PATH, "DB_HOST", form_data.db_host)
        set_key(ENV_PATH, "DB_PORT", form_data.db_port, quote_mode="never")
        set_key(ENV_PATH, "DB_USER", form_data.db_user)
        set_key(ENV_PATH, "DB_PASSWORD", form_data.db_password)
        set_key(ENV_PATH, "DB_NAME", form_data.db_name)
        set_key(ENV_PATH, "DB_TABLE_PREFIX", form_data.db_table_prefix)
        # .env 세션 비밀키 설정
        session_secret_key = secrets.token_urlsafe(50)
        set_key(ENV_PATH, "SESSION_SECRET_KEY", session_secret_key)

        # Settings 클래스에 .env 파일 설정 적용
        settings.DB_ENGINE = form_data.db_engine
        settings.DB_HOST = form_data.db_host
        settings.DB_PORT = form_data.db_port
        settings.DB_USER = form_data.db_user
        settings.DB_PASSWORD = form_data.db_password
        settings.DB_NAME = form_data.db_name
        settings.DB_TABLE_PREFIX = form_data.db_table_prefix
        settings.SESSION_SECRET_KEY = session_secret_key

        # 데이터베이스 연결 설정
        db = DBConnect()
        db.set_connect_infomation()
        db.create_url()
        if not db.supported_engines.get(form_data.db_engine.lower()):
            raise Exception("지원가능한 데이터베이스 엔진을 선택해주세요.")

        # 새로운 데이터베이스 연결 생성 및 테스트
        db.create_engine()
        connect = db.engine.connect()
        connect.close()

        # 플러그인 활성화 초기화
        plugin_list = read_plugin_state()
        for plugin in plugin_list:
            plugin.is_enable = False
        write_plugin_state(plugin_list)

        form_cache.update({"form": form_data})

        # 세션 초기화
        request.session.clear()

        return templates.TemplateResponse("result.html", {"request": request})

    except OperationalError as e:
        os.remove(ENV_PATH)
        message = e._message().replace('"', r'\"').strip()
        raise AlertException(f"설치가 실패했습니다. 데이터베이스 연결에 실패했습니다.\\n{message}")

    except Exception as e:
        os.remove(ENV_PATH)
        raise AlertException(f"설치가 실패했습니다.\\n{e}")


@router.get("/process", dependencies=[Depends(validate_token)])
async def install_process(request: Request):
    async def install_event():
        db_connect = DBConnect()
        engine = db_connect.engine
        SessionLocal = db_connect.sessionLocal
        yield "데이터베이스 연결 완료"

        try:
            form_data: InstallFrom = form_cache.get("form")

            if form_data.reinstall:
                models.Base.metadata.drop_all(bind=engine)
                # 접두사 + 'write_' 게시판 테이블 전부 삭제
                metadata = MetaData()
                metadata.reflect(bind=engine)
                table_names = metadata.tables.keys()
                for name in table_names:
                    if name.startswith(f"{form_data.db_table_prefix}write_"):
                        Table(name, metadata, autoload=True).drop(bind=engine)

                yield "기존 데이터베이스 테이블 삭제 완료"

            models.Base.metadata.create_all(bind=engine)
            yield "데이터베이스 테이블 생성 완료"

            with SessionLocal() as db:
                config_setup(db, form_data.admin_id, form_data.admin_email)
                admin_member_setup(db, form_data.admin_id, form_data.admin_name,
                                   form_data.admin_password, form_data.admin_email)
                content_setup(db)
                qa_setup(db)
                faq_master_setup(db)
                board_group_setup(db)
                board_setup(db)
                db.commit()
                yield "기본설정 정보 입력 완료"

            for board in default_boards:
                dynamic_create_write_table(board['bo_table'], create_table=True)
            yield "게시판 테이블 생성 완료"

            setup_data_directory()
            yield "데이터 경로 생성 완료"

            yield f"[success] 축하합니다. {default_version} 설치가 완료되었습니다."

        except Exception as e:
            os.remove(ENV_PATH)
            yield f"[error] 설치가 실패했습니다. {e}"
            raise

    # 설치 진행 이벤트 스트림 실행
    return EventSourceResponse(install_event())


def config_setup(db: Session, admin_id, admin_email):
    """환경설정 기본값 등록"""
    exists_config = db.scalar(
        exists(models.Config)
        .where(models.Config.cf_id == 1).select()
    )
    if not exists_config:
        db.execute(
            insert(models.Config).values(
                cf_admin=admin_id,
                cf_admin_email=admin_email,
                **default_config
            )
        )


def admin_member_setup(db: Session, admin_id: str, admin_name : str,
                       admin_password: str, admin_email: str):
    """최고관리자 등록"""
    admin_member = db.scalar(
        select(models.Member).where(models.Member.mb_id == admin_id)
    )
    if admin_member:
        admin_member.mb_password = create_hash(admin_password)
        admin_member.mb_name = admin_name
        admin_member.mb_email = admin_email
    else:
        db.execute(
            insert(models.Member).values(
                mb_id=admin_id,
                mb_password=create_hash(admin_password),
                mb_name=admin_name,
                mb_nick=admin_name,
                mb_email=admin_email,
                **default_member
            )
        )


def content_setup(db: Session):
    """컨텐츠 기본값 등록"""
    for content in default_contents:
        exists_content = db.scalar(
            exists(models.Content)
            .where(models.Content.co_id == content['co_id']).select()
        )
        if not exists_content:
            db.execute(insert(models.Content).values(**content))


def qa_setup(db: Session):
    """Q&A 기본값 등록"""

    exists_qa = db.scalar(
        exists(models.QaConfig).select()
    )
    if not exists_qa:
        db.execute(insert(models.QaConfig).values(**default_qa_config))


def faq_master_setup(db: Session):
    """FAQ Master 기본값 등록"""
    exists_faq_master = db.scalar(
        exists(models.FaqMaster)
        .where(models.FaqMaster.fm_id == 1).select()
    )
    if not exists_faq_master:
        db.execute(insert(models.FaqMaster).values(**default_faq_master))


def board_group_setup(db: Session):
    """게시판 그룹 기본값 생성"""
    exists_board_group = db.scalar(
        exists(models.Group)
        .where(models.Group.gr_id == default_gr_id).select()
    )
    if not exists_board_group:
        db.execute(insert(models.Group).values(**default_group))


def board_setup(db: Session):
    """게시판 기본값 및 테이블 생성"""
    for board in default_boards:
        exists_board = db.scalar(
            exists(models.Board)
            .where(models.Board.bo_table == board['bo_table']).select()
        )
        if not exists_board:
            query = insert(models.Board).values(**board, **default_board_data)
            db.execute(query)


def setup_data_directory():
    """데이터 경로 초기화"""
    # 데이터 경로 생성
    os.makedirs(default_data_directory, exist_ok=True)
    # 캐시 디렉토리 비우기
    if os.path.exists(default_cache_directory):
        shutil.rmtree(default_cache_directory)
    # 캐시 디렉토리 생성
    os.makedirs(default_cache_directory)
