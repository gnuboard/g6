import importlib
import pkgutil

from _lib.plugin.service import PLUGIN_DIR

package_name = f"{PLUGIN_DIR}.demo_plugin"

# pkgutil 로 서브디렉토리의 모듈을 가져온다.
package = importlib.import_module(package_name)

# sub directory 의 모듈을 import 한다.
for _, module_name, _ in pkgutil.walk_packages(package.__path__):
    full_module_name = f"{package_name}.{module_name}"
    if module_name == 'static':  # static 폴더는 제외한다.
        continue
    importlib.import_module(full_module_name)

# 패키지 외부에서 접근 가능한 모듈 목록
# "static" 폴더는 제외한다.
__all__ = [
    # "templates",
    "admin",
    "router",
]
