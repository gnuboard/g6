from dotenv import set_key
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sse_starlette.sse import EventSourceResponse

import common.models as models
from .default_values import *
from common.database import DBConnect, DBSetting
from common.formclass import InstallFrom
from lib.common import *
from lib.pbkdf2 import create_hash

INSTALL_TEMPLATES = "install/templates"


router = APIRouter()
templates = Jinja2Templates(directory=INSTALL_TEMPLATES)
templates.env.globals["version"] = default_version

form_cache = cachetools.TTLCache(maxsize=1, ttl=60)


@router.get("/", name="install_main", dependencies=[Depends(validate_install)])
async def main(request: Request):
    """설치 메인 페이지"""
    return templates.TemplateResponse("main.html", {"request": request})


@router.get("/license", name="install_license", dependencies=[Depends(validate_install)])
async def license(request: Request):
    """라이선스 동의 페이지"""
    context = {
        "request": request,
        "license": read_license(),
    }
    return templates.TemplateResponse("license.html", context)


@router.get("/form", dependencies=[Depends(validate_install)])
async def form(request: Request):
    """설치 폼 Redirect"""
    return RedirectResponse(url=request.url_for("install_license"))


@router.post("/form", name="install_form", dependencies=[Depends(validate_install)])
async def form(request: Request):
    """설치 폼 페이지"""
    
    context = {
        "request": request,
    }
    return templates.TemplateResponse("form.html", context)


@router.post("/",
             name="install",
             dependencies=[Depends(validate_token), Depends(validate_install)])
async def install(
    request: Request,
    form: InstallFrom = Depends(),
):
    try:
        # example.env 파일이 있는 경우 .env 파일로 복사
        if os.path.exists("example.env"):
            shutil.copyfile("example.env", ENV_PATH)

        # .env 파일에 데이터베이스 정보 추가
        set_key(ENV_PATH, "DB_ENGINE", form.db_engine)
        set_key(ENV_PATH, "DB_HOST", form.db_host)
        set_key(ENV_PATH, "DB_PORT", form.db_port, quote_mode="never")
        set_key(ENV_PATH, "DB_USER", form.db_user)
        set_key(ENV_PATH, "DB_PASSWORD", form.db_password)
        set_key(ENV_PATH, "DB_NAME", form.db_name)
        set_key(ENV_PATH, "DB_TABLE_PREFIX", form.db_table_prefix)

        # 데이터베이스 연결 설정
        db_setting = DBSetting()
        if not db_setting.supported_engines.get(form.db_engine.lower()):
            raise Exception("지원가능한 데이터베이스 엔진을 선택해주세요.")

        new_engine = create_engine(
            db_setting.url,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=40,
            pool_timeout=60
        )
        # 데이터베이스 연결 테스트
        connect = new_engine.connect()
        connect.close()
        session = sessionmaker(autocommit=False, autoflush=False,
                               bind=new_engine, expire_on_commit=True)

        # 새로운 데이터베이스 연결 추가
        db_connect = DBConnect()
        db_connect.engine = new_engine
        db_connect.sessionLocal = session

        form_cache.update({"form": form})

        return templates.TemplateResponse("result.html", {"request": request})

    # except FileNotFoundError as e:
    #     raise AlertException(f"설치가 실패했습니다. '{e.filename}' 파일을 찾을 수 없습니다.\\n{e}")

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
        yield "설치를 시작합니다. 페이지를 닫지 말고 잠시만 기다려주세요."
        db_connect = DBConnect()
        engine = db_connect.engine
        SessionLocal = db_connect.sessionLocal

        try:
            form: InstallFrom = form_cache.get("form")

            if form.reinstall:
                models.Base.metadata.drop_all(bind=engine)
                yield "기존 데이터베이스 테이블 삭제 완료"

            models.Base.metadata.create_all(bind=engine)
            yield "데이터베이스 테이블 생성 완료"

            with SessionLocal() as db:
                config_setup(db, form.admin_id, form.admin_email)
                admin_member_setup(db, form.admin_id, form.admin_password, form.admin_email)
                content_setup(db)
                faq_master_setup(db)
                board_group_setup(db)
                board_setup(db)
                db.commit()
                yield "그누보드6 기본 데이터 입력 완료"

            for board in default_boards:
                dynamic_create_write_table(board['bo_table'], create_table=True)
            yield "게시판 테이블 생성 완료"

            setup_data_directory()
            yield "데이터 경로 생성 완료"

            yield f"[success] 축하합니다. {default_version} 설치가 완료되었습니다."
        
        except Exception as e:
            yield f"[error] 설치가 실패했습니다. {e}"

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


def admin_member_setup(db: Session, admin_id, admin_password, admin_email):
    """최고관리자 등록"""
    exists_admin_member = db.scalar(
        exists(models.Member)
        .where(models.Member.mb_id == admin_id).select()
    )
    if not exists_admin_member:
        db.execute(
            insert(models.Member).values(
                mb_id=admin_id,
                mb_password=create_hash(admin_password),
                mb_name=admin_id,
                mb_nick=admin_id,
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
    if not os.path.exists(default_data_directory):
        os.makedirs(default_data_directory)
    # 캐시 디렉토리 비우기
    if os.path.exists(default_cache_directory):
        shutil.rmtree(default_cache_directory)
    # 캐시 디렉토리 생성
    os.makedirs(default_cache_directory)
