
# GNUBOARD6 with Python
<p align="center">
   <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/fastapi?logo=python&color=%233776AB">
   <a href='https://g6.demo.sir.kr/' target='_blank'>
      <img alt="Static Badge" src="https://img.shields.io/badge/G6%20Demo-%234d0585">
   </a>
</p>

## 데모 사이트
- [https://g6.demo.sir.kr/](https://g6.demo.sir.kr/)


## 시작하기
### 1. 설치
- Git을 사용한 설치를 권장합니다.
- 루트 디렉토리에 `.env` 파일이 없다면 설치를 자동으로 진행합니다.

#### 설치 방법
```bash
# Github에서 그누보드6 복사 및 설치합니다.
git clone https://github.com/gnuboard/g6.git
```

```bash
# cd 명령어를 이용하여 g6 디렉토리로 이동합니다.
cd g6
```

```bash
# 가상환경을 만듭니다. 필수 설치 요소는 아닙니다.
python -m venv venv
source venv/bin/activate
```

```bash
# 실행에 필요한 파이썬 패키지들을 설치합니다.
pip install -r requirements.txt
```

```bash
# uvicorn을 이용하여 그누보드6을 실행합니다.
# 기본적으로 8000번 포트를 사용합니다.

# Window
uvicorn main:app --reload

# 외부서버
uvicorn main:app --reload --host {서버IP}
```

#### 그누보드6 데이터베이스 설정 방법
1. 웹브라우저를 열고 **http://127.0.0.1:8000** 로 접속합니다.
   - Windows의 경우: 브라우저에서 http://127.0.0.1:8000 으로 접속
   - 외부서버의 경우: 브라우저에서 http://IP주소:8000 으로 접속
      - 외부서버의 아이피가 49.247.14.5 인 경우 http://49.247.14.5:8000 으로 접속하세요.

2. `.env 파일이 없습니다. 설치를 진행해 주세요.` 라는 경고창과 함께 설치 페이지로 이동합니다.

3. 설치 메인페이지에서 설치할 그누보드버전, 파이썬버전, FastAPI버전 및 안내 사항을 확인할 수 있습니다.

4. 그누보드6 라이센스를 확인하고 동의합니다.

5. 데이터베이스 설정을 진행합니다.
   - **MySQL, PostgreSQL, SQLite** 중 하나의 데이터베이스를 선택하여 설정할 수 있습니다.
      - MySQL, PostgreSQL : 연결에 필요한 정보들을 입력합니다.
      - SQLite : 연결정보가 필요 없으며, 설치 시 루트 디렉토리에 `sqlite3.db` 데이터베이스 파일이 생성됩니다.
   - 접두사를 입력합니다. 
      - `{영문+숫자}_` 형식으로 입력해야 합니다.
      - 기본값은 `g6_` 입니다(예: gnuboard6_)
   - 재설치 여부를 체크합니다. (선택)
      > **Warning**  
      > 재설치는 테이블을 삭제 후 재생성합니다. 기존 데이터가 망실될 수 있으니 주의하시기 바랍니다.

6. 관리자 정보를 입력합니다. 입력한 정보를 바탕으로 관리자 계정이 생성됩니다.

7. 설치를 진행합니다. 설치 내용에 따라 순차적으로 진행되며, 설치가 완료되면 설치완료 문구가 출력됩니다.

8. 이제부터 자유롭게 그누보드6를 사용할 수 있습니다.

### 2. 디렉토리 구조
#### admin
관리자 관련 파일들이 포함되어 있습니다.  
router, template 파일 및 관리자 메뉴를 설정하는 .json 파일이 속해 있습니다.

#### bbs
사용자 관련 router가 위치합니다. 요청에 따라 여러가지 기능들을 수행합니다.

#### core
프로젝트의 **핵심 코드**가 위치합니다. 데이터베이스 연결, 미들웨어 실행, 템플릿 엔진 설정 등 기본적인 실행에 필요한 코드를 포함하고 있습니다.
```
core
├─ database.py  # 데이터베이스 연결 및 세션 관리
├─ exception.py  # 예외 처리설정 클래스 & 함수
├─ formclass.py  # @dataclass를 이용한 폼 클래스 모음
├─ middleware.py  # 미들웨어 설정
├─ models.py  # 데이터베이스 모델
├─ plugin.py  # 플러그인 관련 함수
└─ template.py  # 템플릿 엔진 설정
```

#### data
data 디렉토리는 이미지 및 파일을 저장하기 위한 디렉토리 입니다.  
초기에는 존재하지 않으며, 설치 진행 시 자동으로 생성됩니다.

#### install
설치 관련 파일들이 포함되어 있습니다.

#### lib
프로젝트에서 사용되는 여러 함수들을 포함한 디렉토리, 파일들이 속해 있습니다.
```
lib
├─ captcha  # 캡차 관련 함수, 템플릿 (Google reCAPTCHA v2, v2 invisible)
├─ editor  # 에디터 관련 함수, 템플릿 (ckeditor4)
├─ social  # 소셜 로그인 관련 함수 (naver, kakao, google, facebook, twitter)
├─ board_lib.py  # 게시판 관련 함수
├─ common.py  # 공통 함수
├─ dependencies.py  # 종속성 함수
├─ member_lib.py  # 회원 관련 함수
├─ pbkdf2.py  # 암호화 라이브러리
├─ point.py  # 포인트 함수
├─ template_filters.py  # 템플릿 필터 함수
├─ template_functions.py  # 템플릿 출력 관련 함수 모음
└─ token.py  # 토큰 함수
```
#### plugin
사용자가 만든 독립된 기능을 저장하는 디렉토리 입니다.
1. 플러그인 제작
   - `/plugin` 폴더에 제작할 플러그인 디렉토리를 추가합니다.
   - 다른 플러그인과 겹치지 않도록 고유한 이름으로 지어주세요.
   - 아래 파일 구성과 `plugin/demo_plugin`디렉토리를 참고하여 플러그인을 제작합니다.
```
plugin
├─ {플러그인1}
   └─ admin  # 관리자 라우터&메뉴 설정
      ├─ __init__.py 
      └─ admin_router.py
   ├─ static  # css, js, image 등 정적 파일
   ├─ templates  # 템플릿 파일
   ├─ user  # 사용자 라우터 설정
   ├─ __init__.py  # 플러그인 초기화 파일
   ├─ models.py  # 데이터베이스 모델
   ├─ plugin_config.py  # 플러그인 설정 파일
   ├─ readme.txt  # 플러그인 상세정보
   ├─ screenshot.png  # 대표 이미지
├─ {플러그인2}
...
└─ plugin_states.json  # 전체 플러그인 정보 파일
```
2. 관리자 메뉴 주소등록
   - `plugin_config.py` > `admin_menu` 딕셔너리에 추가할 url, name을 등록합니다.
      - 등록한 메뉴는 `admin > __init__.py > register_admin_menu()` 함수를 통해 관리자메뉴에 등록됩니다.

#### static
css, js, image 등 정적 파일을 저장하는 디렉토리 입니다.

#### templates
템플릿 파일을 저장하는 디렉토리 입니다.   
여러개의 템플릿으로 구성할 수 있으며 **관리자페이지 > 템플릿관리** 메뉴에서 템플릿을 변경할 수 있습니다.
```
templates
├─ {템플릿1}
   └─ ...
├─ {템플릿2}
   └─ ...
...
```
- 반응형/적응형
   - `.env`파일의 `IS_RESPONSIVE` 설정 값에 따라 반응형/적응형 웹사이트로 표시됩니다. 적응형일 경우에만 `templates/{템플릿}/moblile` 디렉토리를 생성하여 모바일 화면을 따로 구성할 수 있습니다. 
   - 모바일 화면이 없을경우 자동으로 반응형(PC) 웹사이트로 표시됩니다.

#### .env(.example.env)
사용자 설정에 필요한 파일입니다. 설치 진행 시, `.example.env`을 복사해서 `.env`파일을 자동으로 생성합니다.
   - `.example.env`는 `.env`파일을 생성하기 위한 예제 파일이므로 삭제하지 않는 것을 추천합니다.

입니다. 설치 진행 시, 

#### main.py
프로젝트의 시작점입니다. `uvicorn`을 이용하여 서버를 실행합니다.
```bash
# Window
uvicorn main:app --reload

# 외부서버
uvicorn main:app --reload --host {서버IP}
```

#### requirements.txt
프로젝트에 필요한 라이브러리를 기록한 파일입니다. 명령어를 통해 자동으로 설치할 수 있습니다.
```bash
pip install -r requirements.txt
```

### 3. 설정
설치 후 생성된 `.env`파일을 수정하여 사용자 설정을 변경할 수 있습니다.
- True/False 는 반드시 문자열로 입력해야 합니다.
- 전체 설정은 `.env.example` 파일을 참고하세요.
> **Note**  
> 설정을 변경하면 서버를 재시작해야 정상적으로 적용됩니다.

#### 데이터베이스 설정
```bash
# sqlite는 접속정보관련 설정값은 무시됩니다.
# (DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)

# 테이블 이름 접두사 설정
DB_TABLE_PREFIX = "g6_"
# mysql, postgresql, sqlite
DB_ENGINE = ""
DB_USER = "username"
DB_PASSWORD = ""
DB_HOST = ""
DB_PORT = ""
DB_NAME = ""
DB_CHARSET = "utf8"
```
#### 이메일 발송 설정
```bash
SMTP_SERVER="localhost"
SMTP_PORT=25
# 메일 테스트시 보내는 사용자 이름 및 이메일 주소 반드시 넣어야 합니다.
SMTP_USERNAME="account@your-domain.com"
SMTP_PASSWORD=""

# 예) 네이버 메일 설정 
# SMTP_SERVER="smtp.naver.com"
# SMTP_PORT=465 # 보안 연결(SSL) 필요
# SMTP_USERNAME="네이버 로그인 아이디"
# SMTP_PASSWORD="네이버 로그인 비밀번호"
```

#### 관리자 테마 설정
```bash
# 관리자 테마 설정
# 관리자 테마는 /admin/templates/{테마} 에 위치해야 합니다.
# 테마 이름을 입력하지 않으면 기본 테마(basic)가 적용됩니다.
ADMIN_THEME = "basic"
```

#### 이미지 설정
```bash
# 이미지 크기변환 여부
UPLOAD_IMAGE_RESIZE = "False"
# MB 이미지 업로드 용량 (기본값 20MB)
UPLOAD_IMAGE_SIZE_LIMIT = 20
# (0~100) default 80 이미지 업로드 퀄리티(jpg)
UPLOAD_IMAGE_QUALITY = 80

# UPLOAD_IMAGE_RESIZE 가 True 이고 설정된값보다 크면 크기를 변환합니다.
# px 이미지 업로드 크기변환 가로 크기
UPLOAD_IMAGE_RESIZE_WIDTH = 1200
# px 이미지 업로드 크기변환 세로 크기
UPLOAD_IMAGE_RESIZE_HEIGHT = 2800
```

#### 기타 설정들
```bash
# 디버그 모드 설정 (True/False)
APP_IS_DEBUG = "False"

# 웹사이트 표시 방법 (True/False)
# "True" (기본값) : 반응형 웹사이트 (참고: 반응형 템플릿만 제공합니다.)
# "False" : 적응형 웹사이트
IS_RESPONSIVE = "True"

# www.gnuboard.com 과 gnuboard.com 도메인은 서로 다른 도메인으로 인식합니다. 
# 쿠키를 공유하려면 .gnuboard.com 과 같이 입력하세요.
# 이곳에 입력하지 않으면 www 붙은 도메인과 그렇지 않은 도메인은 쿠키를 공유하지 못하므로 
# 로그인이 풀릴 수 있습니다.
COOKIE_DOMAIN = ""
```
