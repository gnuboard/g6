from dotenv import load_dotenv

# import 순환참조로 인해 common.py 에 둘 수없음.
def load_gnuboard_env():
    """
    그누보드 6의 설정로딩
    """
    load_dotenv(".env", verbose=True)