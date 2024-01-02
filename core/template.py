import logging
import os

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from jinja2 import Environment
from sqlalchemy import select
from starlette.staticfiles import StaticFiles

from core.database import DBConnect
from core.models import Config
from core.plugin import PLUGIN_DIR,\
    get_admin_plugin_menus, get_all_plugin_module_names
from lib.common import *


def get_theme_from_db() -> str:
    """DB에 설정된 테마의 경로를 반환

    Returns:
        str: 테마 경로
    """
    default_theme = "basic"
    try:
        with DBConnect().sessionLocal() as db:
            theme = db.scalar(select(Config.cf_theme)) or default_theme
            theme_path = f"{TEMPLATES}/{theme}"
            
            # DB에 설정된 테마가 경로에 존재하는지 확인
            if not os.path.exists(theme_path):
                theme_path = f"{TEMPLATES}/{default_theme}"

            return theme_path
    except Exception:
        return f"{TEMPLATES}/{default_theme}"

TEMPLATES = "templates"
TEMPLATES_DIR = get_theme_from_db()  # 사용자 템플릿 경로
ADMIN_TEMPLATES_DIR = "admin/templates"  # 관리자 템플릿 경로


class UserTemplates(Jinja2Templates):
    """
    사용자 Jinja2Template 설정 클래스
    - 사용자에서 반복적으로 사용되는 템플릿 설정을 관리
    - 싱글톤 패턴으로 구현
    """
    _instance = None
    default_directories = [TEMPLATES_DIR, EDITOR_PATH, CAPTCHA_PATH]

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UserTemplates, cls).__new__(cls)
            cls._instance._initialized = False  # Initialization flag added
        return cls._instance

    def __init__(self,
                 context_processors: dict = None,
                 globals: dict = None,
                 env: Environment = None
                 ):
        if not getattr(self, '_initialized', False):
            self._initialized = True
            super().__init__(directory=self.default_directories, context_processors=context_processors)

            # 템플릿 필터 설정
            self.env.filters["datetime_format"] = datetime_format
            self.env.filters["number_format"] = number_format
            self.env.filters["set_query_params"] = set_query_params
            # 템플릿 전역 설정
            self.env.globals["editor_macro"] = editor_macro
            self.env.globals["getattr"] = getattr
            self.env.globals["get_selected"] = get_selected
            self.env.globals["get_member_icon"] = get_member_icon
            self.env.globals["get_member_image"] = get_member_image
            self.env.globals["theme_asset"] = theme_asset
            # 템플릿 컨텍스트 프로세서 설정
            self.context_processors.append(self._default_context)
            # 추가 env.global 설정
            if globals:
                self.env.globals.update(**globals.__dict__)

    def _default_context(self):
        context = {
            "menus": get_menus(),
            "poll": get_recent_poll(),
            "populars": get_populars(),
            "latest": latest,
            "visit": visit,
        }
        return context

    # temp debug
    # def TemplateResponse(
    #         self,
    #         name: str,
    #         context: dict,
    #         status_code: int = 200,
    #         headers: typing.Optional[typing.Mapping[str, str]] = None,
    #         media_type: typing.Optional[str] = None,
    #         background=None):

    #     logger = logging.getLogger("uvicorn.error")
    #     logger.warning("------template---------")
    #     logger.info(name)
    #     logger.info(self.env.loader.searchpath)

    #     return super().TemplateResponse(name, context, status_code, headers, media_type, background)


class AdminTemplates(Jinja2Templates):
    """
    관리자 Jinja2Template 설정 클래스
    - 관리자에서 반복적으로 사용되는 템플릿 설정을 관리
    - 싱글톤 패턴으로 구현
    """
    _instance = None
    default_directories = [ADMIN_TEMPLATES_DIR, CAPTCHA_PATH, EDITOR_PATH, PLUGIN_DIR]

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AdminTemplates, cls).__new__(cls)
            cls._instance._initialized = False  # Initialization flag added
        return cls._instance

    def __init__(self,
                 context_processors: dict = None,
                 globals: dict = None,
                 env: Environment = None
                 ):
        if not getattr(self, '_initialized', False):
            self._initialized = True
            super().__init__(directory=self.default_directories, context_processors=context_processors)

            # 템플릿 필터 설정
            self.env.filters["datetime_format"] = datetime_format
            self.env.filters["number_format"] = number_format
            self.env.filters["set_query_params"] = set_query_params
            # 템플릿 전역 설정
            self.env.globals["editor_macro"] = editor_macro
            self.env.globals["getattr"] = getattr
            self.env.globals["get_selected"] = get_selected
            self.env.globals["get_member_icon"] = get_member_icon
            self.env.globals["get_member_image"] = get_member_image
            self.env.globals["theme_asset"] = theme_asset
            self.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
            self.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
            self.env.globals["option_selected"] = option_selected
            self.env.globals["option_array_checked"] = option_array_checked
            self.env.globals["subject_sort_link"] = subject_sort_link
            # 템플릿 컨텍스트 프로세서 설정
            self.context_processors.append(self._default_admin_context)

            # 추가 env.global 설정
            if globals:
                self.env.globals.update(**globals.__dict__)

    def _default_admin_context(self, request: Request):
        context = {
            "admin_menus": get_admin_menus()
        }
        return context


def theme_asset(asset_path: str) -> str:
    """
    현재 템플릿의 asset url을 반환하는 헬퍼 함수

    Args:
        asset_path (str): 플러그인 모듈 이름

    Returns:
        asset_url (str): asset url
    """

    theme_path = TEMPLATES_DIR
    theme_name = theme_path.replace(TEMPLATES + '/', "")

    return f"/theme_static/{theme_name}/{asset_path}"


def register_theme_statics(app: FastAPI) -> None:
    """
    현재 테마의 static 디렉토리를 등록하는 함수

    Args:
        app (FastAPI): FastAPI 객체
    """
    # url 경로 /theme_static/{{theme_name}}/css, js, img 등 static 생략
    # 실제 경로 /theme/{{theme_name}}/static/ 을 등록
    theme_path = TEMPLATES_DIR
    theme_name = theme_path.replace(TEMPLATES + '/', "")

    if not os.path.isdir(f"{TEMPLATES}/{theme_name}/static"):
        logger = logging.getLogger("uvicorn.error")
        logger.warning("template has not static directory")
        return

    url = f"/theme_static/{theme_name}"
    path = StaticFiles(directory=f"{TEMPLATES}/{theme_name}/static")
    app.mount(url, path, name=f"static_{theme_name}")  # tag