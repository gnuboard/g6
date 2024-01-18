import re
import importlib
import logging
import json
import os
from dataclasses import dataclass, field, asdict

import cachetools
from filelock import FileLock
from starlette.staticfiles import StaticFiles
from typing import List

PLUGIN_DIR = 'plugin'
PLUGIN_STATE_FILE = 'plugin_states.json'
PLUGIN_STATE_FILE_PATH = f'{PLUGIN_DIR}/{PLUGIN_STATE_FILE}'

# 전역 캐시
# 플러그인 관리자 메뉴를 저장하는 캐시
cache_plugin_menu = cachetools.Cache(maxsize=1)

# PLUGIN_STATE_FILE 파일읽기를 줄이기 위한 정보와 마지막 변경시간 캐시
# 키 값
# change_time: 플러그인 상태 변경 시간
# info: 플러그인 상태파일을 읽어서 저장한 플러그인 정보
cache_plugin_state = cachetools.Cache(maxsize=2)

# 활성화된 플러그인의 모듈정보를 저장


@dataclass
class PluginState:
    plugin_name: str  # 관리자 정보 표시 이름
    module_name: str  # 플러그인의 모듈이름
    is_enable: field(default=False)  # bool on/off 상태


def get_all_plugin_info(plugin_dir=PLUGIN_DIR):
    """PLUGIN_DIR 폴더 내부의 모든 패키지들 정보를 가져온다. (비활성화된 플러그인 포함)
    Args:
        plugin_dir (str): 플러그인 폴더
    Returns:
        all_plugin_info (list): 플러그인 정보 목록
    """
    plugin_list = []
    for module_name in os.listdir(plugin_dir):
        module_path = os.path.join(plugin_dir, module_name)
        if module_name == '__pycache__':
            continue
        if os.path.isdir(module_path):
            info = get_plugin_info(module_name, plugin_dir)
            info['module_name'] = module_name
            plugin_list.append(info)

    plugin_state = read_plugin_state()
    all_plugin_info = []
    for plugin in plugin_list:
        for state in plugin_state:
            if plugin['module_name'] == state.module_name:
                plugin['is_enable'] = state.is_enable
                break
            else:
                plugin['is_enable'] = False
        all_plugin_info.append(plugin)
    return all_plugin_info


def get_plugin_state_cache():
    """현재 플러그인 상태 파일의 캐시를 가져온다.
    Returns:
        active_plugin_info (dict): 활성화된 플러그인 정보
    """
    return cache_plugin_state.__getitem__('info') or {}


def get_all_plugin_module_names(plugin_dir=PLUGIN_DIR):
    """플러그인 폴더에 있는 모든 플러그인들의 이름을 가져온다. (비활성화 된것 포함)
    Args:
        plugin_dir (str): 플러그인 폴더
    Returns:
        list: plugin_name_list 플러그인 이름 목록
    """
    plugin_names = []
    for module_name in os.listdir(plugin_dir):
        module_path = os.path.join(plugin_dir, module_name)
        if module_name == '__pycache__':
            continue
        if os.path.isdir(module_path):
            plugin_names.append(module_name)
    return plugin_names


def get_plugin_state_change_time():
    """플러그인 상태 변경 시간을 반환한다.
    Returns:
        float: mtime 플러그인 상태 변경 시간
    """
    if not os.path.isfile(PLUGIN_STATE_FILE_PATH):
        return 0

    return os.path.getmtime(PLUGIN_STATE_FILE_PATH)


