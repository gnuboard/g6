import logging
import os
import pkgutil
import importlib

from starlette.staticfiles import StaticFiles

# import _plugin's forlder
# required : admin, router, templates

# import _plugin's sub forlder (if exists)
# whole files in _plugin's sub forlder are imported
# 패키지 목록을 가져온다.
# 가져온 목록을 import 한다.
# __init__.py 가 있어야 패키지로 인식한다. - 파이썬 기본사양
# __init__.py 는 필수.
# on/off 기능을 에따라 off 된것은  배열에서 제외한다.

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
    """
    plugin_list = []
    # pkgutil 로 서브디렉토리의 모듈을 가져온다.
    package = importlib.import_module(plugin_dir)
    for _, module_name, _ in pkgutil.walk_packages(package.__path__):
        full_module_name = f"{plugin_dir}.{module_name}"
        importlib.import_module(full_module_name)
        plugin_list.append(module_name)

    if '__pycache__' in plugin_list:
        plugin_list.remove('__pycache__')
    return plugin_list


def plugin_import(package_name):
    """
    개별 플러그인 패키지 모든 python 파일들을 import 함다
    """
    # sub directory 의 모듈을 import 한다.
    package = importlib.import_module(package_name)
    for _, module, _ in pkgutil.walk_packages(package.__path__):
        full_module_name = f"{package_name}.{module}"
        if module == 'static':  # static 폴더는 제외한다.
            continue

        importlib.import_module(full_module_name)


def register_statics(app, import_list):
    # 하위경로를 먼저 등록하고 상위경로를 등록해야 한다.
    for module_name in import_list:
        try:
            app.mount(f"/static/plugin/{module_name}", StaticFiles(directory=f"{PLUGIN_DIR}/{module_name}/static"),
                      name=f"{module_name}")
        except Exception as e:
            logging.critical(f"register_statics: {e}")


def register_admin():
    pass


def unregister_admin():
    pass


def delete_router_by_tagname(app, tagname):
    """태그 이름으로 등록된 라우터 삭제
    """
    app.router.routes = [item for item in app.routes
                         if not hasattr(item, "tags") or tagname not in getattr(item, "tags")]


def unregister_plugin():
    """
    플러그인을 비활성화 한다.
    """
    # unregister_admin()
    # delete_router_by_tagname()
