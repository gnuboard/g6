import logging
import os
import typing

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from pydantic import TypeAdapter
from sqlalchemy import select
from starlette.background import BackgroundTask
from starlette.staticfiles import StaticFiles
from starlette.templating import _TemplateResponse

from core.database import DBConnect
from core.models import Config
from core.plugin import (
    get_admin_plugin_menus, get_all_plugin_module_names, PLUGIN_DIR
)
from lib.common import *
from lib.member_lib import get_member_icon, get_member_image
from lib.template_filters import (
    datetime_format, number_format, set_query_params
)
from lib.template_functions import (
    editor_macro, get_selected, option_selected,
    option_array_checked, subject_sort_link
)


def get_template_path() -> str:
    """기본환경설정 > 템플릿의 설정 경로를 반환
    - 설정된 템플릿이 존재하지 않을 경우 기본 템플릿을 반환

    Returns:
        str: 템플릿 경로
    """
    default_template = "basic"
    default_template_path = f"{TEMPLATES}/{default_template}"
    try:
        with DBConnect().sessionLocal() as db:
            template = db.scalar(select(Config.cf_theme)) or default_template
            template_path = f"{TEMPLATES}/{template}"

            # 실제 템플릿이 존재하는지 확인            
            if not os.path.exists(template_path):
                return default_template_path

            return template_path
    except Exception:
        return default_template_path


TEMPLATES = "templates"
TEMPLATES_DIR = get_template_path()  # 사용자 템플릿 경로
ADMIN_TEMPLATES_DIR = "admin/templates"  # 관리자 템플릿 경로


class TemplateService():
    """템플릿 서비스 클래스
    - TODO: 반응형/적응형 변수 외의 다른 부분도 클래스화 해야한다.
    """
    _is_responsive: bool = None  # 반응형 템플릿 여부

    @classmethod
    def get_responsive(cls) -> bool:
        if cls._is_responsive is None:
            cls.set_responsive()

        return cls._is_responsive
    
    @classmethod
    def set_responsive(cls) -> None:
        load_dotenv()
        cls._is_responsive = (
            TypeAdapter(bool)
            .validate_python(os.getenv("IS_RESPONSIVE", True))
        )


class UserTemplates(Jinja2Templates):
    """
    사용자 Jinja2Template 설정 클래스
    - 사용자에서 반복적으로 사용되는 템플릿 설정을 관리
    - 싱글톤 패턴으로 구현
    """
    _instance = None
    _is_mobile: bool = False
    default_directories = [TEMPLATES_DIR, EDITOR_PATH, CAPTCHA_PATH]

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UserTemplates, cls).__new__(cls)
            cls._instance._initialized = False  # Initialization flag added
        return cls._instance

    def __init__(self,
                 context_processors: dict = None,
                 globals: dict = None,
                 env: Environment = None):
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
            self.env.globals["template_asset"] = template_asset
            # 템플릿 컨텍스트 프로세서 설정
            self.context_processors.append(self._default_context)
            # 추가 env.global 설정
            if globals:
                self.env.globals.update(**globals.__dict__)

    def _default_context(self, request: Request):
        # Lazy import
        from lib.board_lib import render_latest_posts

        context = {
            "current_login_count": get_current_login_count(request),
            "menus": get_menus(),
            "poll": get_recent_poll(),
            "populars": get_populars(),
            "render_latest_posts": render_latest_posts,
            "render_visit_statistics": render_visit_statistics,
        }
        return context

    def TemplateResponse(
        self,
        name: str,
        context: dict,
        status_code: int = 200,
        headers: typing.Optional[typing.Mapping[str, str]] = None,
        media_type: typing.Optional[str] = None,
        background: typing.Optional[BackgroundTask] = None,
    ) -> _TemplateResponse:
        """Jinja2Templates TemplateResponse Override
        
        적응형&모바일 접근일 경우 모바일 템플릿을 우선으로 검색하도록 경로를 재설정한다.
        - mobile 템플릿이 존재하지 않을 경우 기본 템플릿을 자동으로 사용한다.
        - 클래스 변수(_is_mobile)를 통해 이전 요청과 비교하여 변경되었을 경우에만 경로를 재설정한다.
        - 해당 로직은 생성자에서 처리하지 못한다.
        """
        request = context.get("request")
        is_mobile: bool = getattr(request.state, "is_mobile", False)
        if (not TemplateService.get_responsive()
                and self._is_mobile != is_mobile):
            # 경로 우선순위 변경
            if is_mobile:
                self.default_directories.insert(0, f"{TEMPLATES_DIR}/mobile")
            else:
                self.default_directories.remove(f"{TEMPLATES_DIR}/mobile")

            # 템플릿 로더 재설정
            self.env.loader = FileSystemLoader(self.default_directories)
            self._is_mobile = is_mobile

        return super().TemplateResponse(name, context, status_code, headers, media_type, background)


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
            self.env.globals["template_asset"] = template_asset
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


