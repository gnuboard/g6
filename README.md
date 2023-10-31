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

SMTP_SERVER="localhost"
SMTP_PORT=25
SMTP_USERNAME="username" # 메일 테스트시 보내는 사용자 이름 및 이메일 주소 반드시 넣어야 함 SMTP_USERNAME="username@domain.com"
SMTP_PASSWORD=""

# 네이버 메일 설정
# SMTP_SERVER="smtp.naver.com"
# SMTP_PORT=465 # 보안 연결(SSL) 필요
# SMTP_USERNAME="네이버 로그인 아이디"
# SMTP_PASSWORD="네이버 로그인 비밀번호"


```

아직 postgresql, sqlite3 는 정상 작동하지 않음
mysql 관련 코드로 작성하면 안됨. 예) TINYINT
