from _lib.plugin.service import PLUGIN_DIR, plugin_import

module_name = "demo_plugin"
plugin_import(package_name=f"{PLUGIN_DIR}.{module_name}")

__version__ = "0.0.1"
__plugin_id__ = 'demo_plugin_id'
__plugin_name__ = "데모 플러그인"

# 패키지 외부에서 접근 가능한 모듈 목록
# "static" 폴더는 제외한다.
__all__ = [
    "admin",
    "router",
]
