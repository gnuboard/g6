import re
import importlib
import logging
import json
import os
from dataclasses import dataclass, field, asdict
from filelock import FileLock
from starlette.staticfiles import StaticFiles
from typing import List

import main

# 플러그인 목록을 가져온다.
# 가져온 목록을 import 한다.
# __init__.py 는 필수 __init__.py 가 있어야 파이썬 모듈로 인식한다.
# 추가/활성/비활화한다.

PLUGIN_DIR = 'plugin'
PLUGIN_STATE_FILE = 'plugin_states.json'


@dataclass
class PluginState:
    plugin_name: str  # 관리자 정보 표시 이름
    module_name: str  # 플러그인의 모듈이름
    is_enable: field(default=False)  # on/off 상태


def get_all_plugin_info(plugin_dir):
    """
    플러그인 폴더 내부의 모든 패키지들의 정보를 가져온다. (비활성화 포함)
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
                plugin['is_enable'] = "False"
        all_plugin_info.append(plugin)
    return all_plugin_info


def get_plugin_state_change_time():
    """플러그인 상태 변경 시간을 반환한다.
    Returns:
        mtime (float): 플러그인 상태 변경 시간
    """
    if not os.path.isfile(PLUGIN_STATE_FILE):
        return 0

    return os.path.getmtime(PLUGIN_STATE_FILE)


def get_plugin_info(module_name, plugin_dir=PLUGIN_DIR):
    """
    플러그인 정보를 반환한다.
    Args:
        plugin_dir (str): 플러그인 루트 폴더
        module_name (str): 플러그인 모듈 이름 - 개별 패키지 폴더 이름
    Returns:
        info (dict): 플러그인 정보
    """
    info = {}
    path = os.path.join(plugin_dir, module_name)

    if os.path.isdir(path):
        screenshot = os.path.join(path, 'screenshot.png')
        screenshot_url = ''
        if os.path.isfile(screenshot):
            try:
                from PIL import Image
                img = Image.open(screenshot)
                if img.format == "PNG":
                    screenshot_url = f"/admin/screenshot/{module_name}"
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
    """
    전역 캐시에 저장된 관리자 메뉴를 반환한다.
    Returns:
        admin_menus (list): 관리자 메뉴 목록
    """
    # 전역변수 cache_plugin_menu
    return main.cache_plugin_menu.get('admin_menus')


def delete_router_by_tagname(app, tagname):
    """태그 이름으로 등록된 라우터 삭제
    Args:
        app (FastAPI): FastAPI 인스턴스
        tagname (str): 태그 이름
    """
    filtered_routes = [route_obj for route_obj in app.routes if
                       not (hasattr(route_obj, "tags") and tagname in route_obj.tags)]

    app.router.routes = filtered_routes


def read_plugin_state() -> List[PluginState]:
    """
    플러그인 활성 상태를 plugin_states.json 에서 읽어온다.
    Returns:
        plugin_state (list): PluginState 목록 반환
    Examples:
        플러그인 상태값 변경시
    """
    if not os.path.isfile(PLUGIN_STATE_FILE):
        return []

    lock = FileLock("plugin_states.json.lock",timeout=5)
    with lock:
        with open(PLUGIN_STATE_FILE, 'r', encoding="UTF-8") as file:
            plugin_state = json.load(file)

    plugin_state_list = []

    for plugin in plugin_state:
        state = PluginState(**plugin)
        plugin_state_list.append(state)
    return plugin_state_list


def write_plugin_state(plugin_states: List[PluginState]):
    """
    플러그인 활성 상태를 plugin_states.json 에 기록한다.
    Args:
        plugin_states (list): 플러그인 목록
    Raises:
        Timeout: 파일 lock 에서 Timeout 발생시
    Examples:
        초기 설치, 관리자메뉴에서 플러그인 상태값 변경시에만 사용
    """
    if not os.path.exists(PLUGIN_STATE_FILE):
        with open(PLUGIN_STATE_FILE, 'w', encoding="UTF-8") as file:
            json.dump({}, file, indent=4, ensure_ascii=False)

    if not plugin_states:
        return
    plugin_states_dict = [asdict(plugin) for plugin in plugin_states]

    
    lock = FileLock("plugin_states.json.lock", timeout=5)
    with lock:
        with open(PLUGIN_STATE_FILE, 'w', encoding="UTF-8") as file:
            json.dump(plugin_states_dict, file, indent=4, ensure_ascii=False)


def import_plugin_by_states(plugin_states: List[PluginState], plugin_dir=PLUGIN_DIR) -> List[PluginState]:
    """
    플러그인 상태값에 따라 플러그인을 import 한다.
    Args:
        plugin_dir (str): 플러그인 폴더
        plugin_states (list): 플러그인 상태 목록
    Returns:
        plugin_list (list): 플러그인 목록
    Examples:
        main, 서버시작(프로세스 시작), 관리자 메뉴에서 사용
    """
    plugin_list = []
    for plugin in plugin_states:
        if plugin.is_enable:
            full_module_name = f"{plugin_dir}.{plugin.module_name}"
            importlib.import_module(full_module_name)
            plugin_list.append(plugin)
    return plugin_list


def import_plugin_admin(plugin_states, plugin_dir=PLUGIN_DIR):
    """
    플러그인의 관리자 메뉴를 등록한다.
    이미 import 되어있으면 플러그인의 router 모듈 __init__.py 를 다시 실행한다.
    Args:
        plugin_states (list): 플러그인 상태 목록
        plugin_dir (str): 플러그인 폴더
    Returns:
        admin_menus (list): 관리자 메뉴 목록
    """
    admin_menus = []
    for plugin in plugin_states:
        if plugin.is_enable:
            admin_module_name = f"{plugin_dir}.{plugin.module_name}.admin"
            module = importlib.import_module(admin_module_name)
            if module:
                # 활성화 -> 비활성화 -> 활성화시 삭제된 관리자 라우트를 등록하기 위함
                importlib.reload(module)
            menu = getattr(module, 'admin_menu', None)
            if menu:
                admin_menus.append(menu)
    return admin_menus


def import_plugin_router(plugin_state, plugin_dir=PLUGIN_DIR):
    """
    플러그인의 라우터를 등록한다.
    이미 import 되어있으면 플러그인의 router 모듈 __init__.py 를 다시 실행한다.

    Args:
        plugin_state (list): 플러그인 상태 목록
        plugin_dir (str): 플러그인 폴더
    """
    for plugin in plugin_state:
        if plugin.is_enable:
            router_module_name = f"{plugin_dir}.{plugin.module_name}.router"
            module = importlib.import_module(router_module_name)
            if module:
                # __init__ 실행 활성화 -> 비활성화 -> 활성화시 삭제된 라우터를 등록
                importlib.reload(module)


def register_statics(app, plugin_info: List[PluginState], plugin_dir=PLUGIN_DIR):
    # 하위경로를 먼저 등록하고 상위경로를 등록해야 한다.
    for plugin in plugin_info:
        try:
            app.mount(
                f"/plugin/{plugin.module_name}/static",
                StaticFiles(directory=f"{plugin_dir}/{plugin.module_name}/static"),
                name=f"{plugin.module_name}"
            )
        except Exception as e:
            logging.warning(f"register_statics: {e}")
