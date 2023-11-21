# Path: lib/social/social.py
import pkgutil
import importlib
from lib.social.social import register_social_provider
from common.database import SessionLocal
from common.models import Config

# Package.
package_name = 'lib.social.providers'

# pkgutil 로 서브디렉토리의 모듈을 가져온다.
package = importlib.import_module(package_name)
for _, module_name, _ in pkgutil.walk_packages(package.__path__):
    full_module_name = f"{package_name}.{module_name}"
    imported_module = importlib.import_module(full_module_name)

__all__ = [
    "google",
    "facebook",
    "naver",
    "kakao",
    "twitter",
]

with SessionLocal() as db:
    config = db.query(Config).first()
    register_social_provider(config)
