import os

from dotenv import load_dotenv
from settings import APP_IS_DEBUG


# import 순환참조로 인해 common.py 에 둘 수없음.
def load_gnuboard_env():
    """
    그누보드 6의 설정로딩
    """

    if APP_IS_DEBUG:
        load_dotenv("dev.env", verbose=True)
    else:
        load_dotenv("prod.env", verbose=True)
