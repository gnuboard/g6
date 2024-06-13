"""소셜 로그인 제공자 패키지"""
import importlib
import pkgutil

# Package.
SOCIAL_PROVIDERS_PACKAGE_NAME = 'lib.social.providers'

# pkgutil 로 서브디렉토리의 모듈을 가져온다.
package = importlib.import_module(SOCIAL_PROVIDERS_PACKAGE_NAME)
for module in pkgutil.walk_packages(package.__path__):
    module_name = module.name
    full_module_name = f"{SOCIAL_PROVIDERS_PACKAGE_NAME}.{module_name}"
    imported_module = importlib.import_module(full_module_name)

__all__ = [
    "google",
    "facebook",
    "naver",
    "kakao",
    "twitter",
]