def template_asset(asset_path: str) -> str:
    """
    현재 템플릿의 asset url을 반환하는 헬퍼 함수

    Args:
        asset_path (str): 플러그인 모듈 이름

    Returns:
        asset_url (str): asset url
    """
    template_path = get_template_path()
    template_name = template_path.replace(TEMPLATES + '/', "")

    return f"/template_static/{template_name}/{asset_path}"


def register_template_statics(app: FastAPI) -> None:
    """
    현재 템플릿의 static 경로를 가상의 경로로 등록하는 함수
    - ex) /templates/basic/static/css -> /template_static/basic/css

    Args:
        app (FastAPI): FastAPI 객체
    """
    template_path = get_template_path()
    template_name = template_path.replace(TEMPLATES + '/', "")
    static_directory = f"{TEMPLATES}/{template_name}/static"

    if not os.path.isdir(static_directory):
        logger = logging.getLogger("uvicorn.error")
        logger.warning("template has not static directory")
        return

    url = f"/template_static/{template_name}"
    path = StaticFiles(directory=static_directory)
    app.mount(url, path, name=f"static_{template_name}")  # tag


def get_template_list():
    """템플릿 경로의 템플릿 목록을 리스트로 반환
    
    Returns:
        list: 디렉토리 리스트

    """
    result_array = []

    dirname = os.path.join(TEMPLATES)
    for file in os.listdir(dirname):
        if file in ['.', '..']:
            continue

        template_path = os.path.join(dirname, file)
        file_list = ['readme.txt', 'screenshot.png', 'index.html']
        if (os.path.isdir(template_path)
                and all(os.path.isfile(os.path.join(template_path, fname)) for fname in file_list)):
            result_array.append(file)

    result_array.sort()  # Using Python's default sort which is similar to natsort for strings

    return result_array


def get_template_info(template_name: str) -> dict:
    """템플릿 정보를 반환합니다.

    Args:
        template_name (str): 템플릿 이름

    Returns:
        dict: 템플릿 정보
    """
    info = {}
    path = os.path.join(TEMPLATES, template_name)

    if os.path.isdir(path):
        screenshot = os.path.join(path, 'screenshot.png')
        screenshot_url = ''
        if os.path.isfile(screenshot):
            try:
                with Image.open(screenshot) as img:
                    if img.format == "PNG":
                        screenshot_url = f"/admin/screenshot/{template_name}"
            except:
                pass

        info['screenshot'] = screenshot_url

        text = os.path.join(path, 'readme.txt')
        if os.path.isfile(text):
            with open(text, 'r', encoding="UTF-8") as f:
                content = [line.strip() for line in f.readlines()]

            patterns = [
                ("^Template Name:(.+)$", "template_name"),
                ("^Template URI:(.+)$", "template_uri"),
                ("^Maker:(.+)$", "maker"),
                ("^Maker URI:(.+)$", "maker_uri"),
                ("^Version:(.+)$", "version"),
                ("^Detail:(.+)$", "detail"),
                ("^License:(.+)$", "license"),
                ("^License URI:(.+)$", "license_uri")
            ]

            for line in content:
                for pattern, key in patterns:
                    match = re.search(pattern, line, re.I)
                    if match:
                        info[key] = match.group(1).strip()

        if not info.get('template_name'):
            info['template_name'] = template_name

        info['template_dir'] = template_name

    return info