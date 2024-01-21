import typing

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from pydantic import TypeAdapter
from starlette.background import BackgroundTask
from starlette.staticfiles import StaticFiles
from starlette.templating import _TemplateResponse

from core.plugin import (
    get_admin_plugin_menus, get_all_plugin_module_names, PLUGIN_DIR, get_plugin_state_cache
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


def get_current_theme() -> str:
    """현재 설정된 테마를 반환
    - 설정된 테마가 존재하지 않을 경우 기본 테마를 반환

    Returns:
        str: 테마 이름
    """
    default_theme = "basic"
    try:
        with DBConnect().sessionLocal() as db:
            theme = db.scalar(select(Config.cf_theme)) or default_theme
            return theme
    except Exception:
        return default_theme


def get_theme_path() -> str:
    """기본환경설정 > 테마의 설정 경로를 반환
    - 설정된 테마가 존재하지 않을 경우 기본 테마를 반환

    Returns:
        str: 테마 경로
    """
    default_theme_path = f"{TEMPLATES}/basic"

    theme = get_current_theme()
    theme_path = f"{TEMPLATES}/{theme}"

    # 실제 테마가 존재하는지 확인            
    if not os.path.exists(theme_path):
        return default_theme_path

    return theme_path
    

def get_admin_theme_path() -> str:
    """관리자 > 테마의 설정 경로를 반환
    - .env 파일에서 설정된 테마를 조회하여 반환
    - 설정된 테마가 존재하지 않을 경우 기본 테마를 반환

    Returns:
        str: 테마 경로
    """
    default_theme = "basic"
    default_theme_path = f"{ADMIN_TEMPLATES}/{default_theme}"
    try:
        theme = os.getenv("ADMIN_THEME", "basic")
        theme_path = f"{ADMIN_TEMPLATES}/{theme}"

        # 실제 테마가 존재하는지 확인            
        if not os.path.exists(theme_path):
            return default_theme_path

        return theme_path
    except Exception:
        return default_theme_path


TEMPLATES = "templates"
TEMPLATES_DIR = get_theme_path()  # 사용자 템플릿 경로

ADMIN_TEMPLATES = "admin/templates"
ADMIN_TEMPLATES_DIR = get_admin_theme_path()  # 관리자 템플릿 경로

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
    default_directories = [TEMPLATES_DIR, EDITOR_PATH, CAPTCHA_PATH, PLUGIN_DIR]

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
            self.env.globals["theme_asset"] = theme_asset
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

        return super().TemplateResponse(
            name=name,
            context=context,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background
        )
    


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
            self.env.globals["get_plugin_state_cache"] = get_plugin_state_cache
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
            "admin_menus": get_admin_menus(),
            "version": read_version()
        }
        return context


def theme_asset(request: Request, asset_path: str) -> str:
    """
    현재 테마의 asset url을 반환하는 헬퍼 함수

    Args:
        request (Request): Request 객체
        asset_path (str): 플러그인 모듈 이름

    Returns:
        asset_url (str): asset url
    """
    theme = get_current_theme()
    mobile_dir = "/mobile" if request.state.is_mobile else ""

    return f"/theme_static/{theme}{mobile_dir}/{asset_path}"


def register_theme_statics(app: FastAPI) -> None:
    """
    현재 테마의 static 경로를 가상의 경로로 등록하는 함수
    - ex) PC: /{theme}/basic/static/css -> /theme_static/basic/css
    - ex) Mobile: /{theme}/basic/mobile/static/css -> /theme_static/basic/mobile/css

    Args:
        app (FastAPI): FastAPI 객체
    """
    theme = get_current_theme()
    directories = ["/mobile", ""]
    for directory in directories:
        static_directory = f"{TEMPLATES}/{theme}{directory}/static"

        if not os.path.isdir(static_directory):
            # logger = logging.getLogger("uvicorn.error")
            # logger.warning("theme has not static directory : ",
            #                static_directory)
            continue

        url = f"/theme_static/{theme}{directory}"
        path = StaticFiles(directory=static_directory)
        static_device = directory.replace("/", "_")
        app.mount(url, path, name=f"static_{theme}{static_device}")  # tag


def get_theme_list():
    """테마 디렉토리의 목록을 리스트로 반환
    
    Returns:
        list: 디렉토리 리스트

    """
    result_array = []

    dirname = os.path.join(TEMPLATES)
    for file in os.listdir(dirname):
        if file in ['.', '..']:
            continue

        theme_path = os.path.join(dirname, file)
        file_list = ['readme.txt', 'screenshot.png', 'index.html']
        if (os.path.isdir(theme_path)
                and all(os.path.isfile(os.path.join(theme_path, fname)) for fname in file_list)):
            result_array.append(file)

    result_array.sort()  # Using Python's default sort which is similar to natsort for strings

    return result_array


def get_theme_info(theme_name: str) -> dict:
    """테마 정보를 반환합니다.

    Args:
        theme_name (str): 테마 이름

    Returns:
        dict: 테마 정보
    """
    info = {}
    path = os.path.join(TEMPLATES, theme_name)

    if os.path.isdir(path):
        screenshot = os.path.join(path, 'screenshot.png')
        screenshot_url = ''
        if os.path.isfile(screenshot):
            try:
                with Image.open(screenshot) as img:
                    if img.format == "PNG":
                        screenshot_url = f"/admin/screenshot/{theme_name}"
            except:
                pass

        info['screenshot'] = screenshot_url

        text = os.path.join(path, 'readme.txt')
        if os.path.isfile(text):
            with open(text, 'r', encoding="UTF-8") as f:
                content = [line.strip() for line in f.readlines()]

            patterns = [
                ("^Theme Name:(.+)$", "theme_name"),
                ("^Theme URI:(.+)$", "theme_uri"),
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

        if not info.get('theme_name'):
            info['theme_name'] = theme_name

        info['theme_dir'] = theme_name

    return info