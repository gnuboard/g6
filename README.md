
# GNUBOARD with python
<p align="center">
<img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/fastapi?logo=python&color=%233776AB">
</p>

## 개요
### 파이썬을 선택한 이유

* __초보자 친화적__ : 파이썬은 읽고 쓰기 쉬운 구문을 가지고 있어 프로그래밍을 처음 시작하는 사람들에게 이상적입니다. 이러한 접근성은 코딩의 기본 개념을 빠르게 배울 수 있게 도와줍니다.

* __다재다능함__ : 웹 개발, 데이터 과학, 인공 지능, 머신 러닝, 자동화 스크립트, 게임 개발 등 다양한 분야에서 사용됩니다. 이로 인해 파이썬은 매우 유연한 언어로 간주됩니다.

* __강력한 표준 라이브러리와 서드파티 패키지__ : 파이썬은 방대한 표준 라이브러리와 다양한 서드파티 패키지를 제공하여, 거의 모든 프로그래밍 문제를 해결할 수 있게 도와줍니다.

* __대규모 커뮤니티와 지원__ : 파이썬은 전 세계적으로 거대한 개발자 커뮤니티를 가지고 있으며, 이는 신규 개발자들이 자료를 찾고, 문제를 해결하는 데 도움이 됩니다.

* __플랫폼 독립적__ : 파이썬은 다양한 운영 체제에서 실행될 수 있으며, 이는 코드의 이식성을 높여줍니다.

* __효율적인 데이터 처리와 분석__ : 데이터 과학과 관련된 분야에서 파이썬은 데이터 처리와 분석을 위한 강력한 도구로 널리 사용됩니다. NumPy, Pandas, Matplotlib 같은 라이브러리들은 데이터 작업을 매우 효율적으로 만들어줍니다.

이러한 이유들로 인해 파이썬은 전 세계적으로 널리 사용되며, 다양한 분야에서 중요한 역할을 하고 있습니다.
^^[프로그래밍 언어 순위 (티오베 인덱스)](https://www.tiobe.com/tiobe-index/)^^

!!! info "보도 자료"

    우리나라는 2025년 부터 초·중학교 코딩교육을 의무화 하고, 향후 5년간(2022~2026년) 100만명의 디지털 인재를 양성 한다고 합니다.
    인공지능(AI)과 사물인터넷(IoT) 등 첨단 분야의 인력 100만 명을 양성할 계획이므로 이에 적합한 언어로 파이썬이 포함될 것으로 예측합니다.<br>
    ^^[디지털 시대의 주인공이 될 100만 인재를 양성합니다.](https://www.msit.go.kr/bbs/view.do?sCode=user&mId=113&mPid=112&pageIndex=&bbsSeqNo=94&nttSeqNo=3182047&searchOpt=ALL&searchTxt=)^^


### FastAPI를 선택한 이유

파이썬의 주요 웹 프레임워크 중 `Django`, `Flask`, `FastAPI`가 있으며, 최근 사용자들 사이에서 FastAPI의 인기가 높아지고 있습니다.
GitHub에서 FastAPI의 별 표시 추이를 분석한 결과, 그 성장률이 상당히 빠르다는 것을 확인했습니다. 
FastAPI는 세밀한 기능 구현과 빠른 개발 속도로 인기를 얻고 있습니다.

<figure markdown>
  ![Image title](./img/star-history-20231114.png)
  <figcaption>Django, Flask, FastAPI 별 갯수(인기도) 비교 : 2023년 11월 14일</figcaption>
</figure>


### 그누보드5와 비교한 사용성

파이썬과 그누보드5를 직접 비교하는 것은 적절하지 않습니다. 
파이썬은 범용 프로그래밍 언어로, 웹 개발뿐만 아니라 다양한 분야에 활용됩니다. 
반면, 그누보드5는 PHP 기반의 웹솔루션으로, 특정 웹 개발 요구에 특화되어 있습니다.

파이썬을 사용한 웹 개발을 위해 FastAPI와 같은 모던 프레임워크를 배우는 것은 초기에 까다로울 수 있지만, 장기적으로 **유연성**과 **확장성**을 제공합니다. 
실제 홈페이지 운영 목적이라면, 기존의 그누보드5를 사용하는 것이 더 편리할 수 있습니다. 
파이썬과 FastAPI를 사용하는 것은 **학습 과정**에서 더 큰 이점을 제공합니다.

따라서 목적에 따라 선택이 달라질 수 있습니다. 
실제 홈페이지 운영을 위해서는 그누보드5를, 학습과 장기적인 프로젝트 개발을 위해서는 **파이썬**과 **FastAPI**를 추천합니다.

## 시작하기
### 1. 설치
- Git을 사용한 설치를 권장합니다.
- `.env`파일을 생성하지 않아도 설치 진행 시 자동으로 생성됩니다.

#### 설치 방법
```bash
# Github에서 그누보드6 복사 및 설치합니다.
git clone git@github.com:gnuboard/gnu6.git
```

```bash
# cd 명령어를 이용하여 gnu6 디렉토리로 이동합니다.
cd gnu6
```

```bash
# 실행에 필요한 라이브러리들을 설치합니다.
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
      - 기본값은 `g6_` 입니다(예: gnuboard5_)
   - 재설치 여부를 체크합니다. (선택)
      - > **Warning**  
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
   - `/plugin`` 폴더에 제작할 플러그인 디렉토리를 추가합니다.
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
IS_RESPONSIVE = "False" 

# www.gnuboard.com 과 gnuboard.com 도메인은 서로 다른 도메인으로 인식합니다. 
# 쿠키를 공유하려면 .gnuboard.com 과 같이 입력하세요.
# 이곳에 입력하지 않으면 www 붙은 도메인과 그렇지 않은 도메인은 쿠키를 공유하지 못하므로 
# 로그인이 풀릴 수 있습니다.
COOKIE_DOMAIN = ""
```