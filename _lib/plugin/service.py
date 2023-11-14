import logging
import os
import pkgutil
import importlib

from starlette.staticfiles import StaticFiles

# 패키지 목록을 가져온다.
# 가져온 목록을 import 한다.
# __init__.py 가 있어야 패키지로 인식한다. - 파이썬 기본사양
# __init__.py 는 필수.
# on/off 기능을 에따라 제외한다.

# ------------------
# - 등록
# 사용가능한 패키지 목록을 순회.
PLUGIN_DIR = '_plugin'


def get_plugin_names():
    plugin_list = []
    for plugin in os.listdir(PLUGIN_DIR):
        if os.path.isdir(os.path.join(PLUGIN_DIR, plugin)):
            plugin_list.append(plugin)

    if '__pycache__' in plugin_list:
        plugin_list.remove('__pycache__')
    return plugin_list


def load_all_plugin(plugin_dir):
    """
    플러그인 폴더 내부의 모든 패키지들을 로드한다.
    {plugin_name, plugin_id, is_enable} 의 리스트를 반환한다.
    Args:
        plugin_dir (str): 플러그인 폴더
    Returns:
        plugin_list (list): 플러그인 목록
    Examples:
        main, 서버시작, 프로세스 시작시
    """
    plugin_list = []
    # pkgutil 로 서브디렉토리의 모듈을 가져온다.
    package = importlib.import_module(plugin_dir)
    for _, module_name, _ in pkgutil.walk_packages(package.__path__):
        full_module_name = f"{plugin_dir}.{module_name}"
        module = importlib.import_module(full_module_name)
        if '__pycache__' in plugin_list:
            continue
        plugin_info = {
            "plugin_name": module.__plugin_name__,
            "plugin_id": module.__plugin_id__,
            "module_name": module_name,
            "is_enable": True,
        }
        plugin_list.append(plugin_info)

    return plugin_list


def plugin_state_setting(plugin_states, plugin_info):
    """플러그인 활성화/비활성화 상태를 설정한다.
    Args:
        plugin_info (list): 플러그인 목록
        plugin_states (list): 플러그인 상태 목록
    Returns:
        plugin_list (list): 플러그인 목록
    Examples:
        플러그인 상태값 변경시
    """
    for plugin in plugin_info:
        for state in plugin_states:
            if plugin["plugin_id"] == state["plugin_id"]:
                plugin["is_enable"] = state["is_enable"]
    return plugin_info


def plugin_import(package_name):
    """개별 플러그인 패키지 모든 python 파일들을 import 한다
    Args:
        package_name (str): 패키지 이름
    Examples:
        개별 플러그인의 __init__.py 에서 호출
        plugin's __init__.py
    """
    # sub directory 의 모듈을 import 한다.
    package = importlib.import_module(package_name)
    for _, module, _ in pkgutil.walk_packages(package.__path__):
        full_module_name = f"{package_name}.{module}"
        if module == 'static':  # static 폴더는 제외한다.
            continue

        importlib.import_module(full_module_name)


def register_statics(app, plugin_info):
    # 하위경로를 먼저 등록하고 상위경로를 등록해야 한다.
    for plugin in plugin_info:
        module_name = plugin['module_name']
        try:
            app.mount(f"/static/plugin/{module_name}", StaticFiles(directory=f"{PLUGIN_DIR}/{module_name}/static"),
                      name=f"{module_name}")
        except Exception as e:
            logging.warning(f"register_statics: {e}")


def register_admin(admin_menu, plugin_id):
    """
    서버시작(프로세스 시작)할 때 관리자에 등록한다.
    """
    for menu in admin_menu:
        menu['id'] = plugin_id
        menu['permission'] = f"{plugin_id}_[{menu['permission']}]"


def unregister_admin(off_plugins, admin_menu):
    """
    플러그인의 관리자 메뉴를 비활성화 한다.
    Args:
        off_plugins (list): 비활성화된 플러그인 목록
        admin_menu (list): 관리자 메뉴 목록
    Returns:
        admin_menu (list): 관리자 메뉴 목록
    Examples:
        프로세스간 불일치 해결, 전역변수 관리를 위해
        관리자페이지 접속 할때마다 미들웨어에서 실행
    """
    # 앞서 비활성화를 했고 신규에서 비활성화 되지않은
    # 플러그인은 활성화 된것이므로 true 로 설정한다.
    for plugin_id in off_plugins:
        for menu in admin_menu:
            if menu['id'] == plugin_id:
                menu['disable'] = True
            else:
                menu['disable'] = False
    return admin_menu


def delete_router_by_tagname(app, tagname):
    """태그 이름으로 등록된 라우터 삭제
    Args:
        app (FastAPI): FastAPI 인스턴스
        tagname (str): 태그 이름
    """
    app.router.routes = [item for item in app.routes
                         if not hasattr(item, "tags") or tagname not in getattr(item, "tags")]


def unregister_plugin(plugin_state, app):
    """
    플러그인을 비활성화 한다.
    Args:
        plugin_state (list): 플러그인 상태 목록
        app (FastAPI): FastAPI 인스턴스
    """
    for plugin_id in plugin_state:
        # 플러그인 라우터는 plugin_id 가 tagname 이다.
        delete_router_by_tagname(app, plugin_id)
