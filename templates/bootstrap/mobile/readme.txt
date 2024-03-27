### 적응형 웹에 대한 설명


.env 파일에 IS_RESPONSIVE 변수가 선언 되어 있습니다.
이 값이 "True" 일 때는 반응형 웹으로 동작, "False" 일 때는 적응형 웹으로 동작합니다.

적응형 웹은 desktop 과 mobile 을 별도로 운용하고자 할 때 사용합니다.
기본으로 제공하는 템플릿 코드에는 반응형 웹 코드만 적용이 되어 있습니다.


적응형으로 사용하는 경우에는 아래와 같은 방법으로 적용하면 됩니다.

basic 템플릿을 사용하는 경우 templates/basic/bbs/formmail.html 을 
예로 들어 

mobile 템플릿 코드를 작성하려면
templates/basic/mobile/bbs/formmail.html 경로에 작성하면 됩니다.


반응형 웹의 전체 코드를 mobile 로 적용하려고 경우, 아래와 같은 경로로 구성하면 됩니다.


templates
└─  basic
    ├─  bbs
    ├─  board
    ├─  ...
    ├─  mobile
    │   ├─  bbs
    │   ├─  board
    │   ├─  ...
    │   └─  visit
    ├─  ...
    └─  visit


그러나 모든 템플릿 파일을 적용할 필요는 없으며 mobile 로 사용하고자 하는 템플릿 파일만
위의 경로를 참고하여 작성하면 됩니다.

-끝-