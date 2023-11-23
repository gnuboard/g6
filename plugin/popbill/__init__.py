module_name = "popbill"
__plugin_name__ = "팝빌 플러그인"

# 패키지 외부에서 접근 가능한 모듈 목록
# "static" 폴더는 제외한다.
__all__ = [
    "admin",
    "router",
    "module_name"
]

POPBILL_LINK_ID = "TESTER"
POPBILL_SECRET_KEY = ""
# 연동환경 설정값, 개발용(True), 상업용(False)
POPBILL_IS_TEST = True

# 인증토큰 IP제한기능 사용여부, 권장(True)
POPBILL_IP_RESTRICT_ON_OFF = True

# 팝빌 API 고정 IP 사용여부, True-사용 False-미사용, 기본값(false)
POPBILL_UseStaticIP = False

# 로컬시스템 시간 사용여부, 권장(True)
POPBILL_UseLocalTimeYN = True