def get_plugin_info(module_name, plugin_dir=PLUGIN_DIR):
    """플러그인 정보를 반환한다.
    Args:
        module_name (str): 플러그인 모듈 이름 - 개별 패키지 폴더 이름
        plugin_dir (str): 플러그인 루트 폴더
    Returns:
        dict: info 플러그인 정보
    """
    info = {}
    path = os.path.join(plugin_dir, module_name)

    if os.path.isdir(path):
        screenshot = os.path.join(path, 'screenshot.png')
        screenshot_url = ''
        if os.path.isfile(screenshot):
            try:
                from PIL import Image
                with Image.open(screenshot) as img:
                    if img.format == "PNG":
                        screenshot_url = f"/admin/plugin/screenshot/{module_name}"
            except:
                pass
        info['screenshot'] = screenshot_url
        info['module_name'] = module_name

        text = os.path.join(path, 'readme.txt')
        if not os.path.isfile(text):
            return info

        with open(text, 'r', encoding="UTF-8") as f:
            content = [line.strip() for line in f.readlines()]

        patterns = [
            ("^Plugin Name:(.+)$", "plugin_name"),
            ("^Plugin URI:(.+)$", "plugin_uri"),
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

    return info


def get_admin_plugin_menus():
    """전역 캐시에 저장된 관리자 메뉴를 반환한다.
    Returns:
        list: 관리자 메뉴 목록
    """
    # 전역변수 cache_plugin_menu 에서 가져온다
    return cache_plugin_menu.get('admin_menus')


def delete_router_by_tagname(app, tagname: str):
    """태그 이름으로 등록된 라우터 삭제
    Args:
        app (FastAPI): FastAPI 객체
        tagname (str): 태그 이름
    """
    filtered_routes = [route_obj for route_obj in app.routes if
                       not (hasattr(route_obj, "tags") and tagname in route_obj.tags)]

    app.router.routes = filtered_routes


def read_plugin_state() -> List[PluginState]:
    """플러그인 활성 상태를 plugin_states.json 에서 읽는다.
    Returns:
        PluginState 목록 반환
    Examples:
        플러그인 상태값 변경시 읽는다.
    """
    if not os.path.isfile(PLUGIN_STATE_FILE_PATH):
        return []

    lock = FileLock(f"{PLUGIN_DIR}/{PLUGIN_STATE_FILE}.lock", timeout=5)
    plugin_state = []
    with lock:
        with open(PLUGIN_STATE_FILE_PATH, 'r', encoding="UTF-8") as file:
            # 파일내용 체크등 미리 읽으면 데이터가 사라지므로.
            # json.load() 를 바로 호출해야한다.
            try:
                plugin_state = json.load(file)
            except Exception as e:
                # plugin_states.json 파일이 json 포맷에 안맞을 경우 플러그인 로딩을 못한다.
                # 빈 파일은 오류가 발생한다. 에러메시지: 'Expecting value: line 1 column 1 (char 0)'
                # json 포맷에 맞게 고치거나 plugin_states.json 파일을 지우고 플러그인을 관리자에서 새로 설정해야한다.
                logging.critical("/plugin/plugin_states.json json validate error. not load any plugin!.")
                logging.critical("It's not allow empty file. check json format. "
                                 f"or remove {PLUGIN_STATE_FILE} file.")
                logging.critical(e)

    plugin_state_list = []

    for plugin in plugin_state:
        state = PluginState(**plugin)
        plugin_state_list.append(state)
    return plugin_state_list


def write_plugin_state(plugin_states: List[PluginState]):
    """플러그인 활성 상태를 plugin_states.json 에 기록한다.
    Args:
        plugin_states (list): 플러그인 목록
    Raises:
        Timeout: 파일 lock 에서 Timeout 발생시
    Examples:
        초기 설치, 관리자메뉴에서 플러그인 상태값 변경시에만 사용
    """
    if not os.path.exists(PLUGIN_STATE_FILE_PATH):
        with open(PLUGIN_STATE_FILE_PATH, 'w', encoding="UTF-8") as file:
            json.dump({}, file, indent=4, ensure_ascii=False)

    if not plugin_states:  # [] 빈 리스트
        return
    plugin_states_dict = [asdict(plugin) for plugin in plugin_states]

    lock = FileLock(f"{PLUGIN_DIR}/{PLUGIN_STATE_FILE}.lock", timeout=5)
    with lock:
        with open(PLUGIN_STATE_FILE_PATH, 'w', encoding="UTF-8") as file:
            json.dump(plugin_states_dict, file, indent=4, ensure_ascii=False)


def import_plugin_by_states(plugin_states: List[PluginState], plugin_dir=PLUGIN_DIR) -> List[PluginState]:
    """플러그인 상태값에 따라 플러그인을 import 한다.
    Args:
        plugin_states (list): 플러그인 상태 목록
        plugin_dir (str): 플러그인 폴더
    Returns:
        List[PluginState] : 플러그인 목록
    Examples:
        main, 그누보드 시작 (프로세스 시작)
    """
    plugin_list = []
    for plugin in plugin_states:
        if plugin.is_enable:
            full_module_name = f"{plugin_dir}.{plugin.module_name}"
            importlib.import_module(full_module_name)
            plugin_list.append(plugin)
    return plugin_list


def register_plugin_admin_menu(plugin_states, plugin_dir=PLUGIN_DIR):
    """플러그인의 관리자 메뉴를 등록한다.
    Args:
        plugin_states (list): 플러그인 상태 목록
        plugin_dir (str): 플러그인 폴더
    Returns:
        list: admin_menus 관리자 메뉴 목록
    """
    admin_menus = []
    for plugin in plugin_states:
        if plugin.is_enable:
            admin_module_name = f"{plugin_dir}.{plugin.module_name}.admin"
            module = importlib.import_module(admin_module_name)
            if module:
                get_menu_function = getattr(module, 'register_admin_menu', None)
                if get_menu_function:
                    admin_menus.append(get_menu_function())
    return admin_menus


def register_plugin(plugin_states, plugin_dir=PLUGIN_DIR):
    """플러그인의 관리자 메뉴를 등록한다.
    Args:
        plugin_states (list): 플러그인 상태 목록
        plugin_dir (str): 플러그인 폴더
    Returns:
        list: admin_menus 관리자 메뉴 목록
    """
    for plugin in plugin_states:
        if plugin.is_enable:
            module_name = f"{plugin_dir}.{plugin.module_name}"
            module = importlib.import_module(module_name)
            if module:
                register_function = getattr(module, 'register_plugin', None)
                if register_function:
                    register_function()
                    logging.info(f"register_plugin: {module_name}")


def unregister_plugin(plugin_states, plugin_dir=PLUGIN_DIR):
    """등록된 플러그인을 해제한다. unregister_plugin() 을 실행.
    Args:
        plugin_states (list): 플러그인 상태 목록
        plugin_dir (str): 플러그인 폴더
    Returns:
        list: admin_menus 관리자 메뉴 목록
    """
    for plugin in plugin_states:
        if not plugin.is_enable:
            module_name = f"{plugin_dir}.{plugin.module_name}"
            module = importlib.import_module(module_name)
            if module:
                unregister_function = getattr(module, 'unregister_plugin', None)
                if unregister_function:
                    unregister_function()
                    logging.info(f"unregister_plugin: {module_name}")


def register_statics(app, plugin_info: List[PluginState], plugin_dir=PLUGIN_DIR):
    """플러그인의 static 을 등록한다.
    Args:
        app: FastAPI()
        plugin_info: 등록할 플러그인 정보
        plugin_dir: 플러그인 폴더
    """
    for plugin in plugin_info:
        try:
            app.mount(
                f"/plugin/{plugin.module_name}/static",
                StaticFiles(directory=f"{plugin_dir}/{plugin.module_name}/static"),
                name=f"{plugin.module_name}"
            )
        except Exception as e:
            logging.warning(f"register_statics: {e}")
