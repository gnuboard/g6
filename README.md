# gnuboard with python

.env

```
# mysql, postgresql, sqlite3
DB_ENGINE = ""
DB_HOST = ""
DB_PORT = ""
DB_USER = ""
DB_PASSWORD = ""
DB_NAME = ""

# 테이블명 앞에 붙는 이름
# g6_ 로 설정시
# 예) g6_config, g6_member, g6_board
DB_TABLE_PREFIX = "g6_"

SMTP_SERVER="localhost"
SMTP_PORT=25
SMTP_USERNAME="username" # 메일 테스트시 보내는 사용자 이름 및 이메일 주소 반드시 넣어야 함 SMTP_USERNAME="username@domain.com"
SMTP_PASSWORD=""

# 디버그 모드 설정 (True/False)
APP_IS_DEBUG = "False"

# 네이버 메일 설정
# SMTP_SERVER="smtp.naver.com"
# SMTP_PORT=465 # 보안 연결(SSL) 필요
# SMTP_USERNAME="네이버 로그인 아이디"
# SMTP_PASSWORD="네이버 로그인 비밀번호"


# 웹사이트 표시 방법
# "True" (기본값) : 반응형 웹사이트 (참고: 반응형 템플릿만 제공합니다.)
# "False" : 적응형 웹사이트
IS_RESPONSIVE = "False" # 반드시 문자열로 입력해야 합니다.


```

아직 postgresql, sqlite3 는 정상 작동하지 않음
mysql 관련 코드로 작성하면 안됨. 예) TINYINT
