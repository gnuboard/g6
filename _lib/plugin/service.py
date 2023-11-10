import os
from main import app

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


def get_plugin_list():
    plugin_list = []
    for plugin in os.listdir(PLUGIN_DIR):
        if os.path.isdir(os.path.join(PLUGIN_DIR, plugin)):
            plugin_list.append(plugin)

    if '__pycache__' in plugin_list:
        plugin_list.remove('__pycache__')
    return plugin_list


def delete_admin():
    pass


def set_admin():
    pass


def set_router():
    pass


def set_static():
    pass


def delete_static():
    pass


def delete_router_by_tagname(tagname):
    """태그 이름으로 라우터 삭제"""
    app.router.routes = [item for item in app.routes
                         if not hasattr(item, "tags") or tagname not in getattr(item, "tags")]
