import importlib
import logging
import pkgutil

from sqlalchemy import select, inspect

from core.database import DBConnect
from core.models import Config
from lib.social.social import register_social_provider

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


with DBConnect().sessionLocal() as db:
    # 설치되기 전에는 config 테이블이 없으므로 확인.
    if inspect(DBConnect().engine).has_table(DBConnect().table_prefix + "config"):
        try:
            config = db.scalar(select(Config))
            # 서버시작시 소셜로그인 설정을 불러온다.
            register_social_provider(config)
        except Exception as e:
            logging.warning("소셜로그인 설정을 불러올 수 없습니다. " + str(e.args[0]))
