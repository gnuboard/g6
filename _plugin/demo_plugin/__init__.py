from _lib.plugin.service import PLUGIN_DIR, plugin_import

module_name = "demo_plugin"
package_name = f"{PLUGIN_DIR}.{module_name}"
import_list = plugin_import(package_name=package_name)

# 패키지 외부에서 접근 가능한 모듈 목록
# "static" 폴더는 제외한다.
__all__ = [
    # "templates",
    "admin",
    "router",
]
